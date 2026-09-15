# PuntersEdge API — Code Examples

> Australian bookmaker odds API — live sports odds for AFL, NRL, NBA, tennis and more, plus a
> separate racing feed for horse, harness and greyhound racing.
>
> **API docs & free key:** [puntersedge.online/developers](https://puntersedge.online/developers)

---

## What is PuntersEdge?

[PuntersEdge](https://puntersedge.online) aggregates Australian bookmaker prices into a single
REST/JSON API. Racing is served from **14 Australian bookmakers** — the live count and per-book
freshness are published at [puntersedge.online/coverage-report](https://puntersedge.online/coverage-report),
so use that page rather than any number in a README. Sports odds come from a subset of those books.

Use it to build:
- 📊 Odds comparison dashboards
- 🤖 Arbitrage scanners
- 📈 Betting model data feeds
- 🔔 Price alert systems
- 🏇 Racing next-to-go widgets

**Free tier:** 1,500 credits/month — no credit card required. Credits are not requests: most
data endpoints cost 1–5 credits each (see [Credits & Rate Limits](#credits--rate-limits) below).

**Get your key:** [puntersedge.online/developers/getting-started](https://puntersedge.online/developers/getting-started)

---

## Start with the repo for what you are building

This repository is the index. The examples further down are small single-file snippets that
show a call and its response shape. If you are actually building something, one of these
standalone repos is closer to it — each one runs on its own, and each has a path that works
**before you register**.

| Building… | Repo | Runs with no key |
|---|---|---|
| A Python client for AU racing | [australian-racing-api-python](https://github.com/Propertyscout001/australian-racing-api-python) | `python3 quickstart.py` |
| A racing odds board in the browser | [horse-racing-odds-dashboard](https://github.com/Propertyscout001/horse-racing-odds-dashboard) | open `index.html` |
| AFL odds, best price and overround | [afl-odds-api-example](https://github.com/Propertyscout001/afl-odds-api-example) | yes — Python and Node |
| An NRL model feed as CSV | [nrl-odds-api-python](https://github.com/Propertyscout001/nrl-odds-api-python) | yes |
| Tracking firmers and drifters | [racing-price-movement-tracker](https://github.com/Propertyscout001/racing-price-movement-tracker) | yes |
| A Discord bot | [sports-odds-discord-bot](https://github.com/Propertyscout001/sports-odds-discord-bot) | `demo.py`, no Discord token |
| Your own backend over the API | [racing-data-fastapi](https://github.com/Propertyscout001/racing-data-fastapi) | starts and answers keyless |
| Odds inside Claude, Cursor or Claude Code | [puntersedge-mcp-examples](https://github.com/Propertyscout001/puntersedge-mcp-examples) | yes |

Official clients, if you would rather not write the HTTP layer:
[**puntersedge-python**](https://github.com/Propertyscout001/puntersedge-python) (`pip install
puntersedge`) · [**puntersedge-node**](https://github.com/Propertyscout001/puntersedge-node)
(`npm install puntersedge`) · [**puntersedge-mcp**](https://github.com/Propertyscout001/puntersedge-mcp)
(MCP server). Also [puntersedge-examples](https://github.com/Propertyscout001/puntersedge-examples)
(six standalone Python scripts) and
[au-racing-odds-dashboard](https://github.com/Propertyscout001/au-racing-odds-dashboard)
(a next-to-go board as one dependency-free Python file).

---

## Quick Start

```bash
curl --compressed -H "X-API-Key: YOUR_API_KEY" \
  "https://api.puntersedge.online/v1/sports/afl/odds?markets=h2h"
```

Two things to note before you write a client against it:

- The base URL is `https://api.puntersedge.online/v1` — a subdomain, not a path on the website.
- This endpoint returns a **bare JSON array of events**, not an object with an `events` key.

```jsonc
[
  {
    "id": "event_123",
    "sport_key": "afl",
    "sport_title": "AFL",
    "commence_time": "2026-06-07T09:30:00Z",
    "home_team": "Brisbane Lions",
    "away_team": "Collingwood",
    "bookmakers": [
      { "key": "sportsbet", "title": "Sportsbet",
        "markets": [ { "key": "h2h", "outcomes": [ { "name": "Brisbane Lions", "price": 1.90 } ] } ] }
    ],
    "data_age_seconds": 15,
    "stale": false
  }
]
```

---

## Examples

### Python

| File | Description |
|------|-------------|
| [afl_odds.py](examples/python/afl_odds.py) | Fetch AFL head-to-head odds and find the best price per team |
| [arb_scanner.py](examples/python/arb_scanner.py) | Cross-book arbitrage scanner over sports h2h markets |
| [horse_racing_ntg.py](examples/python/horse_racing_ntg.py) | Racing next-to-go feed with runner prices |
| [price_alert.py](examples/python/price_alert.py) | Alert when odds drift out past a threshold |
| [betting_model_feed.py](examples/python/betting_model_feed.py) | Feed bookmaker odds into a pandas DataFrame |

### JavaScript / Node

| File | Description |
|------|-------------|
| [afl_odds.js](examples/javascript/afl_odds.js) | Fetch AFL odds with the fetch API (browser / Node 18+) |
| [odds_widget.js](examples/javascript/odds_widget.js) | Simple odds comparison widget (vanilla JS) |
| [nrl_alerts.js](examples/node/nrl_alerts.js) | NRL price alert with Node.js + polling |

Every example is runnable as-is once you paste your key into `API_KEY`.

---

## Supported Sports

Sports odds live at `GET /v1/sports/{sport_key}/odds` — the sport is a **path parameter**, not
`?sport=`. The market filter is `markets` (plural) and the only valid values are `h2h`,
`spreads` and `totals`.

**Racing is not a sport_key.** There is no `horse_racing`, `greyhound` or `harness` key —
passing one returns 404. Racing has its own endpoint family under `/v1/racing/*`.

Coverage is genuinely thin outside the big AU codes, and it moves with the season. The table
below was **re-measured live on 15 September 2026** by calling `/v1/sports/{key}/odds?markets=h2h`
for every key in the live catalogue and counting distinct bookmakers in the response. A code with
no fixtures scheduled returns an empty array rather than an error.

| Sport | `sport_key` | Fixtures upcoming | Books quoting h2h |
|-------|-------------|------------------:|------------------:|
| AFL | `afl` | 3 | 6 |
| NRL | `nrl` | 2 | 6 |
| NBA | `nba` | 21 | 5 |
| Rugby Union | `rugby_union` | 27 | 4 |
| Tennis WTA | `tennis_wta` | 39 | 4 |
| Tennis ATP | `tennis_atp` | 35 | 4 |
| WNBA | `wnba` | 8 | 4 |
| NFL | `nfl` | 48 | 3 |
| AFLW | `aflw` | 18 | 3 |
| Super League | `super_league` | 2 | 3 |
| NRLW | `nrlw` | 2 | 2 |
| MLB | `mlb` | 28 | 2 |
| College Football | `ncaaf` | 40 | 2 |
| Soccer — EPL | `soccer_epl` | 20 | 2 |
| Soccer — other competitions | `soccer_other` | 45 | 2 |
| Basketball — other competitions | `basketball_other` | 13 | 2 |
| MMA/UFC | `mma` | 22 | 1 |
| NHL | `nhl` | 5 | 1 |
| Cricket — other competitions | `cricket_other` | 10 | 1 |
| Test Cricket | `cricket_test` | 0 | — |

Read that honestly: on most individual fixtures outside AFL, NRL and NBA only one or two books
quote. **Racing is where the bookmaker depth is** — a median of 14 books per Australian race
against a maximum of 6 on any sport. If you need many books on one market, you want the racing
endpoints, not the sports ones.

Those twenty keys are the complete list. There is no `cricket_bb` / Big Bash key — an earlier
version of this table listed one and it 404s. There is also no `cricket`, `tennis`, `soccer` or
`epl` key; those families are split by competition above.

Call `GET /v1/sports` for the live catalogue rather than hardcoding this table. There is no
`cricket`, `tennis`, `soccer` or `epl` key — those families are split by competition above.

### Racing

```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  "https://api.puntersedge.online/v1/racing/next-to-go?num_races=5&country=AU"
```

Valid parameters: `num_races`, `categories` (horse, harness, greyhound), `bookmakers`,
`country`. It also returns a **bare JSON array**, one entry per race, each with a `runners`
array carrying a per-bookmaker `win_price`, plus `place_price` only where that book quotes one — the key is **absent**, not null, so read it with `.get()` rather than `[]`.

---

## Supported Bookmakers

**Racing — 14 Australian bookmakers** (live count: [coverage report](https://puntersedge.online/coverage-report)).
Keys you will see in payloads include:

| Bookmaker | Key | Bookmaker | Key |
|-----------|-----|-----------|-----|
| Sportsbet | `sportsbet` | Neds | `neds` |
| TAB | `tab` | Unibet | `unibet` |
| Ladbrokes | `ladbrokes_au` | PointsBet | `pointsbetau` |
| BetRight | `betright` | NextBet | `playup` |
| Betr | `betr_au` | TABtouch | `tabtouch` |
| Palmerbet | `palmerbet` | BetDeluxe | `betdeluxe` |
| BetGold | `betgold` | BoostBet | `boostbet` |

Two things that catch people out: **NextBet is returned under its pre-rebrand key `playup`**,
and **Betfair Exchange prices are never returned** — the exchange is ingested for internal reference
only and withheld from customer responses pending a data licence, so it is not counted above and
you will not see it in a payload.

**Sports — 6 books at the time of writing.** Only Sportsbet, TAB, Ladbrokes, BetRight, PointsBet and Palmerbet supply
sports odds. Betr, Neds, Unibet, NextBet and TABtouch are racing-only here, and not all six
sports books quote every fixture — which is why the counts in the sports table top out at 5.

---

## Authentication

All requests require an `X-API-Key` header:

```python
import requests

API_KEY = "your_api_key_here"
BASE_URL = "https://api.puntersedge.online/v1"

resp = requests.get(
    f"{BASE_URL}/sports/afl/odds",
    params={"markets": "h2h"},
    headers={"X-API-Key": API_KEY},
    timeout=15,
)
resp.raise_for_status()
events = resp.json()  # bare list of events
print(f"{len(events)} AFL events")
```

Reuse the connection (`requests.Session()`) and send `Accept-Encoding: gzip` — on this API a
reused connection cuts observed latency by roughly 70%, and gzip shrinks a typical odds
response about 9x.

Get your free key at [puntersedge.online/developers/getting-started](https://puntersedge.online/developers/getting-started)

---

## Credits & Rate Limits

Two independent budgets: how fast you may call, and how much you may call per month. Exceed
the rate and you get `429` (clears in 60s). Exhaust credits and you get `402` — retrying will
never clear that; credits reset on the 1st of each calendar month at 00:00 UTC.

| Plan | Price (AUD/mo) | Credits/month | Requests/minute |
|------|---------------|---------------|-----------------|
| Free | $0 | 1,500 | 30 |
| Hobby | $9 | 7,500 | 60 |
| Standard | $29 | 75,000 | 200 |
| Plus | $49 | 140,000 | 250 |
| Business | $99 | 300,000 | 300 |
| Unlimited | $249 | 5,000,000 | 2,000 |

Read from the [live pricing page](https://puntersedge.online/api/pricing) on 15 September 2026.
An earlier version of this table named a `Starter` and a `Pro Plus` tier and a `$19` racing
plan; those names are gone, so check the pricing page rather than this file — a tier rename is
invisible in a README until somebody quotes it back at you.

Historical odds, price movements, webhooks and the closing-line archive are **403 on Free and
Hobby**, which is worth knowing before you build on them.

Credits are charged per call, and the cost varies by endpoint:

| Endpoint | Cost |
|----------|------|
| `GET /v1/sports` | 1 credit |
| `GET /v1/sports/{sport_key}/odds` | 1 credit **per requested market** |
| `GET /v1/racing/next-to-go` | 2 credits |
| `GET /v1/best-odds/{sport_key}` | 3 credits |
| `GET /v1/racing/best-odds` | 3 credits |
| `GET /v1/usage` | free |

Every **metered** response carries `X-Credits-Remaining` (alongside `X-Credits-Cost`, `X-Credits-Used` and `X-Credits-Limit`), so you can track spend without a separate call. Error responses carry none of them, and on the Unlimited plan the value is the string `"unlimited"` rather than a number.
Unknown sport keys and unknown market names are rejected before billing, so a typo costs
nothing.

---

## Links

- 🌐 Website: [puntersedge.online](https://puntersedge.online)
- 📖 API Docs: [puntersedge.online/developers](https://puntersedge.online/developers)
- 🚀 Getting Started: [puntersedge.online/developers/getting-started](https://puntersedge.online/developers/getting-started)
- 📚 API Reference: [puntersedge.online/developers/api-reference](https://puntersedge.online/developers/api-reference)
- ⏱️ Rate Limits: [puntersedge.online/developers/rate-limits](https://puntersedge.online/developers/rate-limits)
- 📊 API Coverage: [puntersedge.online/api/coverage](https://puntersedge.online/api/coverage)
- 💰 Pricing: [puntersedge.online/api/pricing](https://puntersedge.online/api/pricing)
- 🧪 Live schema: [api.puntersedge.online/docs](https://api.puntersedge.online/docs) · [openapi.json](https://api.puntersedge.online/openapi.json) · [Postman collection](https://api.puntersedge.online/postman.json)

Two sandbox endpoints need no key at all, if you want to see the shape before signing up:

```bash
curl "https://api.puntersedge.online/v1/demo/racing/next-to-go"
curl "https://api.puntersedge.online/v1/demo/best-odds?sport=nrl"
```

Sandbox payloads are truncated and wrapped in an object — use them to learn field names, not
envelope shape.

---

## Responsible Gambling

PuntersEdge provides odds data for informational and analytical purposes. Always gamble
responsibly. 18+ only. If gambling is causing problems, contact the
[National Gambling Helpline](https://www.gamblinghelponline.org.au) on 1800 858 858.
