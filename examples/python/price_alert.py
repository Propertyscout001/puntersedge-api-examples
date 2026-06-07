"""
PuntersEdge API — Price Alert Example
Poll the API and alert when a team's odds exceed a target price.

Get a free API key: https://puntersedge.online/developers/getting-started
API docs: https://puntersedge.online/odds-alert-api-australia
"""

import requests
import time

API_KEY = "your_api_key_here"
BASE_URL = "https://puntersedge.online/api"
headers = {"X-API-Key": API_KEY}

# --- Configure your alert here ---
SPORT = "afl"
MARKET = "h2h"
TARGET_TEAM = "Sydney Swans"
TARGET_PRICE = 2.80  # Alert when price >= this
POLL_INTERVAL_SECONDS = 60
# ----------------------------------


def get_odds():
    resp = requests.get(
        f"{BASE_URL}/odds",
        params={"sport": SPORT, "market": MARKET},
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def find_best_price_for_team(events, team):
    """Scan all bookmakers for the best current price for a team."""
    best_price = None
    best_bk = None
    for event in events:
        home = event.get("home_team", "")
        away = event.get("away_team", "")
        if team not in (home, away):
            continue
        for bk in event.get("bookmakers", []):
            for market in bk.get("markets", []):
                if market["key"] != "h2h":
                    continue
                for outcome in market["outcomes"]:
                    if outcome["name"] == team:
                        if best_price is None or outcome["price"] > best_price:
                            best_price = outcome["price"]
                            best_bk = bk["key"]
    return best_price, best_bk


def alert(team, price, bookmaker):
    """Replace this with email, Telegram, SMS, etc."""
    print(f"\n🔔 ALERT! {team} is now ${price:.2f} at {bookmaker}")
    print(f"   Target was ${TARGET_PRICE:.2f} — go go go!\n")


def main():
    print(f"👀 Watching {TARGET_TEAM} for price >= ${TARGET_PRICE:.2f}")
    print(f"   Polling every {POLL_INTERVAL_SECONDS}s. Ctrl+C to stop.\n")

    while True:
        try:
            events = get_odds()
            price, bk = find_best_price_for_team(events, TARGET_TEAM)

            if price is None:
                print(f"  {TARGET_TEAM} not found in current markets.")
            elif price >= TARGET_PRICE:
                alert(TARGET_TEAM, price, bk)
            else:
                print(f"  {TARGET_TEAM}: best price ${price:.2f} @ {bk} (waiting for ${TARGET_PRICE:.2f})")

        except requests.RequestException as e:
            print(f"  API error: {e}")

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
