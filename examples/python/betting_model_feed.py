"""
PuntersEdge API — Betting Model Data Feed Example
Load bookmaker odds into a pandas DataFrame for model input or analysis.

Get a free API key: https://puntersedge.online/developers/getting-started
API docs: https://puntersedge.online/betting-model-data-api

Requires: pip install requests pandas

Cost: GET /v1/sports/{sport_key}/odds bills 1 credit per requested market, so the
run below (4 sports x 1 market) costs 4 credits. The free tier is 1,500 credits
per month, no credit card.
"""

import re

import requests
import pandas as pd

API_KEY = "your_api_key_here"
BASE_URL = "https://api.puntersedge.online/v1"
headers = {"X-API-Key": API_KEY}

# Real sport keys — GET /v1/sports has the live catalogue. Racing is NOT a sport
# key: horse, harness and greyhound racing live under /v1/racing/*, not here.
# Coverage is uneven, so know it before you model on it: up to 5 bookmakers per
# event on afl and nrl, about 3 on nba and tennis_atp, as few as 1 on some keys.
# Out of season is an empty array with HTTP 200, not an error; an unknown key is
# a 404 and costs no credits.
SPORTS = ["afl", "nrl", "nba", "tennis_atp"]

_DRAW = {"draw", "tie", "x"}


def get_odds(sport, markets="h2h"):
    """GET /v1/sports/{sport_key}/odds — returns a BARE JSON array of events.

    Sport is a path segment; the market list is `markets` (comma-separated:
    h2h,spreads,totals). Prices are decimal unless you pass oddsFormat=american,
    in which case the implied probability below no longer applies.
    """
    resp = requests.get(
        f"{BASE_URL}/sports/{sport}/odds",
        params={"markets": markets},
        headers=headers,
        timeout=10,
    )
    if resp.status_code in (401, 402, 404, 429):
        # Errors are application/problem+json with a readable `detail`.
        problem = resp.json() if "json" in resp.headers.get("content-type", "") else {}
        raise SystemExit(f"HTTP {resp.status_code}: {problem.get('detail') or resp.text[:300]}")
    resp.raise_for_status()
    return resp.json()


def _tokens(name):
    return {t for t in re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).split() if t}


def side_of(home, away, selection):
    """Collapse a bookmaker's selection name onto the event's home/away side.

    Books spell the same team differently — one sends "Melbourne Storm" where
    another sends "Melbourne" — so grouping on the raw name splits one runner in
    two. This token-subset match is deliberately simple; a name matching neither
    side keeps its own label rather than being merged. For the API's own
    alias-aware grouping use GET /v1/best-odds/{sport_key} (3 credits).
    """
    t = _tokens(selection)
    if not t:
        return (selection or "").strip()
    if t & _DRAW:
        return "Draw"
    for team in (home, away):
        tt = _tokens(team)
        if tt and (t <= tt or tt <= t):
            return team
    return (selection or "").strip()


def events_to_rows(events, sport):
    """Flatten the API response to one row per (event, bookmaker, selection)."""
    rows = []
    for event in events:
        home = event.get("home_team") or ""
        away = event.get("away_team") or ""
        for bk in event.get("bookmakers", []):
            for market in bk.get("markets", []):
                for outcome in market.get("outcomes", []):
                    price = outcome.get("price")
                    if not price or price <= 1:
                        continue  # missing price, or one that cannot return a profit
                    rows.append({
                        "sport": sport,
                        "event_id": event["id"],
                        "competition": event.get("competition") or "",
                        "home_team": home,
                        "away_team": away,
                        "commence_time": event["commence_time"],
                        "bookmaker": bk["key"],
                        "market": market["key"],
                        "selection": outcome["name"],
                        "side": side_of(home, away, outcome["name"]),
                        "price": price,
                        "implied_prob": round(1 / price, 4),
                        # Freshness of THIS book's market. The event-level `stale`
                        # flag follows the oldest contributing book, so check the
                        # per-book age before feeding a price to a model.
                        "age_seconds": bk.get("age_seconds"),
                        "stale": bool(bk.get("stale", False)),
                    })
    return rows


def best_prices(df):
    """One row per (event, market, side): the best price and the book offering it."""
    winners = df.loc[df.groupby(["event_id", "market", "side"])["price"].idxmax()]
    return winners[[
        "sport", "event_id", "commence_time", "home_team", "away_team",
        "market", "side", "price", "implied_prob", "bookmaker", "age_seconds",
    ]].sort_values(["event_id", "side"])


def main():
    all_rows = []
    for sport in SPORTS:
        print(f"Fetching {sport}...")
        events = get_odds(sport)
        if not events:
            print(f"  no upcoming {sport} events with fresh prices")
            continue
        all_rows.extend(events_to_rows(events, sport))

    if not all_rows:
        print("\nNo odds returned — every sport above is between fixtures right now.")
        return

    df = pd.DataFrame(all_rows)
    print(f"\nLoaded {len(df)} rows across {df['event_id'].nunique()} events\n")

    print("=== Best price per selection ===")
    best = best_prices(df)
    print(best.to_string(index=False))

    print("\n=== Bookmaker coverage ===")
    print(df.groupby(["sport", "bookmaker"]).size().unstack(fill_value=0))

    if df["stale"].any():
        stale_books = sorted(df.loc[df["stale"], "bookmaker"].unique())
        print(f"\nStale markets present from: {', '.join(stale_books)}")

    # Overround per event+market, from the best price on each side. Under 1.0
    # means the best prices cross — the arithmetic definition of an arb, not a
    # promise both legs are still on screen, hence the oldest leg alongside it.
    # A name side_of() could not place stays its own side and adds a term, so
    # this under-reports rather than inventing crossings.
    scored = best.groupby(["event_id", "market"]).agg(
        overround=("implied_prob", "sum"),
        oldest_leg_seconds=("age_seconds", "max"),
    )
    crossed = scored[scored["overround"] < 1.0]
    if len(crossed):
        print("\nBest prices cross (implied probability sums below 1.0):")
        print(crossed.round(4).to_string())

    # Save for model use
    df.to_csv("odds_feed.csv", index=False)
    print(f"\nSaved {len(df)} rows to odds_feed.csv")


if __name__ == "__main__":
    main()
