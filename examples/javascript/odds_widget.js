/**
 * PuntersEdge API — Odds Comparison Widget (Vanilla JS)
 * Renders a simple odds comparison table in the browser.
 *
 * Usage: include this script, add <div id="pe-widget" data-sport="afl"></div>
 *
 * Get a free API key: https://puntersedge.online/developers/getting-started
 * API docs: https://puntersedge.online/odds-widget-api-australia
 */

(function () {
  const API_KEY = "your_api_key_here";
  const BASE_URL = "https://puntersedge.online/api";

  async function fetchOdds(sport) {
    const res = await fetch(
      `${BASE_URL}/odds?sport=${sport}&market=h2h`,
      { headers: { "X-API-Key": API_KEY } }
    );
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return (await res.json()).data || [];
  }

  function buildTable(events) {
    // Collect all bookmakers
    const bkSet = new Set();
    events.forEach(e =>
      (e.bookmakers || []).forEach(bk => bkSet.add(bk.key))
    );
    const bookmakers = [...bkSet];

    const table = document.createElement("table");
    table.style.cssText = "border-collapse:collapse;width:100%;font-family:sans-serif;font-size:14px";

    // Header
    const thead = table.createTHead();
    const hr = thead.insertRow();
    ["Match", "Kickoff", ...bookmakers].forEach(col => {
      const th = document.createElement("th");
      th.textContent = col;
      th.style.cssText = "padding:8px 12px;background:#1e293b;color:#fff;text-align:left;white-space:nowrap";
      hr.appendChild(th);
    });

    // Rows
    const tbody = table.createTBody();
    for (const event of events) {
      // Index prices: bk.key → {team: price}
      const prices = {};
      for (const bk of event.bookmakers || []) {
        prices[bk.key] = {};
        for (const market of bk.markets || []) {
          if (market.key !== "h2h") continue;
          for (const outcome of market.outcomes || []) {
            prices[bk.key][outcome.name] = outcome.price;
          }
        }
      }

      const teams = [event.home_team, event.away_team];
      for (const team of teams) {
        const tr = tbody.insertRow();
        tr.style.borderBottom = "1px solid #e2e8f0";

        // Match cell (first row of pair only)
        const matchTd = tr.insertCell();
        if (team === event.home_team) {
          matchTd.rowSpan = 2;
          matchTd.textContent = `${event.home_team} vs ${event.away_team}`;
          matchTd.style.cssText = "padding:8px 12px;font-weight:600;vertical-align:middle";
        }

        // Kickoff cell
        if (team === event.home_team) {
          const kickTd = tr.insertCell();
          kickTd.rowSpan = 2;
          kickTd.textContent = new Date(event.commence_time).toLocaleString("en-AU", {
            month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"
          });
          kickTd.style.cssText = "padding:8px 12px;color:#64748b;vertical-align:middle;white-space:nowrap";
        }

        // Price cells
        let bestPrice = 0;
        bookmakers.forEach(bk => {
          const p = prices[bk]?.[team];
          if (p && p > bestPrice) bestPrice = p;
        });

        bookmakers.forEach(bk => {
          const td = tr.insertCell();
          const p = prices[bk]?.[team];
          td.textContent = p ? `$${p.toFixed(2)}` : "—";
          td.style.cssText = `padding:8px 12px;text-align:center;${p === bestPrice ? "background:#dcfce7;font-weight:700;color:#15803d" : ""}`;
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
