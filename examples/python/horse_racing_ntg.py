"""
PuntersEdge API — Horse Racing Next-to-Go Example
Fetch the next upcoming Australian horse racing events with runner odds.

Get a free API key: https://puntersedge.online/developers/getting-started
API docs: https://puntersedge.online/horse-racing-api-australia
"""

import requests
from datetime import datetime, timezone

API_KEY = "your_api_key_here"
BASE_URL = "https://puntersedge.online/api"
headers = {"X-API-Key": API_KEY}


def get_racing_ntg(limit=5):
    """Fetch the next {limit} horse racing events."""
    resp = requests.get(
        f"{BASE_URL}/racing/next-to-go",
        params={"sport": "horse_racing", "limit": limit},
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def format_time(iso_str):
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        mins = int((dt - now).total_seconds() / 60)
        return f"in {mins}m" if mins > 0 else "NOW"
    except Exception:
        return iso_str


def main():
    races = get_racing_ntg(limit=8)
    print(f"🏇 Next {len(races)} Australian horse racing events\n")

    for race in races:
        venue = race.get("venue", "Unknown")
        race_num = race.get("race_number", "")
        name = race.get("race_name", "")
        start = format_time(race.get("commence_time", ""))

        print(f"R{race_num} {venue} — {name}  ({start})")

        # Show top 3 runners by best available price
        runners = []
        for bk in race.get("bookmakers", []):
            for market in bk.get("markets", []):
                if market["key"] != "win":
                    continue
                for outcome in market["outcomes"]:
                    runners.append({
                        "name": outcome["name"],
                        "price": outcome["price"],
                        "bookmaker": bk["key"],
                    })

        # Best price per runner
        best = {}
        for r in runners:
            n = r["name"]
            if n not in best or r["price"] > best[n]["price"]:
                best[n] = r

        # Sort by price ascending (favourite first)
        sorted_runners = sorted(best.values(), key=lambda x: x["price"])
        for runner in sorted_runners[:5]:
            print(f"  {runner['name']:30s}  ${runner['price']:.2f}  ({runner['bookmaker']})")
        print()


if __name__ == "__main__":
    main()
