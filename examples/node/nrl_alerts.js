/**
 * PuntersEdge API — NRL Price Alert (Node.js)
 * Polls the API every 60 seconds and logs when odds cross a target.
 *
 * Usage: node nrl_alerts.js
 * Requires Node 18+ (built-in fetch) or install node-fetch.
 *
 * Get a free API key: https://puntersedge.online/developers/getting-started
 * API docs: https://puntersedge.online/nrl-odds-api
 */

const API_KEY = "your_api_key_here";
const BASE_URL = "https://puntersedge.online/api";
const POLL_INTERVAL_MS = 60_000;

// Configure alerts: { team: targetPrice }
const ALERTS = {
  "Melbourne Storm": 2.20,
  "South Sydney Rabbitohs": 3.00,
  "Penrith Panthers": 1.90,
};

async function getOdds(sport = "nrl") {
  const res = await fetch(`${BASE_URL}/odds?sport=${sport}&market=h2h`, {
    headers: { "X-API-Key": API_KEY },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return (await res.json()).data || [];
}

function extractBestPrices(events) {
  const prices = {};
  for (const event of events) {
    for (const bk of event.bookmakers || []) {
      for (const market of bk.markets || []) {
        if (market.key !== "h2h") continue;
        for (const { name, price } of market.outcomes || []) {
          if (!prices[name] || price > prices[name].price) {
            prices[name] = { price, bookmaker: bk.key };
          }
        }
      }
    }
  }
  return prices;
}

async function poll() {
  const now = new Date().toLocaleTimeString("en-AU");
  try {
    const events = await getOdds("nrl");
    const prices = extractBestPrices(events);

    for (const [team, target] of Object.entries(ALERTS)) {
      const current = prices[team];
      if (!current) {
        console.log(`[${now}] ${team}: not found in markets`);
        continue;
      }
      const flag = current.price >= target ? "🔔 ALERT" : "  watch";
      console.log(
        `[${now}] ${flag}  ${team.padEnd(28)} $${current.price.toFixed(2)} @ ${current.bookmaker}` +
        (current.price >= target ? `  (target $${target.toFixed(2)} hit!)` : `  (target $${target.toFixed(2)})`)
      );
    }
  } catch (e) {
    console.error(`[${now}] Error: ${e.message}`);
  }
}

console.log("🏉 NRL Price Alert — PuntersEdge API");
console.log(`   Watching ${Object.keys(ALERTS).length} teams. Polling every ${POLL_INTERVAL_MS / 1000}s.\n`);
poll();
setInterval(poll, POLL_INTERVAL_MS);
