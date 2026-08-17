"""
PuntersEdge API - AFL Odds Example
Fetch AFL head-to-head odds and find the best available price per team.

Get a free API key (1,500 credits/month, no credit card):
    https://puntersedge.online/developers/getting-started
API docs: https://puntersedge.online/developers/sports-odds-api-australia

Cost: /v1/sports/{sport_key}/odds bills 1 credit per requested market, so the
single markets=h2h call below costs 1 credit.
"""

import json
import sys

import requests

API_KEY = "your_api_key_here"
BASE_URL = "https://api.puntersedge.online/v1"

headers = {"X-API-Key": API_KEY}


def get_afl_odds():
    """Fetch current AFL head-to-head odds.

    The sport is a PATH segment (/sports/afl/odds), and the query parameter is
    `markets` - plural, comma-separated. Other valid params: bookmakers,
    competition, include_unknown_competition, oddsFormat, maxAgeMinutes.

    Racing is NOT a sport_key. For horse, harness or greyhound racing use
    /v1/racing/next-to-go instead - see horse_racing_ntg.py.

    Returns a bare JSON array of events. There is no "data" or "events" wrapper.
    """
    resp = requests.get(
        f"{BASE_URL}/sports/afl/odds",
        params={"markets": "h2h"},  # oddsFormat defaults to decimal
        headers=headers,
        timeout=10,
    )
    if resp.status_code in (401, 402, 429):
        # Errors are RFC 7807 application/problem+json: type, title, status, detail.
        problem = resp.json()
        # `detail` is a string for most errors, an ARRAY of field errors on 422 and an
        # OBJECT on 429 — print it defensively rather than interpolating a raw dict.
        _d = problem.get('detail')
        if not isinstance(_d, str):
            _d = json.dumps(_d)
        sys.exit(f"{resp.status_code} {problem.get('title')}: {_d}")
    resp.raise_for_status()
    return resp.json()


def _tokens(name):
    """Lowercase word tokens of a team name, punctuation stripped."""
    cleaned = "".join(c if c.isalnum() else " " for c in name)
    return {t for t in cleaned.lower().split() if t}


def match_team(outcome_name, home, away):
    """Map one bookmaker's outcome name onto the event's home or away team.

    Bookmakers do not agree on team names and the API passes each book's own
    spelling through untouched: on a live AFL event one book priced
    "Gold Coast" while another priced "Gold Coast SUNS". Grouping on the raw
    name splits one team into two rows and understates its best price.

    Matches when one token set contains the other. Returns None when the name
    is ambiguous or unrecognised - reporting it unmatched beats assigning the
    price to the wrong side.
    """
    got = _tokens(outcome_name)
    hits = [
        team
        for team in (home, away)
        if team and got and (got <= _tokens(team) or _tokens(team) <= got)
    ]
    return hits[0] if len(hits) == 1 else None


def best_price(event):
    """Best available h2h price per team across every bookmaker on the event.

    Returns (matched, unmatched): both map a label to {"price", "bookmaker"}.
    """
    home, away = event.get("home_team"), event.get("away_team")
    matched, unmatched = {}, {}
    for bookmaker in event.get("bookmakers", []):
        bk_name = bookmaker["key"]
        for market in bookmaker.get("markets", []):
            if market["key"] != "h2h":
                continue
            for outcome in market.get("outcomes", []):
                price = outcome["price"]
                team = match_team(outcome["name"], home, away)
                target = matched if team else unmatched
                label = team or outcome["name"]
                if label not in target or price > target[label]["price"]:
                    target[label] = {"price": price, "bookmaker": bk_name}
    return matched, unmatched


def main():
    events = get_afl_odds()
    print(f"Found {len(events)} AFL events\n")

    for event in events:
        home = event.get("home_team") or "Home"
        away = event.get("away_team") or "Away"
        print(f"{home} vs {away}  |  {event['commence_time']}")

        # Coverage on AFL is thin: at most 5 bookmakers price an event and some
        # carry three, so "best price" here means best of a handful, not of
        # the whole Australian market.
        books = [b["key"] for b in event.get("bookmakers", [])]
        print(f"  {len(books)} bookmaker(s): {', '.join(books) or 'none'}")

        # `stale` is true when the OLDEST contributing book has not updated in
        # 30 minutes (twice the 15-minute sports poll); `stale_bookmakers`
        # names them so you can drop those prices and keep the rest.
        if event.get("stale"):
            stale_books = ", ".join(event.get("stale_bookmakers", [])) or "unknown"
            print(f"  STALE - no recent update from: {stale_books}")

        matched, unmatched = best_price(event)
        for team, info in matched.items():
            print(f"  {team:30s}  Best: ${info['price']:.2f}  ({info['bookmaker']})")
        for name, info in unmatched.items():
            print(f"  {name:30s}  ${info['price']:.2f}  ({info['bookmaker']}) [unmatched name]")
        print()

    if not events:
        print("No upcoming AFL events. The AFL season runs March to September;")
        print("try markets=h2h on nba or nfl out of season — nrl runs Mar-Oct, alongside AFL.")


if __name__ == "__main__":
    main()
