"""
PuntersEdge API — Arbitrage Scanner Example
Detects arbitrage opportunities across Australian bookmakers.

An arb exists when 1/best_price_A + 1/best_price_B < 1.0 — but only if a stake
sits on EVERY way the market can settle, and only if every price is live. This
scanner enforces both, which is why it reports far fewer "arbs" than the naive
formula does.

Get a free API key: https://puntersedge.online/developers/getting-started
Walkthrough:       https://puntersedge.online/blog/how-to-build-arb-scanner-australia
"""

import re

import requests

API_KEY = "your_api_key_here"
BASE_URL = "https://api.puntersedge.online/v1"
headers = {"X-API-Key": API_KEY}

# Real sport keys — see GET /v1/sports for the catalogue. Racing is NOT a sport
# key; horse, harness and greyhound racing live under /v1/racing/*.
#
# Coverage is thin: at most 5 Australian bookmakers price afl and nrl, 3 price
# nba and tennis_atp, and several other keys carry a single book. One bookmaker
# can never produce an arb, so dry runs are the normal result. Two-way markets
# only — soccer_other settles home/draw/away and needs a third leg this example
# does not place.
SPORTS = ["afl", "nrl", "nba", "tennis_atp"]

# Cost: this endpoint is 1 credit per requested market, so one pass over SPORTS
# with markets=h2h costs len(SPORTS) credits. The free tier is 1,500 per month.

_WORDS = re.compile(r"[a-z0-9]+")


def get_odds(sport_key):
    """GET /v1/sports/{sport_key}/odds — returns a bare JSON array of events."""
    resp = requests.get(
        f"{BASE_URL}/sports/{sport_key}/odds",
        params={"markets": "h2h"},
        headers=headers,
        timeout=10,
    )
    if not resp.ok:
        # Errors are problem+json: {"type", "title", "status", "detail"}.
        try:
            problem = resp.json()
        except ValueError:
            problem = {}
        raise SystemExit(
            f"{resp.status_code} {problem.get('title', resp.reason)}: "
            f"{problem.get('detail', resp.text[:200])}"
        )
    return resp.json()


def side_of(outcome_name, home_team, away_team):
    """Map a bookmaker's outcome name onto the event's home or away side.

    Bookmakers do not agree on team names — the same side is "Melbourne Storm" at
    one book and "Melbourne" at another. Grouping by raw outcome name (the obvious
    approach) splits one team into two pseudo-selections and makes the implied
    probability sum meaningless. Match on token containment against the event's
    own home_team / away_team instead, and return None rather than guess when a
    name is ambiguous or unrecognised (a Draw line, or "N. Djokovic" against a
    home_team of "Novak Djokovic"). An unmapped name costs a missed arb, never a
    phantom one.
    """
    tokens = frozenset(_WORDS.findall((outcome_name or "").lower()))
    if not tokens:
        return None
    hits = []
    for side, label in (("home", home_team), ("away", away_team)):
        side_tokens = frozenset(_WORDS.findall((label or "").lower()))
        if side_tokens and (tokens <= side_tokens or side_tokens <= tokens):
            hits.append(side)
    return hits[0] if len(hits) == 1 else None


def find_best_prices(event):
    """Best h2h price per side across all bookmakers on one event.

    Returns (best, max_outcomes, unmapped):
      best         -> {"home": (price, bookmaker_key, outcome_name), "away": ...}
      max_outcomes -> the widest outcome space any single bookmaker listed
      unmapped     -> outcomes that could not be placed on a side
    """
    home_team = event.get("home_team")
    away_team = event.get("away_team")
    # A price that has stopped updating is the biggest single source of phantom
    # arbs. The API names the frozen books on each event, so drop them.
    frozen = set(event.get("stale_bookmakers") or [])

    best = {}
    max_outcomes = 0
    unmapped = 0

    for bookmaker in event.get("bookmakers", []):
        bk_key = bookmaker.get("key")
        if bk_key in frozen or bookmaker.get("stale"):
            continue
        for market in bookmaker.get("markets", []):
            if market.get("key") != "h2h":
                continue
            outcomes = market.get("outcomes", [])
            max_outcomes = max(max_outcomes, len(outcomes))
            for outcome in outcomes:
                price = outcome.get("price")
                if not isinstance(price, (int, float)) or price <= 1:
                    continue
                side = side_of(outcome.get("name"), home_team, away_team)
                if side is None:
                    unmapped += 1
                    continue
                if side not in best or price > best[side][0]:
                    best[side] = (price, bk_key, outcome.get("name"))

    return best, max_outcomes, unmapped


def check_arb(best, max_outcomes):
    """Returns (is_arb, implied_sum, profit_pct).

    Refuses to call it an arb unless both sides are priced AND no single book
    listed a wider outcome space than the two covered here. Two-way math on a
    market that can also settle a third way is not an arb — it is an unhedged bet
    that the third outcome does not happen, and that outcome loses both legs.
    This mirrors the server-side guard on GET /v1/arb/sports.
    """
    if len(best) < 2 or max_outcomes > 2:
        return False, None, 0.0
    implied = sum(1 / price for price, _, _ in best.values())
    if implied < 1.0:
        return True, round(implied, 4), round((1 - implied) * 100, 2)
    return False, round(implied, 4), 0.0


def main():
    print("🔍 PuntersEdge Arb Scanner\n")
    arbs_found = 0
    events_scanned = 0
    unmapped_total = 0

    for sport_key in SPORTS:
        events = get_odds(sport_key)  # bare array of events, not {"data": [...]}
        events_scanned += len(events)

        for event in events:
            home = event.get("home_team") or "?"
            away = event.get("away_team") or "?"
            best, max_outcomes, unmapped = find_best_prices(event)
            unmapped_total += unmapped
            is_arb, implied, profit = check_arb(best, max_outcomes)

            if not is_arb:
                continue

            arbs_found += 1
            print(f"✅ ARB FOUND: {home} vs {away} ({sport_key})")
            print(f"   Implied margin: {implied}  |  Profit: {profit}%")
            for side in ("home", "away"):
                price, bk_key, name = best[side]
                print(f"   {name:30s}  {price:.2f}  @ {bk_key}")
            if len({bk for _, bk, _ in best.values()}) == 1:
                print("   NOTE: both legs at one bookmaker — usually a stale price, "
                      "not a placeable arb. Verify before staking.")
            print()

    print(f"Scanned {events_scanned} events across {len(SPORTS)} sports.")
    if unmapped_total:
        print(f"{unmapped_total} outcome(s) skipped: name variants or extra lines "
              f"that could not be matched to a side.")
    if arbs_found == 0:
        print("No arbs found right now — the normal result with this few books "
              "pricing each market. Try again closer to the jump.")
    else:
        print(f"Found {arbs_found} arb opportunity/ies.")
    print("One-call alternative: GET /v1/arb/sports (3 credits) runs these same "
          "guards server-side and returns optimal stakes.")


if __name__ == "__main__":
    main()
