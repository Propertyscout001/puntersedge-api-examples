"""
PuntersEdge API — Betting Model Data Feed Example
Load bookmaker odds into a pandas DataFrame for model input or analysis.

Get a free API key: https://puntersedge.online/developers/getting-started
API docs: https://puntersedge.online/betting-model-data-api
"""

import requests
import pandas as pd

API_KEY = "your_api_key_here"
BASE_URL = "https://puntersedge.online/api"
headers = {"X-API-Key": API_KEY}

SPORTS = ["afl", "nrl", "cricket", "tennis"]


def get_odds(sport, market="h2h"):
    resp = requests.get(
        f"{BASE_URL}/odds",
        params={"sport": sport, "market": market},
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def events_to_rows(events, sport):
    """Flatten API response to one row per (event, bookmaker, selection)."""
    rows = []
    for event in events:
        event_id = event.get("id", "")
        home = event.get("home_team", "")
        away = event.get("away_team", "")
        commence = event.get("commence_time", "")
        for bk in event.get("bookmakers", []):
            for market in bk.get("markets", []):
                for outcome in market.get("outcomes", []):
                    rows.append({
                        "sport": sport,
                        "event_id": event_id,
                        "home_team": home,
                        "away_team": away,
                        "commence_time": commence,
                        "bookmaker": bk["key"],
                        "market": market["key"],
                        "selection": outcome["name"],
                        "price": outcome["price"],
                        "implied_prob": round(1 / outcome["price"], 4),
                    })
    return rows


def best_prices(df):
    """Return DataFrame with best available price per (event, selection)."""
    return (
        df.sort_values("price", ascending=False)
        .groupby(["event_id", "selection"], as_index=False)
        .first()[["sport", "event_id", "home_team", "away_team", "commence_time",
                   "selection", "price", "implied_prob", "bookmaker"]]
    )


def main():
    all_rows = []
    for sport in SPORTS:
        print(f"Fetching {sport}...")
        events = get_odds(sport)
        all_rows.extend(events_to_rows(events, sport))

    df = pd.DataFrame(all_rows)
    print(f"\nLoaded {len(df)} rows across {df['event_id'].nunique()} events\n")

    print("=== Best prices per selection ===")
    best = best_prices(df)
    print(best.to_string(index=False))

    print("\n=== Bookmaker coverage ===")
    print(df.groupby(["sport", "bookmaker"]).size().unstack(fill_value=0))

    # Example: flag where implied prob sum < 1.0 (potential arb)
    implied_sums = df.groupby("event_id")["implied_prob"].sum()
    arbs = implied_sums[implied_sums < 1.0]
    if len(arbs):
        print(f"\n⚡ {len(arbs)} events with implied prob sum < 1.0 (potential arb)")

    # Save for model use
    df.to_csv("odds_feed.csv", index=False)
    print("\nSaved to odds_feed.csv")


if __name__ == "__main__":
    main()
