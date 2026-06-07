"""
PuntersEdge API — Arbitrage Scanner Example
Detects arbitrage opportunities across Australian bookmakers.

Arb exists when: 1/odds_team_a + 1/odds_team_b < 1.0

Get a free API key: https://puntersedge.online/developers/getting-started
API docs: https://puntersedge.online/arbitrage-betting-api-australia
"""

import requests

API_KEY = "your_api_key_here"
BASE_URL = "https://puntersedge.online/api"
headers = {"X-API-Key": API_KEY}

SPORTS = ["afl", "nrl", "cricket", "tennis", "nba"]


def get_odds(sport):
    resp = requests.get(
        f"{BASE_URL}/odds",
        params={"sport": sport, "market": "h2h"},
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def find_best_prices(event):
    """Return {team: (best_price, bookmaker)} across all bookmakers for an event."""
    best = {}
    for bk in event.get("bookmakers", []):
        for market in bk.get("markets", []):
            if market["key"] != "h2h":
                continue
            for outcome in market["outcomes"]:
                name = outcome["name"]
                price = outcome["price"]
                if name not in best or price > best[name][0]:
                    best[name] = (price, bk["key"])
    return best


def check_arb(prices):
    """Returns (True, margin, profit_pct) if arb exists, else (False, margin, 0)."""
    if len(prices) < 2:
        return False, None, 0
    implied = sum(1 / p for p, _ in prices.values())
    if implied < 1.0:
        profit_pct = round((1 - implied) * 100, 2)
        return True, round(implied, 4), profit_pct
    return False, round(implied, 4), 0


def main():
    print("🔍 PuntersEdge Arb Scanner\n")
    arbs_found = 0

    for sport in SPORTS:
        events = get_odds(sport)
        for event in events:
            home = event.get("home_team", "?")
            away = event.get("away_team", "?")
            prices = find_best_prices(event)
            is_arb, margin, profit = check_arb(prices)

            if is_arb:
                arbs_found += 1
                print(f"✅ ARB FOUND: {home} vs {away} ({sport.upper()})")
                print(f"   Implied margin: {margin}  |  Profit: {profit}%")
                for team, (price, bk) in prices.items():
                    print(f"   {team:30s}  {price:.2f}  @ {bk}")
                print()

    if arbs_found == 0:
        print("No arbs found right now. Markets are efficient — check again soon.")
    else:
        print(f"Found {arbs_found} arb opportunity/ies.")


if __name__ == "__main__":
    main()
