/* =============================================
   Thursday Numbers — Vanilla JS App
   ============================================= */

"use strict";

// ─── Data paths (relative to web/ folder) ───────────────────────────────────
const DATA_URL    = "data/powerball_draws.json";
const PICKS_URL   = "picks/picks_history.json";
const VERSION_URL = "VERSION";

// ─── State ──────────────────────────────────────────────────────────────────
let draws = [];         // ALL draws (1996–present, all formats)
let currentDraws = [];  // Current-format only: 7 main from 1–35, PB from 1–20 (Apr 2018+)
let mainFreq = {};   // { ball: count }
let pbFreq   = {};
let hotMain  = [];   // sorted list of top-10 most frequent
let coldMain = [];   // sorted list of bottom-10 least frequent
let hotPb    = [];   // top-5

let recencyWeightsArr   = []; // [{ball, w}] — recency-weighted main ball probabilities
let pbRecencyWeightsArr = []; // [{ball, w}] — recency-weighted PB probabilities
let coldPb = [];              // bottom-5 least-frequent powerballs

let charts = {};     // cache Chart.js instances so we can destroy/rebuild
let histPage = 1;
let histPerPage = 20;
let histFiltered = [];

// ─── Bootstrap ──────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  setupTabs();
  loadVersion();
  loadData();
});

// ─── Version ────────────────────────────────────────────────────────────────
async function loadVersion() {
  try {
    const resp = await fetch(VERSION_URL);
    if (!resp.ok) return;
    const ver = (await resp.text()).trim();
    const el = document.getElementById("footer-version");
    if (el) el.textContent = `v${ver}`;
  } catch (_) { /* version display is non-critical */ }
}

// ─── Tab navigation ─────────────────────────────────────────────────────────
function setupTabs() {
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach(s => s.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
    });
  });
}

// ─── Data loading ────────────────────────────────────────────────────────────
async function loadData() {
  try {
    const resp = await fetch(DATA_URL);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    draws = await resp.json();
  } catch (e) {
    showError(`Could not load draw data: ${e.message}. Are you running this from GitHub Pages or a local server?`);
    return;
  }

  // Filter to draws using the current game format (7 main balls 1–35, PB 1–20)
  // Pre-2018 used different formats (5 or 6 balls from wider pools) and must not
  // be mixed into frequency analysis for the current game.
  currentDraws = draws.filter(d => d.main.length === 7);

  computeFrequencies();
  renderDashboard();
  renderFrequency();
  renderTrends();
  setupPicker();
  setupHistory();
}

// ─── Frequency analysis ──────────────────────────────────────────────────────
function computeFrequencies() {
  mainFreq = {};
  pbFreq   = {};

  for (let n = 1; n <= 35; n++) mainFreq[n] = 0;
  for (let n = 1; n <= 20; n++) pbFreq[n]   = 0;

  // Use currentDraws only — pre-2018 formats used different ball pools
  for (const d of currentDraws) {
    for (const b of d.main) mainFreq[b]++;
    pbFreq[d.powerball]++;
  }

  const mainSorted = Object.entries(mainFreq)
    .map(([k, v]) => ({ ball: +k, count: v }))
    .sort((a, b) => b.count - a.count);

  hotMain  = mainSorted.slice(0, 10).map(x => x.ball).sort((a, b) => a - b);
  coldMain = mainSorted.slice(-10).map(x => x.ball).sort((a, b) => a - b);

  hotPb = Object.entries(pbFreq)
    .map(([k, v]) => ({ ball: +k, count: v }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 5)
    .map(x => x.ball)
    .sort((a, b) => a - b);

  coldPb = Object.entries(pbFreq)
    .map(([k, v]) => ({ ball: +k, count: v }))
    .sort((a, b) => a.count - b.count)
    .slice(0, 5)
    .map(x => x.ball)
    .sort((a, b) => a - b);

  computeRecencyWeights();
}

// ─── Recency-weighted frequency ──────────────────────────────────────────────
// Each draw is assigned a linear weight: oldest draw = 1.0, newest = 2.0.
// This gives recent draws twice the influence of draws at the start of the
// dataset — a defensible middle-ground between flat frequency (equal weight)
// and a pure recency window (hard cutoff).  All 35 main balls and 20 PBs are
// included, so sampling is from the full pool with probability proportional
// to recency-adjusted appearance counts.
function computeRecencyWeights() {
  const n = currentDraws.length;
  if (n === 0) return;

  const rawMain = {}, rawPb = {};
  for (let b = 1; b <= 35; b++) rawMain[b] = 0;
  for (let b = 1; b <= 20; b++) rawPb[b]   = 0;

  currentDraws.forEach((draw, idx) => {
    const w = 1 + idx / (n - 1); // 1.0 (oldest draw) → 2.0 (newest draw)
    draw.main.forEach(b => { rawMain[b] += w; });
    rawPb[draw.powerball] += w;
  });

  const mainTotal = Object.values(rawMain).reduce((s, v) => s + v, 0);
  recencyWeightsArr = [];
  for (let b = 1; b <= 35; b++) recencyWeightsArr.push({ ball: b, w: rawMain[b] / mainTotal });

  const pbTotal = Object.values(rawPb).reduce((s, v) => s + v, 0);
  pbRecencyWeightsArr = [];
  for (let b = 1; b <= 20; b++) pbRecencyWeightsArr.push({ ball: b, w: rawPb[b] / pbTotal });
}

// ─── Dashboard ───────────────────────────────────────────────────────────────
function renderDashboard() {
  const latest      = draws[draws.length - 1];
  const first       = draws[0];
  const firstCurrent = currentDraws[0];

  // Stats — total historical draws and date range of full archive
  document.getElementById("stat-draws").textContent = draws.length;
  document.getElementById("stat-range").textContent =
    first.date.slice(0, 4) + "–" + latest.date.slice(0, 4);

  // Hottest ball stats are based on current-format draws only
  const hottestBall = hotMain[0];
  document.getElementById("stat-hottest").textContent =
    `${hottestBall} (${mainFreq[hottestBall]}x)`;
  document.getElementById("stat-hot-pb").textContent =
    `${hotPb[0]} (${pbFreq[hotPb[0]]}x)`;

  // Panel sub-heading: clarify that frequency counts use current-format draws only
  document.getElementById("dash-draws").textContent = currentDraws.length;

  // Hot main
  const hotEl = document.getElementById("hot-main-balls");
  hotEl.innerHTML = hotMain.map(b =>
    `<span class="ball ball-main">${b}</span>
     <span class="ball ball-freq">${mainFreq[b]}x</span>`
  ).join("");

  // Cold main
  const coldEl = document.getElementById("cold-main-balls");
  coldEl.innerHTML = coldMain.map(b =>
    `<span class="ball ball-cold">${b}</span>
     <span class="ball ball-freq">${mainFreq[b]}x</span>`
  ).join("");

  // Hot PBs
  const pbEl = document.getElementById("hot-pb-balls");
  pbEl.innerHTML = hotPb.map(b =>
    `<span class="ball ball-pb">${b}</span>
     <span class="ball ball-freq">${pbFreq[b]}x</span>`
  ).join("");

  // Latest draw
  const hotSet = new Set(hotMain);
  document.getElementById("latest-draw-info").innerHTML = `
    <div class="latest-draw">
      <div class="latest-draw-num">Draw #${latest.draw}</div>
      <div class="latest-draw-date">${formatDate(latest.date)}</div>
      <div class="draw-balls">
        ${latest.main.map(b =>
          `<span class="draw-ball ${hotSet.has(b) ? "hot" : ""}">${b}</span>`
        ).join("")}
        <span class="draw-separator">│</span>
        <span class="draw-ball pb-ball">${latest.powerball}</span>
      </div>
      <div class="draw-hot-note">
        🔥 Highlighted = hot numbers
      </div>
    </div>
  `;
}

// ─── Frequency tab ───────────────────────────────────────────────────────────
function renderFrequency() {
  // Main ball frequency bar chart
  const mainLabels = Array.from({ length: 35 }, (_, i) => i + 1);
  const mainData   = mainLabels.map(n => mainFreq[n]);
  const hotSet     = new Set(hotMain);

  destroyChart("main-freq");
  const ctx1 = document.getElementById("chart-main-freq").getContext("2d");
  charts["main-freq"] = new Chart(ctx1, {
    type: "bar",
    data: {
      labels: mainLabels,
      datasets: [{
        label: "Times drawn",
        data: mainData,
        backgroundColor: mainLabels.map(n => hotSet.has(n) ? "#f97316cc" : "#6366f166"),
        borderColor:     mainLabels.map(n => hotSet.has(n) ? "#f97316" : "#6366f1"),
        borderWidth: 1,
      }]
    },
    options: chartOptions("Main ball frequency (1–35)", "Ball number", "Times drawn"),
  });

  // Powerball frequency
  const pbLabels = Array.from({ length: 20 }, (_, i) => i + 1);
  const pbData   = pbLabels.map(n => pbFreq[n]);
  const hotPbSet = new Set(hotPb);

  destroyChart("pb-freq");
  const ctx2 = document.getElementById("chart-pb-freq").getContext("2d");
  charts["pb-freq"] = new Chart(ctx2, {
    type: "bar",
    data: {
      labels: pbLabels,
      datasets: [{
        label: "Times drawn",
        data: pbData,
        backgroundColor: pbLabels.map(n => hotPbSet.has(n) ? "#a855f7cc" : "#6366f166"),
        borderColor:     pbLabels.map(n => hotPbSet.has(n) ? "#a855f7" : "#6366f1"),
        borderWidth: 1,
      }]
    },
    options: chartOptions("Powerball frequency (1–20)", "Powerball number", "Times drawn"),
  });
}

// ─── Trends tab ──────────────────────────────────────────────────────────────
function renderTrends() {
  // Use currentDraws so we're always looking at current-format draws (7/35)
  const recent = currentDraws.slice(-20);

  // Count appearances in last 20 current-format draws
  const recentCount = {};
  for (let n = 1; n <= 35; n++) recentCount[n] = 0;
  for (const d of recent) for (const b of d.main) recentCount[b]++;

  const rc = Object.entries(recentCount)
    .filter(([, v]) => v > 0)
    .sort(([, a], [, b]) => b - a);

  destroyChart("recent-main");
  const ctx3 = document.getElementById("chart-recent-main").getContext("2d");
  charts["recent-main"] = new Chart(ctx3, {
    type: "bar",
    data: {
      labels: rc.map(([k]) => k),
      datasets: [{
        label: "Appearances in last 20 draws",
        data: rc.map(([, v]) => v),
        backgroundColor: "#38bdf866",
        borderColor: "#38bdf8",
        borderWidth: 1,
      }]
    },
    options: chartOptions("Appearances in last 20 draws", "Ball", "Count"),
  });

  // Draws since last appearance (within current-format draws only)
  const sinceMap = {};
  for (let n = 1; n <= 35; n++) sinceMap[n] = currentDraws.length; // default: never seen

  for (let n = 1; n <= 35; n++) {
    let found = false;
    for (let i = currentDraws.length - 1; i >= 0; i--) {
      if (currentDraws[i].main.includes(n)) { sinceMap[n] = currentDraws.length - 1 - i; found = true; break; }
    }
    if (!found) sinceMap[n] = currentDraws.length;
  }

  const sl = Object.entries(sinceMap).sort(([, a], [, b]) => a - b);

  destroyChart("since-last");
  const ctx4 = document.getElementById("chart-since-last").getContext("2d");
  charts["since-last"] = new Chart(ctx4, {
    type: "bar",
    data: {
      labels: sl.map(([k]) => k),
      datasets: [{
        label: "Draws since last appearance",
        data: sl.map(([, v]) => v),
        backgroundColor: sl.map(([, v]) => v <= 4 ? "#22c55e88" : v <= 10 ? "#f9731688" : "#6366f166"),
        borderColor:     sl.map(([, v]) => v <= 4 ? "#22c55e" : v <= 10 ? "#f97316" : "#6366f1"),
        borderWidth: 1,
      }]
    },
    options: chartOptions("Draws since last appearance", "Ball", "Draws"),
  });
}

// ─── Picker tab ──────────────────────────────────────────────────────────────
let pickerMode      = "hot";  // hot | cold | mixed | random
let pickerGameCount = 18;     // 1 | 18

function setupPicker() {
  // Strategy card selection
  document.querySelectorAll(".strategy-card").forEach(card => {
    card.addEventListener("click", () => {
      document.querySelectorAll(".strategy-card").forEach(c => c.classList.remove("active"));
      card.classList.add("active");
      pickerMode = card.dataset.mode;
    });
  });

  // Game count toggle
  document.querySelectorAll(".count-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".count-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      pickerGameCount = parseInt(btn.dataset.count, 10);
    });
  });

  // Generate button
  document.getElementById("btn-generate").addEventListener("click", () => {
    renderPickerResult(generateGamesLocal(pickerMode, pickerGameCount));
  });
}

function generateGameWithStrategy(mode) {
  let main, pb;

  if (mode === "hot") {
    // Recency-weighted sampling from all 35 balls — balls that appeared more
    // frequently in recent draws get proportionally higher selection probability.
    main = weightedSample(recencyWeightsArr, 7).sort((a, b) => a - b);
    pb   = weightedSample(pbRecencyWeightsArr, 1)[0];

  } else if (mode === "cold") {
    // Flat frequency cold pool for main; cold Powerballs for PB.
    main = sample([...coldMain], 7).sort((a, b) => a - b);
    pb   = coldPb[Math.floor(Math.random() * coldPb.length)];

  } else if (mode === "mixed") {
    // Balanced Draw: rejection sampling against the hypergeometric distribution.
    // Constraints derived from 7-choose-35 theoretical distribution:
    //   Sum  in [87, 165]  — central ~90th percentile  (E=126, SD≈24.3)
    //   Odds in [2, 5]     — covers 91.2% of probability (17 odd in 1–35)
    //   Lows in [2, 5]     — covers 91.2% (17 "low" = 1–17, 18 "high" = 18–35)
    // ~85% of uniform random draws satisfy all three, so average ~1.2 iterations.
    main = generateBalancedMain();
    pb   = weightedSample(pbRecencyWeightsArr, 1)[0];

  } else {
    // True Random: cryptographically-uniform over all valid combinations.
    main = sample(Array.from({ length: 35 }, (_, i) => i + 1), 7).sort((a, b) => a - b);
    pb   = Math.floor(Math.random() * 20) + 1;
  }

  return { main, powerball: pb };
}

// Rejection sampling for a statistically balanced main-ball pick.
// All three constraints come from the hypergeometric distribution of
// drawing 7 balls without replacement from pools of size 35.
function generateBalancedMain() {
  const allMain = Array.from({ length: 35 }, (_, i) => i + 1);
  for (let attempt = 0; attempt < 5000; attempt++) {
    const pick = sample(allMain, 7);
    const sum  = pick.reduce((a, b) => a + b, 0);
    const odds = pick.filter(n => n % 2 !== 0).length;
    const lows = pick.filter(n => n <= 17).length;
    if (sum >= 87 && sum <= 165 && odds >= 2 && odds <= 5 && lows >= 2 && lows <= 5) {
      return pick.sort((a, b) => a - b);
    }
  }
  return sample(allMain, 7).sort((a, b) => a - b); // fallback (essentially impossible)
}

function generateGamesLocal(mode = "hot", count = 1) {
  const games = [];
  const seen  = new Set();

  for (let i = 0; i < count * 1000 && games.length < count; i++) {
    const g   = generateGameWithStrategy(mode);
    const key = g.main.join(",") + "|" + g.powerball;
    if (!seen.has(key)) {
      seen.add(key);
      games.push({ game: games.length + 1, ...g });
    }
  }

  return {
    generated_at:   new Date().toISOString().slice(0, 19),
    draws_analysed: currentDraws.length,
    data_range:     `${currentDraws[0].date} to ${currentDraws[currentDraws.length - 1].date}`,
    strategy:       mode,
    hot_main_balls: hotMain,
    hot_powerballs: hotPb,
    games,
  };
}

function renderPickerResult(result) {
  const container = document.getElementById("picker-result");
  container.innerHTML = "";
  renderGamesGrid(container, result);
}

const STRATEGY_LABELS = {
  hot:    "🔥 Hot Numbers",
  cold:   "❄️ Cold Numbers",
  mixed:  "⚖️ Balanced Draw",
  random: "🎲 True Random",
};

function renderSingleGame(container, result) {
  const g     = result.games[0];
  const label = STRATEGY_LABELS[result.strategy] || "Generated";
  const panel = document.createElement("div");
  panel.className = "panel single-result";
  panel.innerHTML = `
    <div class="single-result-header">
      <span class="single-strategy-badge">${label}</span>
      <span class="single-meta">${result.draws_analysed} draws analysed · ${result.generated_at.slice(0, 10)}</span>
    </div>
    <div class="single-balls">
      ${g.main.map(b => `<span class="ball-lg ball-lg-main">${b}</span>`).join("")}
      <span class="ball-lg-divider">+</span>
      <span class="ball-lg ball-lg-pb">${g.powerball}</span>
    </div>
    <div class="single-labels">
      <span>Main Balls (7)</span>
      <span>Powerball</span>
    </div>
    <div class="single-odds">Jackpot odds: 1 in 134,490,400 · For entertainment only</div>
  `;
  container.appendChild(panel);
}

function renderGamesGrid(container, result) {
  const label = STRATEGY_LABELS[result.strategy] || "";
  const panel = document.createElement("div");
  panel.className = "panel";
  panel.innerHTML = `<p class="panel-sub">${label} · ${result.draws_analysed} draws analysed · ${result.generated_at.slice(0, 10)}</p>`;

  const grid = document.createElement("div");
  grid.className = "games-grid";
  for (const g of result.games) {
    const card = document.createElement("div");
    card.className = "game-card";
    const balls = g.main.map(b => `<span class="ball-sm main">${b}</span>`).join("");
    card.innerHTML = `
      <div class="gc-header">Game ${g.game}</div>
      <div class="gc-main">${balls}</div>
      <div class="gc-pb">
        <span class="gc-pb-label">Powerball</span>
        <span class="ball-sm pb">${g.powerball}</span>
      </div>`;
    grid.appendChild(card);
  }

  panel.appendChild(grid);
  container.appendChild(panel);
}

// ─── History tab ─────────────────────────────────────────────────────────────
function setupHistory() {
  histFiltered = [...draws].reverse(); // newest first
  document.getElementById("hist-total").textContent = draws.length;

  document.getElementById("hist-search").addEventListener("input", e => {
    const q = e.target.value.toLowerCase();
    histFiltered = draws.filter(d =>
      String(d.draw).includes(q) ||
      d.date.includes(q) ||
      d.main.some(b => String(b) === q.trim())
    ).reverse();
    histPage = 1;
    renderHistoryTable();
  });

  document.getElementById("hist-per-page").addEventListener("change", e => {
    histPerPage = +e.target.value;
    histPage = 1;
    renderHistoryTable();
  });

  renderHistoryTable();
}

function renderHistoryTable() {
  const hotSet = new Set(hotMain);
  const start  = (histPage - 1) * histPerPage;
  const page   = histFiltered.slice(start, start + histPerPage);
  const tbody  = document.getElementById("history-tbody");

  tbody.innerHTML = page.map(d => `
    <tr>
      <td><strong>#${d.draw}</strong></td>
      <td>${formatDate(d.date)}</td>
      <td>
        <div class="draw-balls">
          ${d.main.map(b =>
            `<span class="draw-ball ${hotSet.has(b) ? "hot" : ""}">${b}</span>`
          ).join("")}
        </div>
      </td>
      <td><span class="draw-ball pb-ball">${d.powerball}</span></td>
    </tr>
  `).join("");

  renderPagination();
}

function renderPagination() {
  const total = Math.ceil(histFiltered.length / histPerPage);
  const pag   = document.getElementById("hist-pagination");

  if (total <= 1) { pag.innerHTML = ""; return; }

  const pages = [];
  if (histPage > 1) pages.push({ label: "←", p: histPage - 1 });
  for (let p = Math.max(1, histPage - 2); p <= Math.min(total, histPage + 2); p++) {
    pages.push({ label: String(p), p, active: p === histPage });
  }
  if (histPage < total) pages.push({ label: "→", p: histPage + 1 });

  pag.innerHTML = pages.map(({ label, p, active }) =>
    `<button class="page-btn ${active ? "active" : ""}" data-p="${p}">${label}</button>`
  ).join("");

  pag.querySelectorAll(".page-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      histPage = +btn.dataset.p;
      renderHistoryTable();
      document.getElementById("tab-history").scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
}

// ─── Helpers ─────────────────────────────────────────────────────────────────
// Weighted sampling without replacement (probability proportional to .w field).
// pool: [{ball, w}, ...]; returns array of n ball numbers.
function weightedSample(pool, n) {
  const p = pool.map(x => ({ ball: x.ball, w: x.w }));
  const result = [];
  while (result.length < n && p.length > 0) {
    const total = p.reduce((s, x) => s + x.w, 0);
    let r = Math.random() * total;
    for (let i = 0; i < p.length; i++) {
      r -= p[i].w;
      if (r <= 0 || i === p.length - 1) {
        result.push(p[i].ball);
        p.splice(i, 1);
        break;
      }
    }
  }
  return result;
}

function sample(arr, n) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a.slice(0, n);
}

function formatDate(iso) {
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}

function chartOptions(title, xLabel, yLabel) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      title: { display: false },
      tooltip: {
        backgroundColor: "#22263a",
        borderColor: "#2d3148",
        borderWidth: 1,
        titleColor: "#e2e8f0",
        bodyColor: "#8892a4",
      }
    },
    scales: {
      x: {
        ticks: { color: "#8892a4", font: { size: 11 } },
        grid:  { color: "#1e2235" },
        title: { display: true, text: xLabel, color: "#8892a4", font: { size: 12 } },
      },
      y: {
        ticks: { color: "#8892a4", font: { size: 11 } },
        grid:  { color: "#1e2235" },
        title: { display: true, text: yLabel, color: "#8892a4", font: { size: 12 } },
        beginAtZero: true,
      },
    },
  };
}

function destroyChart(key) {
  if (charts[key]) { charts[key].destroy(); delete charts[key]; }
}

function showError(msg) {
  document.querySelector("main").innerHTML =
    `<div class="error-msg">⚠️ ${msg}</div>`;
}
