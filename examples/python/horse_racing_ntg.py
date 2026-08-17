"""
PuntersEdge API — Horse Racing Next-to-Go Example
Fetch the next upcoming Australian horse racing events with runner odds.

Get a free API key (1,500 credits/month, no card): https://puntersedge.online/developers/getting-started
API docs: https://puntersedge.online/horse-racing-api-australia
"""

import requests
from datetime import datetime, timezone

API_KEY = "your_api_key_here"
BASE_URL = "https://api.puntersedge.online/v1"
headers = {"X-API-Key": API_KEY}


def get_racing_ntg(num_races=8):
    """Fetch the next `num_races` Australian horse races. Costs 2 credits per call.

    Racing is its own endpoint family under /v1/racing/* — there is no
    `horse_racing` sport key, and this is not /v1/sports/{key}/odds.

    Params this endpoint accepts: num_races, categories, bookmakers, country.
      categories — horse, greyhound, harness (comma-separated); omit for all.
      country    — pass AU. Every non-Australian race in the feed is quoted by
                   exactly ONE bookmaker, so a cross-book comparison on those
                   races compares nothing.

    Returns a bare JSON array of races (not an object with a "data" key).
    """
    resp = requests.get(
        f"{BASE_URL}/racing/next-to-go",
        params={"num_races": num_races, "categories": "horse", "country": "AU"},
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def format_time(iso_str):
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        mins = int((dt - now).total_seconds() / 60)
        return f"in {mins}m" if mins > 0 else "NOW"
    except Exception:
        return iso_str


def best_price_per_runner(race):
    """Best available win price for each runner, across bookmakers.

    Each runner carries a `bookmakers` list of {key, win_price, ...} entries —
    there is no markets/outcomes nesting on racing. `win_price` can be null, and
    each entry carries its own `age_seconds`/`stale`, so a book that has stopped
    publishing is skipped rather than allowed to win the "best price" comparison.

    How many books quote a race is not a fixed number: an Australian race gathers
    bookmakers as it approaches the jump (a median of 10 inside 30 minutes, far
    fewer hours out). Betfair Exchange prices are withheld from customer keys, so
    what you see here is the 11 bookmakers, not the exchange.
    """
    best = []
    for runner in race.get("runners", []):
        top = None
        for bk in runner.get("bookmakers", []):
            price = bk.get("win_price")
            if price is None or bk.get("stale"):
                continue
            if top is None or price > top["price"]:
                top = {"price": price, "bookmaker": bk["key"]}
        if top:
            # `number` is the saddlecloth, resolved by majority vote across the
            # books; it is null when no book supplies one.
            best.append({"name": runner["name"], "number": runner.get("number"), **top})
    return best


def main():
    races = get_racing_ntg(num_races=8)
    print(f"Next {len(races)} Australian horse racing events\n")

    for race in races:
        venue = race.get("venue") or "Unknown"
        race_num = race.get("race_number") or ""
        name = race.get("race_name") or ""
        start = format_time(race.get("start_time", ""))

        header = f"R{race_num} {venue}"
        if name:
            header += f" — {name}"
        print(f"{header}  ({start})")

        # Race-level freshness is reported worst-first: `data_age_seconds` is the
        # age of the OLDEST quote in the race. A stale book does not invalidate
        # the race — the loop above just drops that leg.
        if race.get("stale"):
            print(f"  ! stale books: {', '.join(race.get('stale_bookmakers', [])) or 'unknown'}")

        # Scratched runners are never in `runners` — they live in `scratchings`.
        scratchings = race.get("scratchings") or []
        if scratchings:
            print(f"  {len(scratchings)} scratching(s)")

        # Sort by price ascending (favourite first)
        for runner in sorted(best_price_per_runner(race), key=lambda r: r["price"])[:5]:
            num = f"{runner['number']}." if runner["number"] is not None else " "
            print(f"  {num:>4} {runner['name']:28s}  ${runner['price']:.2f}  ({runner['bookmaker']})")
        print()


if __name__ == "__main__":
    main()
