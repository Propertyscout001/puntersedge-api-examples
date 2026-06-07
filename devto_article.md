# How to Build an Australian Sports Odds Comparison App in Python

If you've ever wanted to compare AFL, NRL or horse racing odds across multiple Australian bookmakers without scraping 8 different websites — this is for you.

In this tutorial I'll show you how to use the [PuntersEdge API](https://puntersedge.online/developers) to fetch live Australian bookmaker odds and find the best available price in a few lines of Python.

---

## What We're Building

A Python script that:
1. Fetches AFL head-to-head odds from multiple Australian bookmakers via one API call
2. Finds the best available price per team
3. Flags any arbitrage opportunities (implied prob sum < 1.0)

---

## Setup

Get a free API key at [puntersedge.online/developers/getting-started](https://puntersedge.online/developers/getting-started) (500 credits/month free, no credit card).

```bash
pip install requests
```

---

## Step 1: Fetch AFL Odds

```python
import requests

API_KEY = "your_api_key_here"
headers = {"X-API-Key": API_KEY}

resp = requests.get(
    "https://puntersedge.online/api/odds",
    params={"sport": "afl", "market": "h2h"},
    headers=headers,
)
events = resp.json()["data"]
print(f"Found {len(events)} AFL events")
```

The response is a list of events. Each event has a `bookmakers` array — one entry per supported Australian bookmaker (Sportsbet, TAB, Neds, Ladbrokes, Betfair, Unibet, PointsBet, Betr).

---

## Step 2: Find the Best Price Per Team

```python
def best_prices(event):
    best = {}
    for bk in event["bookmakers"]:
        for market in bk["markets"]:
            if market["key"] != "h2h":
                continue
            for outcome in market["outcomes"]:
                team = outcome["name"]
                price = outcome["price"]
                if team not in best or price > best[team]["price"]:
                    best[team] = {"price": price, "bookmaker": bk["key"]}
    return best

for event in events:
    print(f"\n{event['home_team']} vs {event['away_team']}")
    for team, info in best_prices(event).items():
        print(f"  {team}: ${info['price']:.2f} @ {info['bookmaker']}")
```

Sample output:
```
Brisbane Lions vs Geelong Cats
  Brisbane Lions: $2.10 @ sportsbet
  Geelong Cats: $1.85 @ betfair
```

---

## Step 3: Detect Arbitrage

Arb exists when the sum of implied probabilities (1/odds) across the best prices is less than 1.0. That means you could back both sides and guarantee a profit.

```python
def check_arb(prices):
    implied_sum = sum(1 / info["price"] for info in prices.values())
    if implied_sum < 1.0:
        profit_pct = round((1 - implied_sum) * 100, 2)
        return True, profit_pct
    return False, 0

for event in events:
    prices = best_prices(event)
    is_arb, profit = check_arb(prices)
    if is_arb:
        print(f"ARB FOUND: {event['home_team']} vs {event['away_team']} — {profit}% profit")
```

---

## Step 4: Load Into pandas for Modelling

If you're feeding odds into a betting model, you'll want a flat DataFrame:

```python
import pandas as pd

rows = []
for event in events:
    for bk in event["bookmakers"]:
        for market in bk["markets"]:
            for outcome in market["outcomes"]:
                rows.append({
                    "event": f"{event['home_team']} vs {event['away_team']}",
                    "bookmaker": bk["key"],
                    "team": outcome["name"],
                    "price": outcome["price"],
                    "implied_prob": round(1 / outcome["price"], 4),
                })

df = pd.DataFrame(rows)
print(df.groupby(["event", "team"])["price"].max())  # Best price per team
```

---

## Supported Sports

The API covers all major Australian betting markets:

- **AFL** — H2H, line, totals
- **NRL** — H2H, line, State of Origin
- **Horse Racing** — Win, place, next-to-go
- **Greyhound & Harness Racing**
- **Cricket** — BBL, Test, ODI
- **Tennis** — ATP/WTA including Australian Open
- **NBA, Soccer, Rugby Union, MMA/UFC**

---

## Price Alert in 20 Lines

```python
import time

TARGET_TEAM = "Melbourne Demons"
TARGET_PRICE = 2.50

while True:
    events = requests.get(
        "https://puntersedge.online/api/odds",
        params={"sport": "afl", "market": "h2h"},
        headers=headers,
    ).json()["data"]

    for event in events:
        for bk in event["bookmakers"]:
            for market in bk["markets"]:
                for outcome in market["outcomes"]:
                    if outcome["name"] == TARGET_TEAM and outcome["price"] >= TARGET_PRICE:
                        print(f"ALERT: {TARGET_TEAM} @ ${outcome['price']:.2f} ({bk['key']})")

    time.sleep(60)
```

---

## Full Code on GitHub

All examples (arb scanner, price alerts, horse racing NTG, pandas feed, JS widget) are on GitHub:  
👉 [github.com/your-username/puntersedge-api-examples](https://github.com/your-username/puntersedge-api-examples)

---

## Get Started

- 🔑 Free API key: [puntersedge.online/developers/getting-started](https://puntersedge.online/developers/getting-started)
- 📖 API docs: [puntersedge.online/developers](https://puntersedge.online/developers)
- 📊 Coverage: [puntersedge.online/api/coverage](https://puntersedge.online/api/coverage)

Free tier is 500 credits/month — enough to test all the examples above. 18+ only, gamble responsibly.
