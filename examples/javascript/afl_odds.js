/**
 * PuntersEdge API — AFL Odds (browser / Node 18+ fetch)
 * Fetch AFL head-to-head odds and display the best price per team.
 *
 * Free tier: 1,500 credits per month, no credit card. Credits are not requests —
 * this endpoint bills 1 credit per requested market, so one h2h call costs 1.
 *
 * Get a free API key: https://puntersedge.online/developers/getting-started
 * API docs: https://puntersedge.online/developers/sports-odds-api-australia
 */

const API_KEY = "your_api_key_here";
const BASE_URL = "https://api.puntersedge.online/v1";

async function getAflOdds() {
  // The sport is a PATH segment, and the query parameter is `markets` (plural,
  // comma-separated: h2h,spreads,totals). Other valid parameters: bookmakers,
  // competition, include_unknown_competition, oddsFormat, maxAgeMinutes.
  // Racing is NOT a sport_key — it lives under /v1/racing/* (e.g. next-to-go).
  const url = new URL(`${BASE_URL}/sports/afl/odds`);
  url.searchParams.set("markets", "h2h");

  const res = await fetch(url.toString(), {
    headers: { "X-API-Key": API_KEY },
  });

  if (!res.ok) {
    // Errors are RFC 7807 problem+json: { type, title, status, detail }.
    // 401 = bad/missing key, 402 = monthly credits exhausted,
    // 429 = rate limited (honour the Retry-After header, in seconds).
    let note = "";
    try {
      const problem = await res.json();
      const detail = typeof problem.detail === "string" ? problem.detail : problem.title;
      if (detail) note = ` — ${detail}`;
    } catch (_) {
      /* body was not JSON */
    }
    throw new Error(`API error ${res.status}${note}`);
  }

  // This endpoint returns a BARE JSON array of events. There is no { data: ... }
  // wrapper, so do not reach for one.
  return res.json();
}

/**
 * Fold a bookmaker's outcome name onto the event's canonical home_team/away_team.
 * Books do not agree on team names: on a live AFL card TAB sends "Brisbane" and
 * "Gold Coast" where Sportsbet sends "Brisbane Lions" and "Gold Coast SUNS", so
 * keying on the raw name splits one team into two rows. Case-insensitive prefix
 * matching in either direction handles those. It does NOT handle abbreviations
 * that share no prefix — "GWS"/"GWS GIANTS" will not fold onto "Greater Western
 * Sydney", nor "Wst Bulldogs" onto "Western Bulldogs". Names that fail to match
 * are kept under their raw spelling rather than dropped; a production app wants
 * a real alias table.
 */
function canonicalTeam(event, name) {
  const raw = name.toLowerCase();
  for (const team of [event.home_team, event.away_team]) {
    if (!team) continue;
    const canon = team.toLowerCase();
    if (raw.startsWith(canon) || canon.startsWith(raw)) return team;
  }
  return name;
}

function bestPrices(event) {
  // Event shape: { id, sport_key, sport_title, competition, commence_time,
  // home_team, away_team, odds_format, bookmakers[], data_age_seconds,
  // freshest_age_seconds, stale, stale_bookmakers[], data_quality, ... }
  // Each bookmaker: { key, title, last_update, age_seconds, stale, quality,
  // markets[] } and each market: { key, quality, outcomes[{ name, price }] }.
  const best = {};
  for (const bk of event.bookmakers || []) {
    for (const market of bk.markets || []) {
      if (market.key !== "h2h") continue;
      for (const outcome of market.outcomes || []) {
        const team = canonicalTeam(event, outcome.name);
        const price = outcome.price;
        if (typeof price !== "number") continue;
        if (!best[team] || price > best[team].price) {
          best[team] = { price, bookmaker: bk.key };
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
    // commence_time is UTC ISO 8601. Coverage on sports is thinner than on
    // racing: AFL h2h currently comes from about five books (betright,
    // palmerbet, pointsbetau, sportsbet, tab), spreads from three, and some
    // sports carry only one — so "best price" here means best of what is live,
    // not best of the whole market.
    const bookCount = (event.bookmakers || []).length;
    console.log(`${event.home_team} vs ${event.away_team}  |  ${event.commence_time}`);
    console.log(
      `  ${bookCount} bookmaker(s)` +
        // data_age_seconds is the age of the OLDEST contributing price, not the
        // newest; stale_bookmakers names the books that have stopped updating.
        (event.data_age_seconds != null ? `, oldest price ${event.data_age_seconds}s old` : "") +
        (event.stale ? "  [STALE]" : "") +
        (event.stale_bookmakers && event.stale_bookmakers.length
          ? `  stale: ${event.stale_bookmakers.join(", ")}`
          : "")
    );

    const prices = bestPrices(event);
    for (const [team, { price, bookmaker }] of Object.entries(prices)) {
      console.log(`  ${team.padEnd(30)} Best: $${price.toFixed(2)}  (${bookmaker})`);
    }
    console.log();
  }
}

main().catch((err) => console.error(err.message));
