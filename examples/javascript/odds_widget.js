/**
 * PuntersEdge API — Odds Comparison Widget (Vanilla JS)
 * Renders a simple odds comparison table in the browser.
 *
 * Usage: include this script, then add a container carrying the `data-pe-widget`
 * attribute (that attribute is the selector — an id alone will not be picked up):
 *
 *   <div data-pe-widget data-sport="afl"></div>
 *
 * Heads up: this puts your API key in page source, where anyone can read it. That
 * is fine for a local demo. In production, proxy the call through your own backend
 * and keep the key server-side.
 *
 * Get a free API key (1,500 credits/month, no credit card):
 *   https://puntersedge.online/developers/getting-started
 * Widget/API docs: https://puntersedge.online/odds-widget-api-australia
 * Interactive reference: https://api.puntersedge.online/docs
 */

(function () {
  const API_KEY = "your_api_key_here";
  const BASE_URL = "https://api.puntersedge.online/v1";

  // Real sport keys accepted by /v1/sports/{sport_key}/odds — fetch the live list
  // from GET /v1/sports:
  //   afl, nrl, nba, wnba, aflw, nrlw, nfl, nhl, mlb, ncaaf, mma,
  //   tennis_atp, tennis_wta, cricket_test, cricket_other, cricket_bb,
  //   rugby_union, soccer_other, basketball_other
  //
  // There is NO racing sport key. Horse, harness and greyhound racing live in a
  // separate endpoint family (GET /v1/racing/next-to-go, GET /v1/racing/best-odds);
  // passing something like "horse_racing" here returns 404.
  //
  // Coverage is genuinely uneven, so expect a sparse grid: AFL and NRL carry at most
  // 5 bookmakers, NBA and ATP at most 3, and several sports only 1. Blank cells mean
  // that book has no price for that selection, not that the widget failed.

  async function fetchOdds(sportKey) {
    // sport_key is a PATH parameter. The query parameter is `markets` (plural) and
    // takes a comma-separated list: h2h, spreads, totals. Costs 1 credit per market
    // requested, so this call is 1 credit.
    const url = `${BASE_URL}/sports/${encodeURIComponent(sportKey)}/odds?markets=h2h`;
    const res = await fetch(url, { headers: { "X-API-Key": API_KEY } });

    if (!res.ok) {
      throw new Error(await describeError(res));
    }

    // This endpoint returns a BARE JSON ARRAY of events — there is no envelope and
    // no "data" key to unwrap.
    const events = await res.json();
    return Array.isArray(events) ? events : [];
  }

  // Errors come back as RFC 7807 problem+json: {type, title, status, detail}.
  // `detail` is a string for most errors, an array of field errors for 422.
  async function describeError(res) {
    let message = `HTTP ${res.status}`;
    try {
      const problem = await res.json();
      const detail = Array.isArray(problem.detail)
        ? problem.detail.map(d => d.msg || JSON.stringify(d)).join("; ")
        : (typeof problem.detail === "string" ? problem.detail : "");
      const parts = [problem.title, detail].filter(Boolean);
      message = [...new Set(parts)].join(" — ") || message;
    } catch (_) {
      // Non-JSON body (e.g. a gateway error page) — fall back to the status code.
    }
    if (res.status === 429) {
      // NOTE: a 429 does carry Retry-After, but the API's CORS config sets no
      // expose_headers, so in a BROWSER this reads null — only server-side callers
      // can see it. Left in because this file is also useful as a fetch reference.
      const retry = res.headers.get("Retry-After");
      if (retry) message += ` (retry in ${retry}s)`;
    }
    return message;
  }

  function buildTable(events) {
    // Collect every bookmaker present, keeping the display title the API supplies.
    const bookTitles = new Map();
    events.forEach(e =>
      (e.bookmakers || []).forEach(bk => {
        if (!bookTitles.has(bk.key)) bookTitles.set(bk.key, bk.title || bk.key);
      })
    );
    const bookmakers = [...bookTitles.keys()];

    const table = document.createElement("table");
    table.style.cssText = "border-collapse:collapse;width:100%;font-family:sans-serif;font-size:14px";

    // Header
    const thead = table.createTHead();
    const hr = thead.insertRow();
    ["Match", "Start", ...bookmakers.map(k => bookTitles.get(k))].forEach(col => {
      const th = document.createElement("th");
      th.textContent = col;
      th.style.cssText = "padding:8px 12px;background:#1e293b;color:#fff;text-align:left;white-space:nowrap";
      hr.appendChild(th);
    });

    // Rows
    const tbody = table.createTBody();
    for (const event of events) {
      // Index prices: bk.key → {selection name: price}
      const prices = {};
      for (const bk of event.bookmakers || []) {
        prices[bk.key] = [];
        for (const market of bk.markets || []) {
          if (market.key !== "h2h") continue;
          for (const outcome of market.outcomes || []) {
            // Prices are decimal by default (oddsFormat=decimal). Pass
            // oddsFormat=american and these become American integers instead,
            // which the "$x.xx" formatting below would misrepresent.
            prices[bk.key].push({ name: outcome.name, price: outcome.price });
          }
        }
      }

      // `stale_bookmakers` names books whose price has not moved in over 30 minutes
      // (2x the 15-minute sports poll). They are still served — just flagged.
      const staleBooks = new Set(event.stale_bookmakers || []);

      // home_team/away_team are nullable on some feeds (individual-sport events in
      // particular), so fall back rather than printing "null".
      const home = event.home_team || "Home";
      const away = event.away_team || "Away";

      // Bookmakers do NOT agree on team names. The same NRL event carries "Melbourne
      // Storm" from one book and "Melbourne" from another, so looking a price up by
      // event.home_team against the exact outcome.name misses silently — the cell renders
      // "—" as though that book had no price at all. Match on a normalised form, allowing
      // one label to contain the other.
      const norm = (s) => String(s || "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
      const priceFor = (bk, team) => {
        const t = norm(team);
        if (!t) return undefined;
        let partial;
        for (const o of prices[bk] || []) {
          const n = norm(o.name);
          if (n === t) return o.price;
          if (partial === undefined && (n.includes(t) || t.includes(n))) partial = o.price;
        }
        return partial;
      };

      // Two rows per event: home and away. Sports whose h2h carries a draw
      // (soccer_other, soccer_epl, rugby_union, cricket_test) also return an outcome named
      // "Draw" or "The Draw", which this widget does not render — point data-sport at one
      // of those and the draw price is simply absent.
      const teams = [home, away];
      for (const team of teams) {
        const tr = tbody.insertRow();
        tr.style.borderBottom = "1px solid #e2e8f0";

        // Match + start cells (first row of the pair only)
        if (team === home) {
          const matchTd = tr.insertCell();
          matchTd.rowSpan = 2;
          matchTd.textContent = `${home} vs ${away}`;
          matchTd.style.cssText = "padding:8px 12px;font-weight:600;vertical-align:middle";

          const kickTd = tr.insertCell();
          kickTd.rowSpan = 2;
          kickTd.textContent = new Date(event.commence_time).toLocaleString("en-AU", {
            month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"
          });
          kickTd.style.cssText = "padding:8px 12px;color:#64748b;vertical-align:middle;white-space:nowrap";
        }

        // Best available price across the books that quoted this selection
        let bestPrice = 0;
        bookmakers.forEach(bk => {
          const p = priceFor(bk, team);
          if (typeof p === "number" && p > bestPrice) bestPrice = p;
        });

        bookmakers.forEach(bk => {
          const td = tr.insertCell();
          const p = priceFor(bk, team);
          const isBest = typeof p === "number" && bestPrice > 0 && p === bestPrice;
          td.textContent = typeof p === "number" ? `$${p.toFixed(2)}` : "—";
          if (staleBooks.has(bk)) td.title = `${bookTitles.get(bk)} price is over 30 minutes old`;
          td.style.cssText =
            "padding:8px 12px;text-align:center;" +
            (isBest ? "background:#dcfce7;font-weight:700;color:#15803d;" : "") +
            (staleBooks.has(bk) ? "opacity:0.55;" : "");
        });
      }
    }

    return table;
  }

  function init() {
    const containers = document.querySelectorAll("[data-pe-widget]");
    containers.forEach(async container => {
      const sport = container.dataset.sport || "afl";
      container.innerHTML = "<p style='color:#64748b;font-size:13px'>Loading odds...</p>";
      try {
        const events = await fetchOdds(sport);
        container.innerHTML = "";
        if (!events.length) {
          container.innerHTML =
            `<p style='color:#64748b;font-size:13px'>No upcoming ${sport} events with prices right now.</p>`;
          return;
        }
        container.appendChild(buildTable(events));
      } catch (e) {
        container.innerHTML = `<p style='color:red'>Error loading odds: ${e.message}</p>`;
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
