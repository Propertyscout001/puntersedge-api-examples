"""
PuntersEdge API — AFL Odds Example
Fetch AFL head-to-head odds and find the best available price per team.

Get a free API key: https://puntersedge.online/developers/getting-started
API docs: https://puntersedge.online/developers/sports-odds-api-australia
"""

import requests

API_KEY = "your_api_key_here"
BASE_URL = "https://puntersedge.online/api"

headers = {"X-API-Key": API_KEY}


def get_afl_odds():
    """Fetch current AFL head-to-head odds."""
    resp = requests.get(
        f"{BASE_URL}/odds",
        params={"sport": "afl", "market": "h2h"},
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def best_price(event):
    """Find the best available price per team across all bookmakers."""
    best = {}
    for bookmaker in event.get("bookmakers", []):
        bk_name = bookmaker["key"]
        for market in bookmaker.get("markets", []):
            if market["key"] != "h2h":
                continue
            for outcome in market.get("outcomes", []):
                team = outcome["name"]
                price = outcome["price"]
                if team not in best or price > best[team]["price"]:
                    best[team] = {"price": price, "bookmaker": bk_name}
    return best


def main():
    data = get_afl_odds()
    events = data.get("data", [])
    print(f"Found {len(events)} AFL events\n")

    for event in events:
        home = event.get("home_team", "Home")
        away = event.get("away_team", "Away")
        commence = event.get("commence_time", "")
        print(f"{home} vs {away}  |  {commence}")

        prices = best_price(event)
        for team, info in prices.items():
            print(f"  {team:30s}  Best: ${info['price']:.2f}  ({info['bookmaker']})")
        print()


if __name__ == "__main__":
    main()
