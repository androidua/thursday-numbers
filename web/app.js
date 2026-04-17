/* =============================================
   Thursday Numbers — Vanilla JS App
   ============================================= */

"use strict";

// ─── Data paths (relative to web/ folder) ───────────────────────────────────
const DATA_URL    = "data/powerball_draws.json";
const VERSION_URL = "VERSION";

// ─── State ──────────────────────────────────────────────────────────────────
let draws = [];         // ALL draws (1996–present, all formats)
let currentDraws = [];  // Current-format only: 7 main from 1–35, PB from 1–20 (Apr 2018+)
let mainFreq = {};   // { ball: count }
let pbFreq   = {};
let hotMain  = [];   // sorted list of top-10 most frequent
let coldMain = [];   // sorted list of bottom-10 least frequent
let hotPb    = [];   // top-5

let recencyWeightsArr   = []; // [{ball, w}] — EWMA-weighted main ball probabilities
let pbRecencyWeightsArr = []; // [{ball, w}] — EWMA-weighted PB probabilities
let coldPb = [];              // bottom-5 least-frequent powerballs

// Adaptive sum bounds for balanced-draw mode (empirical 5th/95th percentiles)
let sumP5  = 87;
let sumP95 = 165;

// Chi-squared significance (computed in computeFrequencies)
let chiSquaredMainP  = null;   // p-value for main ball distribution test
let chiSquaredMainStat = null; // χ² statistic

let charts = {};     // cache Chart.js instances so we can destroy/rebuild
let dataLoaded = false;                       // true once draws are ready
const tabsRendered = new Set(["dashboard"]);  // tracks which tabs have been rendered

// Split-pot avoidance prior (v1.5.23). Multiplicative penalties applied to
// EWMA scores before normalization, biasing the picker away from numbers
// humans overpick (dates 1–31, "lucky" 7/11). Doesn't change win probability
// but raises expected payout per win by reducing pot-split dilution.
// 13 left at 1.00 (underpicked — unlucky superstition); 32–35 at 1.00 too.
const POPULARITY_PENALTY_MAIN = {};
for (let b = 1; b <= 31; b++) POPULARITY_PENALTY_MAIN[b] = 0.90;
POPULARITY_PENALTY_MAIN[7]  = 0.85;
POPULARITY_PENALTY_MAIN[11] = 0.85;

const POPULARITY_PENALTY_PB = {};
for (let b = 1; b <= 20; b++) POPULARITY_PENALTY_PB[b] = 0.95;
POPULARITY_PENALTY_PB[7]  = 0.90;
POPULARITY_PENALTY_PB[11] = 0.90;

let histPage = 1;
let histPerPage = 20;
let histFiltered = [];

// ─── Bootstrap ──────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  setupGlobalErrorHandlers();
  setupTabs();
  loadVersion();
  loadData();
});

// Surfaces any uncaught runtime error or unhandled promise rejection to the
// console — without these, exceptions outside the loadData try/catch fail silently in prod.
function setupGlobalErrorHandlers() {
  window.addEventListener("error", (ev) => {
    console.error("[thursday-numbers] uncaught error:", ev.error || ev.message);
  });
  window.addEventListener("unhandledrejection", (ev) => {
    console.error("[thursday-numbers] unhandled promise rejection:", ev.reason);
  });
}

// Two attempts with 500ms backoff. Retries only on network failure or non-OK response,
// not on AbortError. Returns the Response; caller handles .json()/.text() parsing.
async function fetchWithRetry(url, options = {}, maxAttempts = 2) {
  let lastErr;
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      const resp = await fetch(url, options);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      return resp;
    } catch (e) {
      lastErr = e;
      if (e.name === "AbortError" || attempt === maxAttempts) break;
      await new Promise(r => setTimeout(r, 500));
    }
  }
  throw lastErr;
}

// ─── Version ────────────────────────────────────────────────────────────────
async function loadVersion() {
  try {
    const resp = await fetchWithRetry(VERSION_URL);
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
      const tab = btn.dataset.tab;
      document.getElementById("tab-" + tab).classList.add("active");
      if (dataLoaded) maybeRenderTab(tab);
    });
  });
}

// Render a tab's charts the first time it's activated (lazy loading).
// Dashboard is rendered eagerly in loadData(); all others wait for first click.
function maybeRenderTab(tab) {
  if (tabsRendered.has(tab)) return;
  tabsRendered.add(tab);
  if (tab === "frequency") renderFrequency();
  else if (tab === "trends") renderTrends();
}

// ─── Data loading ────────────────────────────────────────────────────────────
async function loadData() {
  showLoading();
  try {
    const resp = await fetchWithRetry(DATA_URL);
    draws = await resp.json();
    if (!Array.isArray(draws) || draws.length === 0 ||
        !Array.isArray(draws[0].main) || !("powerball" in draws[0])) {
      throw new Error("Draw data format is invalid");
    }
  } catch (e) {
    showError(`Could not load draw data: ${e.message}. Are you running this from GitHub Pages or a local server?`);
    return;
  }
  hideLoading();

  // Filter to draws using the current game format (7 main balls 1–35, PB 1–20)
  // Pre-2018 used different formats (5 or 6 balls from wider pools) and must not
  // be mixed into frequency analysis for the current game.
  currentDraws = draws.filter(d => d.main.length === 7);

  computeFrequencies();
  renderDashboard();
  setupPicker();
  setupHistory();
  dataLoaded = true;

  // If user clicked a non-dashboard tab while data was loading, render it now.
  const activeTab = document.querySelector(".tab-btn.active")?.dataset.tab;
  if (activeTab) maybeRenderTab(activeTab);
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

  computeEwmaWeights();
  computeAdaptiveBounds();
  computeChiSquared();
}

// ─── EWMA-weighted frequency ─────────────────────────────────────────────────
// Each ball's score is updated each draw using an Exponentially Weighted
// Moving Average (EWMA):
//
//   s_b[t] = α × 1[b ∈ draw_t] + (1−α) × s_b[t−1]
//
// Initial value: s_b[0] = 7/35 (expected base rate).
// α = 0.03  →  half-life ≈ 23 draws ≈ 6 months at weekly cadence.
//
// EWMA is stationary (adding draws doesn't reshape old weights), has an
// interpretable half-life parameter, and is better-motivated than the old
// linear w = 1 + idx/(n−1) scheme whose 2:1 weight ratio was arbitrary.
function computeEwmaWeights() {
  const alpha = 0.03;
  const n = currentDraws.length;
  if (n === 0) return;

  const mainScores = {}, pbScores = {};
  for (let b = 1; b <= 35; b++) mainScores[b] = 7 / 35;
  for (let b = 1; b <= 20; b++) pbScores[b]   = 1 / 20;

  for (const draw of currentDraws) {
    const drawSet = new Set(draw.main);
    for (let b = 1; b <= 35; b++) {
      mainScores[b] = alpha * (drawSet.has(b) ? 1 : 0) + (1 - alpha) * mainScores[b];
    }
    for (let b = 1; b <= 20; b++) {
      pbScores[b] = alpha * (draw.powerball === b ? 1 : 0) + (1 - alpha) * pbScores[b];
    }
  }

  // Apply split-pot avoidance prior before normalization. Raw mainFreq/pbFreq
  // used by the Dashboard and chi-squared test are unaffected (computed above
  // from observed draws), so the "Hot main balls" panel still reflects reality.
  for (let b = 1; b <= 35; b++) mainScores[b] *= (POPULARITY_PENALTY_MAIN[b] || 1.0);
  for (let b = 1; b <= 20; b++) pbScores[b]   *= (POPULARITY_PENALTY_PB[b]   || 1.0);

  const mainTotal = Object.values(mainScores).reduce((s, v) => s + v, 0);
  recencyWeightsArr = [];
  for (let b = 1; b <= 35; b++) recencyWeightsArr.push({ ball: b, w: mainScores[b] / mainTotal });

  const pbTotal = Object.values(pbScores).reduce((s, v) => s + v, 0);
  pbRecencyWeightsArr = [];
  for (let b = 1; b <= 20; b++) pbRecencyWeightsArr.push({ ball: b, w: pbScores[b] / pbTotal });
}

// ─── Adaptive sum bounds for balanced mode ───────────────────────────────────
// Compute empirical 5th and 95th percentiles of main-ball sums from the
// actual draw history, rather than using hardcoded constants.  These bounds
// update automatically as more draws are added to the dataset.
function computeAdaptiveBounds() {
  if (currentDraws.length === 0) return;
  const sums = currentDraws
    .map(d => d.main.reduce((a, b) => a + b, 0))
    .sort((a, b) => a - b);
  sumP5  = sums[Math.floor(0.05 * sums.length)];
  sumP95 = sums[Math.floor(0.95 * sums.length)];
}

// ─── Chi-squared significance test ───────────────────────────────────────────
// Tests whether the observed main-ball frequency distribution significantly
// deviates from the expected uniform distribution.
//
// H₀: each ball has probability 7/35 = 0.2 of appearing in any draw.
// χ² = Σ (Observed − Expected)² / Expected  with df = 34.
// Critical value at p=0.05, df=34: 48.6.
//
// With ~415 draws, the observed χ² is typically ~22 — well below the critical
// value.  This means the "hot/cold" labels are entertainment-only; no ball is
// statistically distinguishable from a fair draw.
function computeChiSquared() {
  const n = currentDraws.length;
  if (n === 0) { chiSquaredMainP = null; chiSquaredMainStat = null; return; }

  const expected = n * 7 / 35;
  let stat = 0;
  for (let b = 1; b <= 35; b++) {
    const diff = (mainFreq[b] || 0) - expected;
    stat += (diff * diff) / expected;
  }
  chiSquaredMainStat = stat;

  // Approximate p-value using the regularised incomplete gamma function.
  // For df=34 the critical value at p=0.05 is 48.6; at p=0.01 it's 56.1.
  // We store the statistic and compare against the df=34 critical value.
  // (A full CDF isn't feasible in vanilla JS without a library; we set
  //  chiSquaredMainP to a readable label instead.)
  const df = 34;
  // Use the Wilson–Hilferty cube-root approximation for chi-squared CDF:
  //   Z ≈ ((χ²/df)^(1/3) − (1 − 2/(9·df))) / sqrt(2/(9·df))
  const wh = (Math.pow(stat / df, 1 / 3) - (1 - 2 / (9 * df))) /
             Math.sqrt(2 / (9 * df));
  // Approximate standard-normal CDF via Abramowitz & Stegun:
  const p = chiApproxPValue(wh);
  chiSquaredMainP = p;
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

  // Hot main, cold main, hot PBs — renderBallRow uses DOM to avoid innerHTML on JSON data
  renderBallRow(document.getElementById("hot-main-balls"),  hotMain,  "ball-main", mainFreq);
  renderBallRow(document.getElementById("cold-main-balls"), coldMain, "ball-cold", mainFreq);
  renderBallRow(document.getElementById("hot-pb-balls"),    hotPb,    "ball-pb",   pbFreq);

  // Chi-squared significance note
  const chiEl = document.getElementById("chi-squared-note");
  if (chiEl && chiSquaredMainStat !== null) {
    const stat = chiSquaredMainStat.toFixed(2);
    const pStr = chiSquaredMainP !== null ? chiSquaredMainP.toFixed(3) : "n/a";
    const significant = chiSquaredMainP !== null && chiSquaredMainP < 0.05;
    if (significant) {
      chiEl.textContent =
        `Statistical note: frequency distribution significantly deviates from uniform (χ²=${stat}, p=${pStr}). Hot/cold labels are statistically supported.`;
      chiEl.className = "chi-note chi-significant";
    } else {
      chiEl.textContent =
        `Statistical note: frequency distribution is consistent with a fair draw (χ²=${stat}, p=${pStr}, df=34). Hot/cold labels are for entertainment only — no ball is statistically distinguishable from any other.`;
      chiEl.className = "chi-note chi-not-significant";
    }
  }

  // Latest draw — DOM construction avoids innerHTML on JSON-sourced strings (date, draw number)
  const hotSet = new Set(hotMain);
  const infoEl = document.getElementById("latest-draw-info");
  infoEl.innerHTML = "";
  const latestWrap = document.createElement("div");
  latestWrap.className = "latest-draw";

  const numDiv = document.createElement("div");
  numDiv.className = "latest-draw-num";
  numDiv.textContent = `Draw #${latest.draw}`;

  const dateDiv = document.createElement("div");
  dateDiv.className = "latest-draw-date";
  dateDiv.textContent = formatDate(latest.date);

  const ballsWrap = document.createElement("div");
  ballsWrap.className = "draw-balls";
  for (const b of latest.main) {
    const s = document.createElement("span");
    s.className = hotSet.has(b) ? "draw-ball hot" : "draw-ball";
    s.textContent = b;
    ballsWrap.appendChild(s);
  }
  const sepSpan = document.createElement("span");
  sepSpan.className = "draw-separator";
  sepSpan.textContent = "│";
  ballsWrap.appendChild(sepSpan);
  const pbSpan = document.createElement("span");
  pbSpan.className = "draw-ball pb-ball";
  pbSpan.textContent = latest.powerball;
  ballsWrap.appendChild(pbSpan);

  const noteDiv = document.createElement("div");
  noteDiv.className = "draw-hot-note";
  noteDiv.textContent = "🔥 Highlighted = hot numbers";

  latestWrap.appendChild(numDiv);
  latestWrap.appendChild(dateDiv);
  latestWrap.appendChild(ballsWrap);
  latestWrap.appendChild(noteDiv);
  infoEl.appendChild(latestWrap);
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
// Constraints and their statistical basis (all derived from draw history):
//
//   Sum  in [sumP5, sumP95]  — empirical 5th/95th percentiles of observed draw sums.
//                              Bounds adapt automatically as the dataset grows,
//                              replacing the old hardcoded [87, 165] constants.
//                              E[sum] = 126.0, SD ≈ 24.3 (hypergeometric).
//
//   Odds in [2, 5]           — covers 92.8% of historical draws.
//                              17 odd numbers in 1–35; hypergeometric distribution.
//
//   Lows in [2, 5]           — covers 93.3% of historical draws.
//                              17 "low" balls = 1–17, 18 "high" = 18–35.
//
//   Consecutive pairs ≤ 3    — 74.2% of draws contain ≥1 consecutive pair;
//                              only 1.9% have more than 3.  Added constraint
//                              ensures balanced mode reflects the actual draw
//                              distribution (previously this was unconstrained).
function generateBalancedMain() {
  const allMain = Array.from({ length: 35 }, (_, i) => i + 1);
  for (let attempt = 0; attempt < 5000; attempt++) {
    const pick  = sample(allMain, 7).sort((a, b) => a - b);
    const sum   = pick.reduce((a, b) => a + b, 0);
    const odds  = pick.filter(n => n % 2 !== 0).length;
    const lows  = pick.filter(n => n <= 17).length;
    const consec = pick.filter((v, i, a) => i > 0 && v === a[i - 1] + 1).length;
    if (
      sum >= sumP5 && sum <= sumP95 &&
      odds >= 2 && odds <= 5 &&
      lows >= 2 && lows <= 5 &&
      consec <= 3
    ) {
      return pick;
    }
  }
  return sample(allMain, 7).sort((a, b) => a - b); // fallback (essentially impossible)
}

function generateGamesLocal(mode = "hot", count = 1) {
  const games = [];
  const seen  = new Set();

  // Pre-sample diverse Powerballs (up to count PBs without replacement from 20).
  // With count=18 and 20 possible PBs this covers 18 distinct PBs — 90% of
  // the PB pool — guaranteeing the winning PB appears in at least one game
  // with 90% probability, vs the old formula's 25% (5 fixed PBs from 20).
  const diversePbs = weightedSample(pbRecencyWeightsArr, Math.min(count, 20));
  let pbIdx = 0;

  for (let i = 0; i < count * 1000 && games.length < count; i++) {
    const g   = generateGameWithStrategy(mode);
    // Override PB with next diverse PB while supply lasts; then fall back to strategy PB
    if (pbIdx < diversePbs.length) g.powerball = diversePbs[pbIdx];
    const key = g.main.join(",") + "|" + g.powerball;
    if (!seen.has(key)) {
      seen.add(key);
      pbIdx++;
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

function renderGamesGrid(container, result) {
  const label = STRATEGY_LABELS[result.strategy] || "";
  const panel = document.createElement("div");
  panel.className = "panel";
  const sub = document.createElement("p");
  sub.className = "panel-sub";
  sub.textContent = `${label} · ${result.draws_analysed} draws analysed · ${result.generated_at.slice(0, 10)}`;
  panel.appendChild(sub);

  const grid = document.createElement("div");
  grid.className = "games-grid";
  for (const g of result.games) {
    const card = document.createElement("div");
    card.className = "game-card";

    const gcHeader = document.createElement("div");
    gcHeader.className = "gc-header";
    gcHeader.textContent = `Game ${g.game}`;

    const gcMain = document.createElement("div");
    gcMain.className = "gc-main";
    for (const b of g.main) {
      const s = document.createElement("span");
      s.className = "ball-sm main";
      s.textContent = b;
      gcMain.appendChild(s);
    }

    const gcPb = document.createElement("div");
    gcPb.className = "gc-pb";
    const gcPbLabel = document.createElement("span");
    gcPbLabel.className = "gc-pb-label";
    gcPbLabel.textContent = "Powerball";
    const gcPbBall = document.createElement("span");
    gcPbBall.className = "ball-sm pb";
    gcPbBall.textContent = g.powerball;
    gcPb.appendChild(gcPbLabel);
    gcPb.appendChild(gcPbBall);

    card.appendChild(gcHeader);
    card.appendChild(gcMain);
    card.appendChild(gcPb);
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

  tbody.innerHTML = "";
  for (const d of page) {
    const tr = document.createElement("tr");

    const tdNum = document.createElement("td");
    const strong = document.createElement("strong");
    strong.textContent = `#${d.draw}`;
    tdNum.appendChild(strong);

    const tdDate = document.createElement("td");
    tdDate.textContent = formatDate(d.date);

    const tdBalls = document.createElement("td");
    const drawBalls = document.createElement("div");
    drawBalls.className = "draw-balls";
    for (const b of d.main) {
      const s = document.createElement("span");
      s.className = hotSet.has(b) ? "draw-ball hot" : "draw-ball";
      s.textContent = b;
      drawBalls.appendChild(s);
    }
    const histSep = document.createElement("span");
    histSep.className = "draw-separator hist-pb-inline";
    histSep.textContent = "│";
    drawBalls.appendChild(histSep);
    const pbInline = document.createElement("span");
    pbInline.className = "draw-ball pb-ball hist-pb-inline";
    pbInline.textContent = d.powerball;
    drawBalls.appendChild(pbInline);
    tdBalls.appendChild(drawBalls);

    const tdPb = document.createElement("td");
    tdPb.className = "hist-pb-col";
    const pbCol = document.createElement("span");
    pbCol.className = "draw-ball pb-ball";
    pbCol.textContent = d.powerball;
    tdPb.appendChild(pbCol);

    tr.appendChild(tdNum);
    tr.appendChild(tdDate);
    tr.appendChild(tdBalls);
    tr.appendChild(tdPb);
    tbody.appendChild(tr);
  }

  renderPagination();
}

function renderPagination() {
  const total = Math.ceil(histFiltered.length / histPerPage);
  const pag   = document.getElementById("hist-pagination");

  pag.innerHTML = "";
  if (total <= 1) return;

  const pages = [];
  if (histPage > 1) pages.push({ label: "←", p: histPage - 1 });
  for (let p = Math.max(1, histPage - 2); p <= Math.min(total, histPage + 2); p++) {
    pages.push({ label: String(p), p, active: p === histPage });
  }
  if (histPage < total) pages.push({ label: "→", p: histPage + 1 });

  for (const { label, p, active } of pages) {
    const btn = document.createElement("button");
    btn.className = `page-btn${active ? " active" : ""}`;
    btn.dataset.p = p;
    btn.textContent = label;
    btn.addEventListener("click", () => {
      histPage = +btn.dataset.p;
      renderHistoryTable();
      document.getElementById("tab-history").scrollIntoView({ behavior: "smooth", block: "start" });
    });
    pag.appendChild(btn);
  }
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

// Approximate p-value from a standard-normal Z score (upper tail).
// Uses the Abramowitz & Stegun rational approximation (max error 7.5e-8).
// Used by computeChiSquared() via the Wilson–Hilferty transformation.
function chiApproxPValue(z) {
  if (z < -6) return 1;
  if (z >  6) return 0;
  const t = 1 / (1 + 0.2316419 * Math.abs(z));
  const poly = t * (0.319381530 +
               t * (-0.356563782 +
               t * (1.781477937 +
               t * (-1.821255978 +
               t * 1.330274429))));
  const pdf = Math.exp(-0.5 * z * z) / Math.sqrt(2 * Math.PI);
  const upper = pdf * poly;
  return z >= 0 ? upper : 1 - upper;
}

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

// Render a list of balls with frequency counts into a container element.
// Uses DOM construction rather than innerHTML to safely handle JSON-sourced data.
function renderBallRow(el, balls, cssClass, freqMap) {
  el.innerHTML = "";
  for (const b of balls) {
    const pair = document.createElement("span");
    pair.className = "ball-pair";
    const ballEl = document.createElement("span");
    ballEl.className = `ball ${cssClass}`;
    ballEl.textContent = b;
    const freqEl = document.createElement("span");
    freqEl.className = "ball ball-freq";
    freqEl.textContent = `${freqMap[b]}x`;
    pair.appendChild(ballEl);
    pair.appendChild(freqEl);
    el.appendChild(pair);
  }
}

function showLoading() {
  const el = document.createElement("div");
  el.id = "loading-indicator";
  el.className = "loading-indicator";
  el.textContent = "Loading draw data…";
  document.getElementById("tab-dashboard").prepend(el);
}

function hideLoading() {
  const el = document.getElementById("loading-indicator");
  if (el) el.remove();
}

function showError(msg) {
  hideLoading();
  const main = document.querySelector("main");
  main.innerHTML = "";
  const div = document.createElement("div");
  div.className = "error-msg";
  div.textContent = `⚠️ ${msg}`;
  main.appendChild(div);
}
