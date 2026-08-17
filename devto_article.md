# How to Build an Australian Sports Odds Comparison App in Python

If you've ever wanted to compare AFL, NRL or horse racing odds across Australian bookmakers without scraping 11 different websites — this is for you.

In this tutorial I'll show you how to use the [PuntersEdge API](https://puntersedge.online/developers) to fetch live Australian bookmaker odds and find the best available price in a few lines of Python.

---

## What We're Building

A Python script that:
1. Fetches AFL head-to-head odds from multiple Australian bookmakers via one API call
2. Finds the best available price per team
3. Flags any arbitrage opportunities (implied prob sum < 1.0)

---

## Setup

Get a free API key at [puntersedge.online/developers/getting-started](https://puntersedge.online/developers/getting-started) — 1,500 credits/month, no credit card.

Credits are not requests: each endpoint costs 1–5 credits per call. `/v1/sports/{key}/odds` is 1 credit per market requested, `/v1/racing/next-to-go` is 2, `/v1/best-odds/{key}` is 3. The free tier's rate limit is 30 requests/minute.

```bash
pip install requests
```

Two things worth knowing before you write any code:

- The base URL is `https://api.puntersedge.online/v1`, and the key goes in an `X-API-Key` header.
- **Racing is not a sport key.** Horse, harness and greyhound racing live under their own `/v1/racing/*` endpoints. Asking for `/v1/sports/horse_racing/odds` returns 404 (it's the single most common mistake against this API). See [Racing](#horse-racing-a-separate-endpoint-family) below.

---

## Step 1: Fetch AFL Odds

```python
import requests

API_KEY = "your_api_key_here"
BASE_URL = "https://api.puntersedge.online/v1"
headers = {"X-API-Key": API_KEY}

resp = requests.get(
    f"{BASE_URL}/sports/afl/odds",   # sport is a PATH segment, not ?sport=
    params={"markets": "h2h"},       # `markets` is plural and comma-separated
    headers=headers,
    timeout=10,
)
resp.raise_for_status()
events = resp.json()                 # a bare JSON array — there is no "data" wrapper
print(f"Found {len(events)} AFL events")
```

Valid query params here are `markets` (`h2h`, `spreads`, `totals`), `bookmakers`, `competition`, `include_unknown_competition`, `oddsFormat` and `maxAgeMinutes`. An unknown market is a free 422 rather than a billed empty list.

Each event has a `bookmakers` array — one entry per Australian bookmaker quoting that match, each with `markets` → `outcomes`. Eleven bookmakers feed the API (Sportsbet, TAB, TABtouch, Neds, Ladbrokes, Unibet, PointsBet, Betr, BetRight, NextBet — returned under its pre-rebrand key `playup` — and Palmerbet), but **no book covers every fixture**. Measured over 7 days to 2026-08-16, no single NRL match carried more than 5 books and the average match carried under 3. Only AFL, NRL, WNBA and NRLW routinely carry more than one book on the same event.

Each event also carries `data_age_seconds`, `stale` and `stale_bookmakers` so you can see how old the prices are.

---

## Step 2: Find the Best Price Per Team

One wrinkle: bookmakers don't agree on team names, and the API passes each book's own spelling through untouched. One book quotes "Gold Coast", another "Gold Coast SUNS". Group on the raw string and you'll split one team into two rows and understate its best price — so map each outcome onto the event's `home_team` / `away_team` first.

```python
def tokens(name):
    cleaned = "".join(c if c.isalnum() else " " for c in name)
    return {t for t in cleaned.lower().split() if t}


def match_team(outcome_name, home, away):
    """Map a bookmaker's own spelling onto the event's home or away team."""
    got = tokens(outcome_name)
    hits = [t for t in (home, away) if t and got and (got <= tokens(t) or tokens(t) <= got)]
    return hits[0] if len(hits) == 1 else None


def best_prices(event):
    best = {}
    home, away = event.get("home_team"), event.get("away_team")
    for bk in event.get("bookmakers", []):
        for market in bk.get("markets", []):
            if market["key"] != "h2h":
                continue
            for outcome in market.get("outcomes", []):
                team = match_team(outcome["name"], home, away)
                if team is None:
                    continue  # unrecognised name — better unmatched than mis-assigned
                price = outcome["price"]
                if team not in best or price > best[team]["price"]:
                    best[team] = {"price": price, "bookmaker": bk["key"]}
    return best


for event in events:
    books = [b["key"] for b in event.get("bookmakers", [])]
    print(f"\n{event['home_team']} vs {event['away_team']}  ({len(books)} books)")
    for team, info in best_prices(event).items():
        print(f"  {team}: ${info['price']:.2f} @ {info['bookmaker']}")
```

Sample output:
```
Brisbane Lions vs Geelong Cats  (4 books)
  Brisbane Lions: $2.10 @ sportsbet
  Geelong Cats: $1.85 @ betright
```

`home_team` and `away_team` are always present — both are non-nullable columns, and across 2,153 events there is not one null or empty value. They are read with `.get()` only because the response model declares them optional, not because the data omits them.

---

## Step 3: Detect Arbitrage

Arb exists when the sum of implied probabilities (1/odds) across the best prices is less than 1.0 — but only if a stake sits on **every** way the market can settle, and only if every price is still live. Both guards matter more than the formula:

```python
def check_arb(event, prices):
    if len(prices) != 2:
        return False, 0.0          # a side we couldn't price isn't an arb, it's a hole
    if event.get("stale"):
        return False, 0.0          # a book that stopped updating isn't quoting that price
    implied_sum = sum(1 / info["price"] for info in prices.values())
    if implied_sum < 1.0:
        return True, round((1 - implied_sum) * 100, 2)
    return False, 0.0


for event in events:
    is_arb, profit = check_arb(event, best_prices(event))
    if is_arb:
        print(f"ARB FOUND: {event['home_team']} vs {event['away_team']} — {profit}% profit")
```

Be realistic about the hit rate: with at most five books on an AFL or NRL match, genuine two-way arbs are uncommon and short-lived. If you'd rather not maintain this yourself, `GET /v1/arb/sports` (3 credits) runs the same scan server-side and returns `arb_pct` and optimal stakes.

---

## Step 4: Load Into pandas for Modelling

If you're feeding odds into a betting model, you'll want a flat DataFrame:

```python
import pandas as pd

rows = []
for event in events:
    label = f"{event.get('home_team') or '?'} vs {event.get('away_team') or '?'}"
    for bk in event.get("bookmakers", []):
        for market in bk.get("markets", []):
            for outcome in market.get("outcomes", []):
                price = outcome["price"]
                rows.append({
                    "event": label,
                    "commence_time": event["commence_time"],
                    "bookmaker": bk["key"],
                    "market": market["key"],
                    "team": match_team(outcome["name"], event.get("home_team"),
                                       event.get("away_team")) or outcome["name"],
                    "price": price,
                    "implied_prob": round(1 / price, 4),
                    "data_age_seconds": event.get("data_age_seconds"),
                })

df = pd.DataFrame(rows)
print(df.groupby(["event", "team"])["price"].max())  # Best price per team
```

Keeping `data_age_seconds` in the frame is worth the column — it's the age of the oldest contributing quote, so you can drop rows that were priced hours ago before they reach your model.

---

## Horse Racing: A Separate Endpoint Family

Racing has no sport key. It has its own endpoints, its own shape (runners carry a flat `bookmakers` list — no `markets`/`outcomes` nesting), and its own 2-credit price:

```python
races = requests.get(
    f"{BASE_URL}/racing/next-to-go",
    params={"num_races": 5, "categories": "horse", "country": "AU"},
    headers=headers,
    timeout=10,
).json()                             # also a bare JSON array

for race in races:
    print(f"\nR{race.get('race_number')} {race.get('venue')} — {race['start_time']}")
    for runner in race["runners"][:3]:
        quotes = [b for b in runner["bookmakers"] if b.get("win_price")]
        if not quotes:
            continue
        top = max(quotes, key=lambda b: b["win_price"])
        print(f"  {runner['name']}: ${top['win_price']:.2f} @ {top['key']}")
```

Valid params: `num_races`, `categories` (`horse`, `greyhound`, `harness`), `bookmakers`, `country`. Pass `country=AU` — every non-Australian race in the feed is quoted by exactly one bookmaker, so cross-book comparison on those races compares nothing. Scratched runners never appear in `runners`; they're in `scratchings`.

---

## Coverage: What's Actually There

Nineteen sport keys. Every key carries `h2h`; AFL, NRL and NRLW add `spreads` and `totals`, NBA adds `spreads`, and WNBA adds `totals`. Markets shown are those on the current card. The **Books** column is how many bookmakers quote the sport at all, not how many quote a single match:

| Sport | Sport key | Markets | Books |
|---|---|---|---|
| NRL | `nrl` | h2h, spreads, totals | 6 |
| AFL | `afl` | h2h, spreads, totals | 5 |
| WNBA | `wnba` | h2h | 5 |
| NBA | `nba` | h2h, spreads | 3 |
| NRLW | `nrlw` | h2h | 2 |
| `tennis_atp`, `tennis_wta` | as listed | h2h | 3 |
| NFL, `soccer_other` | as listed | h2h | 2 |
| AFLW, NHL, MLB, NCAAF, MMA/UFC, `cricket_test`, `basketball_other` | as listed | h2h | 1 |
| `rugby_union` | as listed | h2h, spreads | 1 |
| Big Bash `cricket_bb`, `cricket_other` | as listed | h2h | seasonal — 0 right now |

Horse, greyhound and harness racing are covered Australia-wide under `/v1/racing/*` by the same 11 bookmakers.

There is no `horse_racing`, `greyhound`, `harness`, `cricket`, `tennis`, `soccer` or `epl` sport key — call `GET /v1/sports` (1 credit) for the live catalogue, and note that a bad key on this endpoint 404s for free rather than billing you for an empty list.

---

## Price Alert in 20 Lines

```python
import time

TARGET_TEAM = "Melbourne Demons"
TARGET_PRICE = 2.50
POLL_SECONDS = 120

while True:
    events = requests.get(
        f"{BASE_URL}/sports/afl/odds",
        params={"markets": "h2h"},
        headers=headers,
        timeout=10,
    ).json()

    for event in events:
        stale_books = event.get("stale_bookmakers", [])
        for bk in event.get("bookmakers", []):
            if bk["key"] in stale_books:
                continue
            for market in bk.get("markets", []):
                for outcome in market.get("outcomes", []):
                    if (match_team(outcome["name"], TARGET_TEAM, None)
                            and outcome["price"] >= TARGET_PRICE):
                        print(f"ALERT: {outcome['name']} @ ${outcome['price']:.2f} ({bk['key']})")

    time.sleep(POLL_SECONDS)
```

Watch the credit burn: each poll is 1 credit, so a 60-second loop is 1,440 credits/day and would eat the whole free month in about 24 hours. The sports feed itself refreshes roughly every 15 minutes, so polling faster than that mostly buys you duplicate data. Run this for the session before a game rather than leaving it up all month.

---

## Full Code on GitHub

All examples (arb scanner, price alerts, horse racing NTG, pandas feed, JS widget) are on GitHub:  
👉 [github.com/Propertyscout001/puntersedge-api-examples](https://github.com/Propertyscout001/puntersedge-api-examples)

---

## Get Started

- 🔑 Free API key: [puntersedge.online/developers/getting-started](https://puntersedge.online/developers/getting-started)
- 📖 API docs: [puntersedge.online/developers](https://puntersedge.online/developers)
- 📊 Coverage: [puntersedge.online/api/coverage](https://puntersedge.online/api/coverage)
- 💰 Pricing: [puntersedge.online/pricing](https://puntersedge.online/pricing)

Free tier is 1,500 credits/month — enough to run every example above many times over. Paid plans start at $9/mo for 7,500 credits, with a racing-focused plan at $19/mo for 40,000. 18+ only, gamble responsibly.
