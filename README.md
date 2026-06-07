# PuntersEdge API — Code Examples

> Australian sports odds API with live bookmaker data for AFL, NRL, horse racing, cricket, tennis and more.
> 
> **API docs & free key:** [puntersedge.online/developers](https://puntersedge.online/developers)

---

## What is PuntersEdge?

[PuntersEdge](https://puntersedge.online) is an Australian bookmaker odds API that aggregates prices from Sportsbet, TAB, Neds, Ladbrokes, Betfair, Unibet, PointsBet and Betr into a single REST/JSON endpoint.

Use it to build:
- 📊 Odds comparison dashboards
- 🤖 Arbitrage scanners
- 📈 Betting model data feeds
- 🔔 Price alert systems
- 🏇 Racing next-to-go widgets

**Free tier:** 500 credits/month — no credit card required.  
**Get your key:** [puntersedge.online/developers/getting-started](https://puntersedge.online/developers/getting-started)

---

## Quick Start

```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  "https://puntersedge.online/api/odds?sport=afl&market=h2h"
```

---

## Examples

### Python

| File | Description |
|------|-------------|
| [afl_odds.py](examples/python/afl_odds.py) | Fetch AFL head-to-head odds and find best price |
| [arb_scanner.py](examples/python/arb_scanner.py) | Simple arbitrage scanner across bookmakers |
| [horse_racing_ntg.py](examples/python/horse_racing_ntg.py) | Horse racing next-to-go feed |
| [price_alert.py](examples/python/price_alert.py) | Alert when odds cross a threshold |
| [betting_model_feed.py](examples/python/betting_model_feed.py) | Feed bookmaker odds into a pandas DataFrame |

### JavaScript / Node

| File | Description |
|------|-------------|
| [afl_odds.js](examples/javascript/afl_odds.js) | Fetch AFL odds with fetch API (browser/Node) |
| [odds_widget.js](examples/javascript/odds_widget.js) | Simple odds comparison widget (vanilla JS) |
| [nrl_alerts.js](examples/node/nrl_alerts.js) | NRL price alert with Node.js + polling |

---

## Supported Sports

| Sport | Slug | Markets |
|-------|------|---------|
| AFL | `afl` | H2H, Line, Totals |
| NRL | `nrl` | H2H, Line, Totals |
| Horse Racing | `horse_racing` | Win, Place, Each Way |
| Greyhound Racing | `greyhound` | Win, Place |
| Harness Racing | `harness` | Win, Place |
| Cricket | `cricket` | Match Winner, Top Batsman |
| Tennis | `tennis` | Match Winner, Set Betting |
| NBA | `nba` | H2H, Spreads, Totals |
| Soccer (EPL/A-League) | `soccer` | H2H, BTTS, Over/Under |
| Rugby Union | `rugby_union` | H2H, Line |
| MMA/UFC | `mma` | Moneyline, Method of Victory |

---

## Supported Bookmakers

- **Sportsbet** — Australia's highest-volume bookmaker
- **TAB** — Legacy racing & sports operator
- **Neds** — Competitive AFL/NRL pricing
- **Ladbrokes** — Broad sport and racing coverage
- **Betfair** — Exchange prices, often best available
- **Unibet** — International brand, AU market
- **PointsBet** — Australian-founded, spread markets
- **Betr** — Newer AU bookmaker, micro-betting focus

---

## Authentication

All requests require an `X-API-Key` header:

```python
import requests

headers = {"X-API-Key": "your_api_key_here"}
response = requests.get("https://puntersedge.online/api/odds", params={"sport": "afl"}, headers=headers)
```

Get your free key at [puntersedge.online/developers/getting-started](https://puntersedge.online/developers/getting-started)

---

## Rate Limits

| Plan | Credits/month | Rate |
|------|--------------|------|
| Free | 500 | 10 req/min |
| Starter | 10,000 | 60 req/min |
| Pro | 100,000 | 300 req/min |
| Enterprise | Unlimited | Custom |

---

## Links

- 🌐 Website: [puntersedge.online](https://puntersedge.online)
- 📖 API Docs: [puntersedge.online/developers](https://puntersedge.online/developers)
- 🚀 Getting Started: [puntersedge.online/developers/getting-started](https://puntersedge.online/developers/getting-started)
- 📊 API Coverage: [puntersedge.online/api/coverage](https://puntersedge.online/api/coverage)
- 💰 Pricing: [puntersedge.online/api/pricing](https://puntersedge.online/api/pricing)

---

## Responsible Gambling

PuntersEdge provides odds data for informational and analytical purposes. Always gamble responsibly. 18+ only. If gambling is causing problems, contact the [National Gambling Helpline](https://www.gamblinghelponline.org.au) on 1800 858 858.
