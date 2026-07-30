# 🎱 Thursday Numbers Analyser — Claude Code Project

## Project Summary

This is a full-stack web tool and automated pipeline for analysing Australian Powerball
historical draw data, generating statistically-informed number picks, and emailing results
on a scheduled basis via GitHub Actions.

Tagline: *"Every Thursday, smarter numbers."*

The project lives at:
- **GitHub:** https://github.com/androidua/thursday-numbers
- **Live site:** https://thursdaynumbers.com (hosted on Cloudflare Pages)

---

## Current Version

**v1.8.6** — see `web/VERSION` file.

---

## Versioning Rules

Use semantic versioning: `MAJOR.MINOR.PATCH`

| Digit | When to increment | Examples |
|---|---|---|
| MAJOR (1st) | Major redesign or large new feature set | Full UI overhaul, new analysis engine |
| MINOR (2nd) | New features or meaningful improvements | New chart, new tab, new script capability |
| PATCH (3rd) | Small fixes, typos, config tweaks | Bug fix, copy update, cron change |

**Rules:**
- Update `web/VERSION`, `README.md`, `CLAUDE.md`, **and the hardcoded fallback in `web/index.html` footer (`id="footer-version"`)** whenever you make changes
- The footer fallback in `index.html` must always match `web/VERSION` — it shows before the async fetch completes and on fetch failure
- **Bump the cache-bust query strings in `web/index.html`** — both `<link rel="stylesheet" href="style.css?v=X.X.X">` and `<script src="app.js?v=X.X.X">` must match the new version. Without this, Cloudflare's edge cache + Safari's aggressive CSS caching can leave users on stale assets for days after a fix is deployed (this happened with the v1.7.19 mobile scoreboard fix). Treat these query strings as part of the release artefact, not as boilerplate.
- Mention the version in every commit message and README changelog
- **Create and push a git tag on every version bump:** `git tag vX.X.X && git push origin vX.X.X` — writing the version in the commit message does NOT create a tag; these are separate operations
- Always push directly to `main` — this is a solo project, no branches needed

---

## Deployment: Cloudflare Pages

The site is deployed via **Cloudflare Pages** (not GitHub Pages).

**How it works:**
- Cloudflare Pages is connected to the GitHub repo (`androidua/thursday-numbers`)
- Every push to `main` triggers an automatic Cloudflare Pages build + deploy
- Build settings: no build command, output directory = `web/`
- The domain `thursdaynumbers.com` is managed in Cloudflare Pages custom domain settings
- No A records or CNAME file needed — Cloudflare handles all DNS internally

**Setup steps (one-time):**
1. Cloudflare Dashboard → Pages → Create a project
2. Connect to GitHub → select `androidua/thursday-numbers`
3. Framework preset: None | Build command: (empty) | Output dir: `web`
4. Deploy
5. Pages project → Custom domains → Add `thursdaynumbers.com`
6. Cloudflare automatically creates the required DNS record

---

## Automation Schedule

Two separate GitHub Actions workflows run on schedule:

**`email-picks.yml`** — Thursday 00:00 UTC (= 10am AEST / 11am AEDT):
1. Runs `scripts/generate_picks.py` — generates 18 fresh games (EWMA-weighted, full coverage, 18 distinct PBs)
2. Runs `scripts/email_picks.py` — sends HTML email via Brevo
3. Commits `web/picks/picks_history.json` if updated — consumed by `score_history.py` (Scoreboard) and `automate_picks.py` (cart fill); NOT fetched by the web frontend

**`powerball-update.yml`** — Thursday 18:00 UTC (= Friday 4am AEST / 5am AEDT):
1. Runs `scripts/scrape.py` — fetches any new draws since last recorded (stops at the first failed Thursday to keep numbering contiguous)
2. Runs `scripts/score_history.py` — rescores picks history → `web/scoreboard.json`
3. Updates `web/sitemap.xml` lastmod
4. Commits `web/data/powerball_draws.json`, `web/scoreboard.json`, `web/sitemap.xml` if changed
5. Runs `scripts/check_data.py --strict` AFTER the commit — a stale or corrupt data file turns the workflow red (GitHub emails on failure) without blocking the data commit
6. Cloudflare Pages auto-deploys on every push to `main`

**Why the two-workflow split?** Email sends *before* the draw (10am) using prior data. Scrape runs *after* the draw (4am next day) to capture results. These are deliberately separate cron jobs.

**Actions versions (Node.js 24):** `actions/checkout@v5`, `actions/setup-python@v6`

---

## Project Structure

```
thursday-numbers/
├── CLAUDE.md                              ← this file
├── README.md                              ← public-facing project description
├── requirements.txt                       ← Python dependencies
├── requirements-dev.txt                   ← dev-only dependencies (pytest)
├── Fill Powerball Numbers.command         ← macOS double-clickable shortcut → scripts/automate_picks.py (clears orphaned index.lock, syncs, then fills)
├── .github/
│   └── workflows/
│       ├── powerball-update.yml           ← GitHub Actions scrape (Thursday 18:00 UTC = Friday 4am AEST)
│       ├── email-picks.yml               ← GitHub Actions email (Thursday 00:00 UTC = 10am AEST)
│       └── tests.yml                      ← CI: pytest on every human push
├── scripts/
│   ├── scrape.py                          ← fetches new draws since last known draw
│   ├── scrape_historical.py               ← one-time backfill: year-archive pages 1996–2018
│   ├── generate_picks.py                  ← generates 18 games — EWMA + coverage portfolio (seeded since v1.6.0)
│   ├── email_picks.py                     ← sends picks via Brevo REST API
│   ├── score_history.py                   ← scores picks_history against draws → scoreboard.json (v1.6.0)
│   ├── automate_picks.py                  ← Playwright: log in to ozlotteries.com, fill 18 games, stop at cart (v1.7.0+); refuses anything but today's emailed picks (v1.8.2)
│   ├── run_all.py                         ← entry point: scrape → generate → email
│   ├── check_data.py                      ← data integrity + freshness validation (v1.8.0; --strict in CI)
│   └── bump_version.py                    ← updates every version stamp atomically (v1.8.0)
├── tests/                                 ← pytest suite (run: pytest -q); CI via .github/workflows/tests.yml
└── web/                                   ← served by Cloudflare Pages
    ├── VERSION                            ← current version number (read by app.js)
    ├── index.html                         ← static site
    ├── app.js                             ← vanilla JS analyser (loads data via fetch)
    ├── style.css                          ← dark-themed styles
    ├── _headers                           ← Cloudflare Pages HTTP security headers (CSP, HSTS, etc.)
    ├── robots.txt                         ← crawler policy + sitemap reference
    ├── sitemap.xml                        ← XML sitemap for search engine indexing
    ├── favicon.svg                        ← site icon, source of truth (v1.8.4; was web/option1.svg)
    ├── favicon.ico                        ← 16/32/48 raster fallback, generated from favicon.svg
    ├── apple-touch-icon.png               ← 180×180 iOS home-screen icon, opaque #0f1117 background
    ├── scoreboard.json                    ← pick-vs-draw performance log (v1.6.0); served to web app
    ├── data/
    │   └── powerball_draws.json           ← draw history; read/written by scripts; served to web app
    └── picks/
        └── picks_history.json             ← generated picks log; written by scripts; public but not fetched by the web app
```

**Single source of truth:** all scripts read from and write to `web/data/` and `web/picks/` directly. There is no separate root-level `data/` or `picks/` directory.

---

## What Has Been Built

### Data
- Complete history since #1 (1996-05-23), auto-appended weekly; current-format draws (Apr 2018+) are the analysis basis.
- Stored in `web/data/powerball_draws.json` (single location — no root-level copy)
- Format: `{"draw": 1144, "date": "2018-04-19", "main": [4,5,9,13,25,32,33], "powerball": 7}`
- Pre-2018 draws have fewer main balls (5 or 6); `app.js` filters to `main.length === 7` for all analysis

### Python Scripts
- `scrape.py` — finds missing Thursdays, fetches each from australia.national-lottery.com
- `scrape_historical.py` — one-time backfill via year-archive pages; supports `--dry-run` and `--start-year`
- `generate_picks.py` — EWMA-weighted two-phase coverage portfolio: 18 games spanning all 35 mains and 18 distinct PBs (the original top-10-main/top-5-PB hot pool was replaced in v1.5.16/17)
- `email_picks.py` — HTML email via Brevo REST API with coloured ball layout (indigo main, purple PB)
- `run_all.py` — local convenience pipeline (scrape → generate → email) with `--dry-run`; NOT used by the workflows, which run the steps individually. No gap check.
- `automate_picks.py` — Playwright: opens Chrome, logs in to ozlotteries.com using `OZ_EMAIL`/`OZ_PASSWORD` from `.env`, switches to manual pick mode, selects 18 games, fills all from the latest `picks_history.json` entry, clicks Add to cart, leaves browser open for the user to complete payment. Aborts unless those picks are today's emailed set (dated today + `source: "cron"`) — see "load-bearing patterns" and "The picks gate" under Script Details; do not regress either

### Web App
- Dark-themed single-page app: Dashboard, Frequency, Recent Trends, Number Picker, Scoreboard, History
- Number Picker supports 1-game, 18-game, or PowerHit generation with 4 strategies (hot/cold/mixed/random)
- Game results displayed as card grid (3-col desktop, 2-col tablet, 1-col mobile)
- Chart.js from CDN with SRI integrity check — no build step
- Loads `data/powerball_draws.json`, `scoreboard.json`, and `VERSION` via `fetch()` (paths relative to `web/`)
- Version displayed in footer (read at runtime from `web/VERSION`)

---

## Script Details

### `scripts/scrape.py`
- URL pattern: `https://australia.national-lottery.com/powerball/results/DD-MM-YYYY`
- Main balls: `<li class="ball medium pb ball">N</li>`
- Powerball: `<li class="ball medium pb powerball">N</li>`
- `time.sleep(0.5)` between requests; User-Agent: `Mozilla/5.0`

### `scripts/generate_picks.py`
Two-phase EWMA generator (v1.5.16/17 replaced the original top-10-main/top-5-PB hot pool):
- **EWMA scoring** per ball (α=0.03, half-life ≈23 draws ≈ 6 months) + split-pot popularity prior (v1.5.23)
- **Phase 1 (games 1–5):** all 35 main balls sampled without replacement in EWMA order, partitioned into 5 games — every main ball appears in every weekly batch
- **Phase 2 (games 6–18):** EWMA-weighted sampling; a candidate is rejected if it shares >4 mains with any existing game
- **Powerballs:** 18 distinct PBs pre-sampled without replacement (18/20 = 90% weekly PB coverage)
- **Determinism:** seed `YYYY-MM-DD-<draw count>` (v1.6.0); `source: "cron" | "local"` provenance (v1.8.0)
- **Honesty check:** chi-squared uniformity test attached to every entry — `freq_significant` has been false on all real data (observed frequencies are consistent with a fair draw), so the "hot" labels are presentation, not signal
- **Structure rationale** (audited v1.8.1 with a 1M-week Monte Carlo of this module): per-game odds are strategy-invariant (1 in 44); the coverage + diversity + PB-spread structure maximises P(≥1 prize per week) ≈ 40%, vs ≈16% for the old concentrated pool, at identical expected value

Output format per run:
```json
{
  "generated_at": "2026-07-16T02:03:33",
  "draws_analysed": 430,
  "data_range": "2018-04-19 to 2026-07-09",
  "ewma_alpha": 0.03,
  "popularity_prior": "v1.5.23",
  "seed": "2026-07-16-430",
  "source": "cron",
  "hot_main_balls": [1, 12, 15, 17, 22, 25, 27, 30, 32, 34],
  "hot_powerballs": [10, 14, 17, 18, 20],
  "freq_significant": false,
  "chi2_main": 21.6,
  "chi2_main_p": 0.951,
  "chi2_pb": 23.49,
  "chi2_pb_p": 0.2165,
  "games": [
    {"game": 1, "main": [6, 14, 25, 29, 30, 32, 33], "powerball": 14}
  ]
}
```

### `scripts/email_picks.py`
- Subject: `Thursday Numbers — your weekly games (YYYY-MM-DD)`
- HTML email with coloured ball table + plain text fallback
- Env vars: `BREVO_API_KEY`, `EMAIL_RECIPIENT`, `EMAIL_SENDER`

### `scripts/run_all.py`
- `--dry-run`: skip email send and data file writes
- Exits with code 1 on failure (GitHub Actions marks run as failed)

### `scripts/automate_picks.py` — load-bearing patterns
This script fills the Oz Lotteries cart end-to-end. Several patterns inside `select_numbers_for_game` and the cart-click block look like they could be simplified but are **load-bearing** — verified against the live DOM in v1.7.16-v1.7.18. **Do not "improve" or "simplify" them without re-verifying against the live page first.**

| Pattern | Why it's required |
|---|---|
| Click hidden `<input data-id="numberGrids_<numbers\|powerball>_hiddenCheckbox">`, never `<label for="N">` | The page emits `<input id="N">` twice per `N ∈ 1..20` (main grid + PB grid). HTML for/id resolution picks the first match — so PB `label[for="N"]` silently toggles the **main** grid's input. `data-id` uniquely scopes each grid. |
| `dispatch_event("click")`, never `.click()` | The hidden input is `opacity:0 absolute` on top of its label, AND `[data-id="lotterySubNavigation"]` is `sticky` covering the top ~114px. Both trip Playwright actionability checks on labels. `dispatch_event` fires a real DOM click React's onChange responds to, bypassing actionability. |
| Scope locators to `game_row = page.locator('[data-id="gameNumberSelect_gameRow"]').nth(game_index)` | The page's picker slide animation briefly mounts both old and new pickers, so global `input[id="N"]` matches 2 elements → strict-mode violation. |
| No `cellsContainer.click()` to switch games | Page auto-advances after PB click. Use a condition-based `wait_for(state="visible")` for `nth(game_index + 1)`'s picker; skip for the last game. |
| No `wait_for_url` after Add to cart | The waiter is set up after the click, misses the navigation event, times out at 15s, and the exception tears down the browser context — erasing the filled cart. Use `wait_for_load_state("domcontentloaded")` in try/except and print the final URL. |

Env vars: `OZ_EMAIL`, `OZ_PASSWORD` in `.env` at the repo root (gitignored). See `.env.example`. CLI flags: `--dry-run` prints picks without opening the browser; `--allow-stale` fills picks that are not today's emailed set. Triggered manually via `Fill Powerball Numbers.command` (macOS double-clickable).

#### The picks gate (v1.8.2) — do not weaken it
`automate_picks.py` is a **pure consumer**. Its job is to buy the numbers the Thursday email delivered, and it must have **no code path that generates numbers of its own.**

`picks_rejection_reason()` requires both:
- **dated today** — `email-picks.yml` generates and commits Thursday's picks at 00:00 UTC (10am AEST) on the morning of the draw, so an older entry belongs to a draw already drawn
- **`source: "cron"`** — proof the entry came from the Actions run that actually sent the email

The second half is the non-obvious one. `generate_picks.py` seeds on `<date>-<draw count>`, so a checkout behind by even one draw yields a different seed and therefore **18 completely different games under today's date**. A `source: "local"` entry dated today is not "close enough" — it is a different portfolio.

**Why this exists (2026-07-30):** a `.git/index.lock` left by a crashed git 10 days earlier blocked every `git pull`, freezing the checkout 5 commits / 2 draws behind. The old code saw picks "14 days old", silently regenerated off 430 draws instead of 432, and filled the cart with 18 games matching no email. The user caught it only by comparing against the email screenshot. **Reintroducing "regenerate when stale" recreates a silent wrong-numbers bug — the worst failure this repo can have, because the output looks confident and correct.** `tests/test_automate_picks.py` pins this, including a test asserting no subprocess call can reach `generate_picks.py`.

Layering: `Fill Powerball Numbers.command` fixes the *cause* (clears an orphaned `index.lock`, sets aside `picks_history.json` edits that block the merge, pulls) and is deliberately **best-effort and non-fatal** — a dropped wifi connection must not block a legitimate run whose picks are already correct on disk. The **hard gate is in Python**, on the picks themselves, where no sync outcome can weaken it and no git success can let wrong numbers through. Don't move the gate into the shell wrapper.

---

## Environment Variables / GitHub Secrets

| Secret Name | Description |
|---|---|
| `BREVO_API_KEY` | Brevo API key with transactional email permission |
| `EMAIL_RECIPIENT` | Email address to receive picks |
| `EMAIL_SENDER` | Verified sender email in Brevo |

Repo → Settings → Secrets and variables → Actions → New repository secret

---

## Current Data Stats

Live counts change weekly — read them from the data, don't record them here:
- **Total / latest draw:** `python3 -c "import json; d=json.load(open('web/data/powerball_draws.json')); print(len(d), d[-1])"`
- **Format eras:** 5-ball 1–45 (1996–2013), 6-ball 1–40 (2013–2018), 7-ball 1–35 + PB 1–20 (Apr 2018–present, `main.length === 7` filter)
- Hot/cold lists are computed at runtime by `app.js` and per-run by `generate_picks.py`; they are never authoritative in docs.

---

## SEO & Security (v1.3.1+, current)

This is a **public GitHub repo**. All web assets are intentionally public — no secrets live in `web/`.

### SEO implemented
| Element | File | Detail |
|---|---|---|
| Title + meta description | `index.html` | Descriptive, keyword-rich |
| Canonical URL | `index.html` | `<link rel="canonical" href="https://thursdaynumbers.com/">` |
| Open Graph tags | `index.html` | `og:title`, `og:description`, `og:url`, `og:type`, `og:site_name`, `og:locale` |
| Twitter Card | `index.html` | `twitter:card=summary`, title, description |
| Schema.org JSON-LD | `index.html` | `WebApplication` type, applicationCategory, free offer |
| `<h1>` heading | `index.html` | Header logo promoted from `<div>` to `<h1>` |
| `robots.txt` | `web/robots.txt` | Allows all crawlers; references sitemap |
| `sitemap.xml` | `web/sitemap.xml` | Single URL, `changefreq=weekly` |
| External link safety | `index.html` | All external links use `rel="noopener noreferrer"` |

### Security implemented
| Header / Feature | Where | Detail |
|---|---|---|
| Content-Security-Policy | `web/_headers` | `default-src 'none'`; allows only local scripts/styles, jsDelivr CDN, same-origin fetch. `img-src` is `'self'` only — `data:` was dropped in v1.8.4 when the inline data-URI emoji favicon was replaced by `/favicon.svg`. The site loads no other images, so don't re-add `data:` without a real consumer. |
| X-Frame-Options | `web/_headers` | `DENY` — prevents all iframe embedding (clickjacking) |
| X-Content-Type-Options | `web/_headers` | `nosniff` — prevents MIME-type confusion attacks |
| Referrer-Policy | `web/_headers` + `index.html` | `strict-origin-when-cross-origin` |
| Permissions-Policy | `web/_headers` | Blocks camera, mic, geolocation, payment, USB, FLoC |
| HSTS | `web/_headers` | `max-age=31536000; includeSubDomains` (supplementary to Cloudflare's own HSTS) |
| SRI on Chart.js | `index.html` | `integrity="sha384-..."` + `crossorigin="anonymous"` — CDN tampering protection |
| No inline styles | `app.js` + `style.css` | Inline styles replaced with CSS classes; enables clean CSP without `unsafe-inline` |

### SRI maintenance rule
**If Chart.js version is ever upgraded**, the SRI hash in `index.html` must be recomputed:
```bash
curl -s "https://cdn.jsdelivr.net/npm/chart.js@VERSION/dist/chart.umd.min.js" | openssl dgst -sha384 -binary | base64
```
Then update the `integrity="sha384-..."` attribute in `index.html` to match.

Current locked version: `chart.js@4.4.0`
Current hash: `sha384-e6nUZLBkQ86NJ6TVVKAeSaK8jWa3NhkYWZFomE39AvDbQWeie9PlQqM3pmYW5d1g`

---

## Key Technical Decisions

| Decision | Choice | Reason |
|---|---|---|
| Hosting | Cloudflare Pages | Domain is on Cloudflare; auto-deploys on push; no A record setup needed |
| Email | Brevo REST API (via `requests`) | Free forever (300/day); no SDK needed; API key safe for public repos |
| Email schedule | Thursday 00:00 UTC (`email-picks.yml`) | 10am AEST — sends picks before that evening's draw |
| Scrape schedule | Thursday 18:00 UTC (`powerball-update.yml`) | Friday 4am AEST — after draw results are published |
| Number strategy | EWMA-weighted coverage portfolio (v1.5.16/17): all 35 mains covered, 18 distinct PBs, ≤4-ball inter-game overlap, split-pot prior (v1.5.23) | Per-game odds are fixed at 1-in-44 regardless of numbers — the structure instead maximises P(≥1 prize per week) (~40% vs ~16% for the old top-10/top-5 hot pool) at identical EV |
| Games per run | 18 | User buys 18 standard games per draw |
| Web framework | Vanilla JS + Chart.js CDN | No build step; Cloudflare Pages serves static files directly |
| Data storage | JSON files in repo | Simple, version-controlled, human-readable diffs |
| Branch strategy | Push directly to `main` | Solo project; no branching needed |
| Security headers | `web/_headers` file | Cloudflare Pages native approach — zero infrastructure, applied at edge |
| No inline styles in JS | CSS classes only | Keeps CSP clean (`style-src 'self'` with no `unsafe-inline`) |
| Oz Lotteries cart-fill clicks | `input[data-id="numberGrids_*_hiddenCheckbox"]` + `dispatch_event("click")` scoped to `gameRow.nth(i)` | Page has duplicate `id="N"` across main/PB grids (silent wrong-toggle on `label[for=N]`), input/sticky-nav occlude labels, and the picker animation briefly mounts two grids. See `automate_picks.py` script details. |
| Cart-fill picks source | Abort unless the newest entry is dated today AND `source: "cron"`; never generate locally | The seed is `<date>-<draw count>`, so a checkout behind on draws produces 18 different games under today's date. Regenerating on staleness fills the cart with numbers matching no email — and looks successful while doing it (2026-07-30). |
| Where the picks gate lives | Python (`automate_picks.py`), not the `.command` wrapper | The wrapper's sync is best-effort: an offline run whose picks are already correct must not be blocked. Only a check on the picks themselves is sound in every case. |

---

## Important Disclaimers

> Powerball is a game of pure chance. Each draw is independent and random.
> Past results have zero statistical influence on future draws.
> This tool is for entertainment only. Please gamble responsibly.
> For help with gambling: gamblinghelponline.org.au or call 1800 858 858.

---

## Notes for Claude Code

- Always read this file first before starting any task
- **Always update `VERSION`, `CLAUDE.md`, `README.md`, the `id="footer-version"` fallback in `web/index.html`, AND the `style.css?v=X.X.X` / `app.js?v=X.X.X` cache-bust query strings in `web/index.html` when making changes**
- **Always create and push a git tag on every version bump** — `git tag vX.X.X && git push origin vX.X.X` — the version in the commit message is NOT a tag
- **Always push directly to `main`** — no branches
- The `data/powerball_draws.json` file is the single source of truth — never overwrite, only append
- All scripts should be runnable standalone: `python scripts/scrape.py`
- Use `argparse` for CLI flags; `json.dumps(..., indent=2)` for all JSON writes
- Write clear `print()` statements so GitHub Actions logs are readable
- The web app needs an HTTP server to run locally (uses `fetch()` for JSON)
- **Never add inline `style="..."` attributes to JS-generated HTML** — use CSS classes to preserve the strict CSP
- **Scope mobile table-collapse rules to a table ID, not `.table-wrap`** — multiple tables (`#history-table`, `#scoreboard-table`) share the `.table-wrap` parent. A `@media` rule like `.table-wrap tbody tr { display: flex }` will silently leak across tables and beat lower-specificity defaults like `.scoreboard-detail { display: none }`. v1.7.19 fixed exactly this regression. When adding a new responsive table, use `#that-table tbody tr { ... }`.
- **Never fetch `style.css?v=X.X.X` / `app.js?v=X.X.X` to verify a deploy until `/VERSION` already reports the new version.** Cloudflare caches per exact URL including the query string, with `max-age` in the hours. Requesting the *new* versioned URL while the origin still serves the *old* build writes stale content into the edge cache under the new key — pinning the very URL `index.html` references to pre-deploy assets for the full TTL, and defeating the cache-bust entirely. This happened in v1.8.5: a verification curl fired ~20s after the push, and the site then served new HTML with old CSS (which looks *more* broken than not deploying at all, since new markup meets missing rules).
  **Correct order:** poll `/VERSION` until it flips → confirm the origin is current by fetching the asset with a *throwaway* query string (`style.css?zzz=<random>`, its own cache key, harmless to poison) → only then touch the real versioned URL. To recover from a poisoned key: purge that URL in the Cloudflare dashboard, or ship the next patch version so the URL changes.
- **After every visible fix, hard-refresh the live site** — Cloudflare Pages deploys in seconds, but iOS Safari aggressively caches `style.css` / `app.js` until next reload. The cache-bust query strings in `<link>` and `<script>` (bumped per release) are what makes returning users see the fix. If a user reports a fix isn't live, check the deployed `/VERSION` and the live CSS contents before re-debugging — it's usually their cache.
- **If upgrading Chart.js**, recompute the SRI hash (see SRI maintenance rule above) and update `integrity` in `index.html`
- **Do not add a `?v=X.X.X` cache-bust to the favicon/icon links** — the CSS and JS query strings are managed by `bump_version.py` and enforced by `tests/test_version_consistency.py`; an icon stamp neither of them knows about would silently drift out of sync on the next release. Icons carry a 1-week `Cache-Control` in `web/_headers` instead. If an icon ever changes, rename the file or purge the Cloudflare cache.
- **Never put a `background-clip: text` gradient on an element that also contains emoji** — `-webkit-text-fill-color: transparent` suppresses a colour emoji's own bitmap, so the gradient shows through its silhouette and the emoji renders as a flat blob. This is what made the header 🎱 a plain orange circle until v1.8.5. Scope the effect to a span wrapping only the words (`.header-logo-text`), and keep decorative emoji in a sibling span marked `aria-hidden="true"`.
- **Icons are all generated from `web/favicon.svg`** — if you change the artwork, regenerate `favicon.ico` and `apple-touch-icon.png` from it rather than editing them separately, or the variants drift apart. The touch icon needs an opaque `#0f1117` background; iOS renders transparency as black.
- The `web/_headers` file controls all HTTP security headers — edit there, not in `index.html` meta tags (meta tags are a fallback only)
- **Workflow auto-commits must use `[skip actions]`, never `[skip ci]`** — Cloudflare Pages respects `[skip ci]` and will silently skip the deployment. `[skip actions]` prevents GitHub Actions re-runs without blocking Cloudflare Pages. Also, never mention `[skip ci]` anywhere in a commit message body, as Cloudflare Pages scans the full message.
- **Do not "simplify" the click strategy in `scripts/automate_picks.py`** — the `input[data-id="..."]` + `dispatch_event("click")` + per-row scoping is load-bearing (see Script Details for `automate_picks.py`). Reverting to `label[for=N].click()` silently breaks PB selection because the page has duplicate `id` attributes; reverting to `.click()` instead of `dispatch_event` re-introduces occlusion failures. Verify against the live page before changing any selector here.
- **Never let `automate_picks.py` generate picks** — it must fill the cart only with picks dated today and carrying `source: "cron"`, and abort otherwise (see "The picks gate" in Script Details). "Regenerate when the saved picks look stale" reads like a convenience and is actually a silent wrong-numbers bug: the seed is `<date>-<draw count>`, so a checkout one draw behind yields 18 entirely different games under the same date. This shipped and reached the cart on 2026-07-30.
- **When a git operation fails inside a user-facing script, do not `|| echo "continuing anyway"`** — verify the outcome (`HEAD` vs `origin/main`) rather than trusting an exit code, and make the downstream step prove its own inputs are right. A stale `.git/index.lock` silently froze this repo 5 commits back for 10 days because a failed pull was reported as a shrug.
- **For Playwright/DOM-integration bugs, inspect the live target before iterating** — v1.7.11-15 shipped five failed patches for the cart-fill because no one verified `pbsChecked` actually changed after a PB click. Use the Playwright MCP (`browser_navigate`, `browser_evaluate`) to read real state before forming a hypothesis.
- **Run `pytest -q` before every push** — the suite covers scraper parsing/numbering, scorer division mapping and dedupe, generator invariants, data validation, and version-stamp consistency
- **Use `python scripts/bump_version.py X.Y.Z` for version bumps** — it updates `web/VERSION`, both cache-bust query strings, the footer fallback, the README badge, and the CLAUDE.md version line atomically, and aborts if any stamp is missing. The changelog entry and git tag remain manual.
