/**
 * PuntersEdge API — NRL Price Alert (Node.js)
 * Polls the API and logs when the best available head-to-head price on a team
 * drifts out to a target you set.
 *
 * Usage: node nrl_alerts.js
 * Requires Node 18+ (built-in fetch).
 *
 * Get a free API key: https://puntersedge.online/developers/getting-started
 * API docs:           https://puntersedge.online/developers
 * NRL odds page:      https://puntersedge.online/nrl-odds
 *
 * CREDIT COST — read before leaving this running.
 * GET /v1/sports/{sport_key}/odds costs 1 credit per market requested. This script
 * asks for one market (h2h), so one poll = 1 credit. The free tier is 1,500 credits
 * per MONTH, so a 5-minute poll running 24/7 costs ~288 credits/day and would drain
 * the free allowance in about five days. The free tier suits short sessions in the
 * hours before a match; for continuous running see
 * https://puntersedge.online/api/pricing
 *
 * Don't poll faster than this. The upstream sports feed refreshes roughly every 15
 * minutes and the API caches odds responses for 30 seconds, so a 60-second poll burns
 * 5x the credits to re-read the same numbers.
 */

const API_KEY = "your_api_key_here";
const BASE_URL = "https://api.puntersedge.online/v1";
const SPORT_KEY = "nrl"; // racing is NOT a sport_key — it lives under /v1/racing/*
const POLL_INTERVAL_MS = 5 * 60_000;

// Configure alerts: { team: targetPrice }. Fires when the best price is at or longer
// than the target. Names are matched loosely, so "Melbourne Storm" and "Storm" both
// work — see the matching notes below for why loose matching is necessary here. Use
// the club name rather than a heavy abbreviation. An abbreviation only matches on cards
// where a book actually publishes it — TAB really does say "Nth Qld" — so a full club
// name matches on every card, while an abbreviation matches only on some.
const ALERTS = {
  "Melbourne Storm": 3.5,
  "South Sydney Rabbitohs": 3.0,
  "Penrith Panthers": 1.5,
};

// Reject a team match weaker than this. Tuned to accept "Storm" -> "Melbourne Storm"
// while rejecting "Brisbane Broncos" -> "London Broncos", which really do both appear
// under this sport key.
const MIN_TEAM_MATCH = 0.5;

// COVERAGE, honestly: five bookmakers price NRL h2h — sportsbet, tab, betright,
// palmerbet and pointsbetau — and pointsbetau carries only about half the fixtures.
// "Best price" below means best of those, not a whole-of-market survey. The `nrl` key
// also carries English rugby league (RFL Championship) alongside the NRL; add
// &competition=NRL to narrow it if that matters to you.

// --- Team name matching ------------------------------------------------------
// Bookmakers do NOT agree on team names, and the API returns each book's own spelling
// verbatim. On one live card betright said "North Queensland Cowboys" where TAB said
// "Nth Qld", and "South Sydney Rabbitohs" also appeared as "Souths". Keying a map on
// outcome.name therefore splits one team into several buckets and silently drops
// whichever book spells it differently — so every outcome is resolved to a side of its
// own event instead.

const normalize = (s) => (s || "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
const tokens = (s) => normalize(s).split(" ").filter(Boolean);

// Jaccard overlap over tokens, treating a token pair as equal when one is a prefix of
// the other ("syd" ~ "sydney", "souths" ~ "south", "ill" ~ "illawarra").
function similarity(a, b) {
  const ta = tokens(a);
  const tb = tokens(b);
  if (!ta.length || !tb.length) return 0;
  const used = new Set();
  let hits = 0;
  for (const x of ta) {
    for (let i = 0; i < tb.length; i++) {
      if (used.has(i)) continue;
      const y = tb[i];
      const prefix = x.length >= 3 && y.length >= 3 && (x.startsWith(y) || y.startsWith(x));
      if (x === y || prefix) {
        used.add(i);
        hits++;
        break;
      }
    }
  }
  return hits / (ta.length + tb.length - hits);
}

// Assign a market's outcomes to home/away. Every NRL h2h market carries exactly two
// outcomes (no draw), so both pairings are scored and the better one wins. That fixes
// the hard cases by elimination: "Nth Qld" matches neither team name on its own, but
// pairing it opposite a confidently matched "Parramatta" resolves it.
function sideOf(market, homeTeam, awayTeam) {
  const outs = market.outcomes || [];
  if (outs.length === 2) {
    const [o0, o1] = outs;
    const straight = similarity(o0.name, homeTeam) + similarity(o1.name, awayTeam);
    const swapped = similarity(o0.name, awayTeam) + similarity(o1.name, homeTeam);
    if (straight === swapped) return {}; // ambiguous — skip rather than guess
    return straight > swapped ? { home: o0, away: o1 } : { home: o1, away: o0 };
  }
  // Defensive fallback for anything that isn't a clean two-way market.
  const picked = {};
  for (const o of outs) {
    const h = similarity(o.name, homeTeam);
    const a = similarity(o.name, awayTeam);
    if (h > a && h > 0) picked.home = o;
    else if (a > h && a > 0) picked.away = o;
  }
  return picked;
}

// Collapse one event into two sides, each with its best (longest) price and every
// spelling the books used for it. Books the API flags stale are skipped — alerting on
// a price that stopped updating hours ago is worse than not alerting at all.
function resolveEvent(event) {
  const sides = {
    home: { aliases: new Set(), best: null },
    away: { aliases: new Set(), best: null },
  };
  if (event.home_team) sides.home.aliases.add(event.home_team);
  if (event.away_team) sides.away.aliases.add(event.away_team);

  const skippedStale = [];
  for (const bk of event.bookmakers || []) {
    if (bk.stale === true) {
      skippedStale.push(bk.key);
      continue;
    }
    for (const market of bk.markets || []) {
      if (market.key !== "h2h") continue;
      // Each market carries a `quality` object. status "bad" means the API found a
      // price outside 1.01-100 or fewer than two outcomes. Note this does NOT catch a
      // merely unusual price: a book that is simply well off the others still reads
      // "ok", and the best price in a five-book market can be a mispricing rather
      // than a gift. Treat an alert as a prompt to go and look, not as a verdict.
      if (market.quality && market.quality.status === "bad") continue;
      const picked = sideOf(market, event.home_team, event.away_team);
      for (const side of ["home", "away"]) {
        const outcome = picked[side];
        if (!outcome || typeof outcome.price !== "number") continue;
        if (outcome.name) sides[side].aliases.add(outcome.name);
        if (!sides[side].best || outcome.price > sides[side].best.price) {
          sides[side].best = { price: outcome.price, bookmaker: bk.key };
        }
      }
    }
  }
  return { event, sides, skippedStale };
}

// Score a configured name against every spelling seen for a side. The event's own
// home_team/away_team can itself be the SHORT form (a live card listed the fixture as
// "Bulldogs v Souths" while four of its five books said "South Sydney Rabbitohs"), so
// the book spellings have to be candidates too.
function scoreSide(wanted, side) {
  let best = 0;
  for (const alias of side.aliases) best = Math.max(best, similarity(wanted, alias));
  return best;
}

// Take the best match across the whole card, so "Brisbane Broncos" cannot land on
// "London Broncos". The endpoint returns up to 50 upcoming events ordered by start
// time, which can span more than one round, so a team really can appear twice — equal
// matches are broken by the earliest kick-off, which is the game an alert is about.
function findTeam(resolved, wanted) {
  const hits = [];
  for (const r of resolved) {
    for (const key of ["home", "away"]) {
      const score = scoreSide(wanted, r.sides[key]);
      if (score >= MIN_TEAM_MATCH) {
        hits.push({ resolved: r, key, score, start: r.event.commence_time || "" });
      }
    }
  }
  if (!hits.length) return null;
  hits.sort((a, b) => b.score - a.score || a.start.localeCompare(b.start));
  // Only genuinely indistinguishable if the top two tie on both score and kick-off.
  if (hits.length > 1 && hits[0].score === hits[1].score && hits[0].start === hits[1].start) {
    return null;
  }
  return hits[0];
}

// --- API ---------------------------------------------------------------------

async function getNrlOdds() {
  // sport_key is a PATH parameter and the query parameter is `markets` (plural).
  // The response is a BARE JSON ARRAY of events — there is no envelope to unwrap.
  const url = new URL(`${BASE_URL}/sports/${SPORT_KEY}/odds`);
  url.searchParams.set("markets", "h2h");

  const res = await fetch(url, { headers: { "X-API-Key": API_KEY } });

  if (!res.ok) {
    // Errors are RFC 7807 problem+json: { type, title, status, detail }.
    const problem = await res.json().catch(() => ({}));
    const reason = problem.title || res.statusText;
    if (res.status === 401) throw new Error(`401 ${reason} — check API_KEY.`);
    if (res.status === 402) throw new Error(`402 ${reason} — monthly credits exhausted.`);
    if (res.status === 429) {
      throw new Error(`429 ${reason} — retry after ${res.headers.get("Retry-After") || "?"}s.`);
    }
    throw new Error(`${res.status} ${reason}`);
  }

  return res.json();
}

async function poll() {
  const now = new Date().toLocaleTimeString("en-AU");
  try {
    const events = await getNrlOdds();
    if (!events.length) {
      console.log(`[${now}] No upcoming NRL events with h2h prices right now.`);
      return;
    }

    const resolved = events.map(resolveEvent);

    for (const [team, target] of Object.entries(ALERTS)) {
      const found = findTeam(resolved, team);
      if (!found) {
        console.log(`[${now}]   watch ${team.padEnd(24)} no upcoming event matched`);
        continue;
      }

      const { best } = found.resolved.sides[found.key];
      if (!best) {
        console.log(`[${now}]   watch ${team.padEnd(24)} event listed but no usable h2h price`);
        continue;
      }

      const { event, skippedStale } = found.resolved;
      const hit = best.price >= target;
      const note = skippedStale.length ? `  [skipped stale: ${skippedStale.join(", ")}]` : "";
      console.log(
        `[${now}] ${hit ? "ALERT " : "  watch"} ${team.padEnd(24)} ` +
          `$${best.price.toFixed(2)} @ ${best.bookmaker.padEnd(12)} ` +
          `(target $${target.toFixed(2)}${hit ? " hit!" : ""})  ` +
          `${event.home_team} v ${event.away_team}${note}`
      );
    }
  } catch (e) {
    console.error(`[${now}] Error: ${e.message}`);
  }
}

console.log("NRL Price Alert — PuntersEdge API");
console.log(
  `   Watching ${Object.keys(ALERTS).length} teams. Polling every ${POLL_INTERVAL_MS / 1000}s ` +
    `(~${Math.round(86_400_000 / POLL_INTERVAL_MS)} credits/day if left running).\n`
);
poll();
setInterval(poll, POLL_INTERVAL_MS);
