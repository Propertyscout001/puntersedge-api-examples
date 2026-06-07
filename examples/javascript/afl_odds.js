/**
 * PuntersEdge API — AFL Odds (Browser / Node fetch)
 * Fetch AFL head-to-head odds and display best price per team.
 *
 * Get a free API key: https://puntersedge.online/developers/getting-started
 * API docs: https://puntersedge.online/afl-odds-api
 */

const API_KEY = "your_api_key_here";
const BASE_URL = "https://puntersedge.online/api";

async function getAflOdds() {
  const url = new URL(`${BASE_URL}/odds`);
  url.searchParams.set("sport", "afl");
  url.searchParams.set("market", "h2h");

  const res = await fetch(url.toString(), {
    headers: { "X-API-Key": API_KEY },
  });

  if (!res.ok) throw new Error(`API error: ${res.status}`);
  const json = await res.json();
  return json.data || [];
}

function bestPrices(event) {
  const best = {};
  for (const bk of event.bookmakers || []) {
    for (const market of bk.markets || []) {
      if (market.key !== "h2h") continue;
      for (const outcome of market.outcomes || []) {
        const { name, price } = outcome;
        if (!best[name] || price > best[name].price) {
          best[name] = { price, bookmaker: bk.key };
        }
      }
    }
  }
  return best;
}

async function main() {
  const events = await getAflOdds();
  console.log(`Found ${events.length} AFL events\n`);

  for (const event of events) {
    console.log(`${event.home_team} vs ${event.away_team}  |  ${event.commence_time}`);
    const prices = bestPrices(event);
    for (const [team, { price, bookmaker }] of Object.entries(prices)) {
      console.log(`  ${team.padEnd(30)} Best: $${price.toFixed(2)}  (${bookmaker})`);
    }
    console.log();
  }
}

main().catch(console.error);
