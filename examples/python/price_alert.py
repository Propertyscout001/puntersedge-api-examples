"""
PuntersEdge API — Price Alert Example
Poll the API and alert when a team's odds drift out to a target price.

Get a free API key: https://puntersedge.online/developers/getting-started
API docs: https://puntersedge.online/developers/sports-odds-api-australia

Cost: GET /v1/sports/{sport_key}/odds bills 1 credit per market requested, so each poll
below costs 1 credit. Polling every 60s is 60 credits/hour — the free tier's 1,500
credits/month covers roughly 25 hours of continuous polling, so run this for the session
before a game rather than leaving it up all month. The server caches this endpoint for
30 seconds, so polling faster than that spends credits on identical data. The free plan
also caps you at 30 requests/minute.
"""

import requests
import time

API_KEY = "your_api_key_here"
BASE_URL = "https://api.puntersedge.online/v1"
HEADERS = {"X-API-Key": API_KEY}

# --- Configure your alert here ---
SPORT = "afl"          # a real sport_key: afl, nrl, nba, nfl, tennis_atp, ... (GET /v1/sports)
MARKETS = "h2h"        # comma-separated; valid values are h2h, spreads, totals
TARGET_TEAM = "Sydney Swans"
TARGET_PRICE = 2.80    # Alert when the best price is >= this
POLL_INTERVAL_SECONDS = 60
# ----------------------------------

# Racing is NOT a sport_key. For horse/harness/greyhound use GET /v1/racing/next-to-go —
# passing "horse_racing" here is a 404.
#
# Sports coverage is thinner than racing: AFL and NRL carry at most 5 bookmakers, NBA and
# ATP at most 3, and several sports only one. "Best price" below means best of whoever
# priced this event, not best of the whole Australian market.


class ApiError(RuntimeError):
    """A 4xx that won't fix itself — bad key, exhausted credits, bad parameter."""


class RateLimited(RuntimeError):
    def __init__(self, retry_after):
        super().__init__(f"rate limited, retry in {retry_after}s")
        self.retry_after = retry_after


def _describe(resp):
    """Pull a human message out of the API's application/problem+json body."""
    try:
        body = resp.json()
    except ValueError:
        return resp.text[:200]
    detail = body.get("detail") if isinstance(body, dict) else None
    if isinstance(detail, dict):                       # 429 sends an object
        return detail.get("message", str(detail))
    if isinstance(detail, list):                       # 422 sends field errors
        return "; ".join(str(item.get("msg", item)) for item in detail)
    return detail or (body.get("title") if isinstance(body, dict) else str(body)[:200])


def fetch_events():
    """One poll. Returns (events, credits_remaining).

    GET /v1/sports/{sport_key}/odds returns a BARE JSON ARRAY of event objects — there is
    no wrapper object and no "data" key.
    """
    resp = requests.get(
        f"{BASE_URL}/sports/{SPORT}/odds",
        params={"markets": MARKETS},
        headers=HEADERS,
        timeout=10,
    )
    if resp.status_code == 429:
        raise RateLimited(int(resp.headers.get("Retry-After", 60)))
    if 400 <= resp.status_code < 500:
        raise ApiError(f"HTTP {resp.status_code}: {_describe(resp)}")
    resp.raise_for_status()
    # Successful (billed) responses carry X-Credits-Remaining, so you can watch the
    # balance without spending an extra call. Error responses do NOT: a 401 carries
    # x-request-id but no credit headers, so guard the lookup rather than assuming.
    return resp.json(), resp.headers.get("X-Credits-Remaining", "?")


def _norm(name):
    return "".join(ch for ch in (name or "").lower() if ch.isalnum())


def _same_team(a, b):
    """Bookmakers spell teams differently — TAB sends 'Brisbane' where Sportsbet sends
    'Brisbane Lions', Palmerbet sends 'Gold Coast SUNS' where PointsBet sends 'Gold Coast'.
    An exact string match silently drops those books, so compare on containment. Use the
    full club name in TARGET_TEAM: a short one like 'Sydney' would also match
    'South Sydney Rabbitohs'.
    """
    a, b = _norm(a), _norm(b)
    return bool(a) and bool(b) and (a in b or b in a)


def find_best_price_for_team(events, team):
    """Scan every bookmaker on the matching event for the best current price.

    Skips bookmakers the API has flagged stale — a price that stopped updating six hours
    ago is not one you can take, and alerting on it is worse than not alerting.
    """
    best_price = None
    best_bk = None
    best_age = None
    for event in events:
        if not (_same_team(team, event.get("home_team")) or _same_team(team, event.get("away_team"))):
            continue
        for bk in event.get("bookmakers", []):
            if bk.get("stale"):
                continue
            for market in bk.get("markets", []):
                if market.get("key") != "h2h":
                    continue
                for outcome in market.get("outcomes", []):
                    if not _same_team(team, outcome.get("name")):
                        continue
                    price = outcome.get("price")
                    if price is not None and (best_price is None or price > best_price):
                        best_price, best_bk = price, bk.get("key")
                        best_age = bk.get("age_seconds")
    return best_price, best_bk, best_age


def alert(team, price, bookmaker):
    """Replace this with email, Telegram, SMS, etc."""
    print(f"\n🔔 ALERT! {team} is now ${price:.2f} at {bookmaker}")
    print(f"   Target was ${TARGET_PRICE:.2f} — go go go!\n")


def main():
    print(f"👀 Watching {TARGET_TEAM} in {SPORT} for price >= ${TARGET_PRICE:.2f}")
    print(f"   Polling every {POLL_INTERVAL_SECONDS}s (1 credit each). Ctrl+C to stop.\n")

    while True:
        wait = POLL_INTERVAL_SECONDS
        try:
            events, credits_left = fetch_events()
            price, bk, age = find_best_price_for_team(events, TARGET_TEAM)

            if price is None:
                print(f"  {TARGET_TEAM} not priced right now "
                      f"({len(events)} upcoming {SPORT} events). Credits left: {credits_left}")
            elif price >= TARGET_PRICE:
                alert(TARGET_TEAM, price, bk)
            else:
                age_note = f", {age}s old" if age is not None else ""
                print(f"  {TARGET_TEAM}: best ${price:.2f} @ {bk}{age_note} "
                      f"(waiting for ${TARGET_PRICE:.2f}). Credits left: {credits_left}")

        except RateLimited as e:
            wait = e.retry_after
            print(f"  Rate limited — backing off {wait}s.")
        except ApiError as e:
            print(f"  {e}")
            print("  Stopping: check your key, plan credits and parameters.")
            return
        except requests.RequestException as e:
            print(f"  Network error: {e}")

        time.sleep(wait)


if __name__ == "__main__":
    main()
