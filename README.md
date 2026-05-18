# 🎱 Thursday Numbers

> **Every Thursday, smarter numbers.**

Statistical analysis of Australian Powerball historical draw data. Generates 18 hot-number game picks and emails them weekly via Brevo — all driven by a free GitHub Actions workflow.

🌐 **Live site:** [thursdaynumbers.com](https://thursdaynumbers.com) — hosted on Cloudflare Pages

**Current version: v1.7.20**

---

## What it does

| Feature | Detail |
|---|---|
| 📊 Web dashboard | Frequency charts, hot/cold numbers, recent trends, full draw history |
| 🎯 Number picker | 18 hot-number games per run (7 main + 1 Powerball each) |
| 🤖 Auto-update | GitHub Actions runs every Friday at 4am AEST; full pipeline runs every week |
| 📧 Email delivery | HTML email via Brevo with all 18 games beautifully formatted |
| 📂 Data | 1,555 draws from May 1996 onward (complete history); analysis uses current-format draws (2018–present) |

---

## How the number generation works

1. **EWMA scoring** — each ball's score is updated draw-by-draw using an Exponentially Weighted Moving Average (α=0.03, half-life ≈23 draws / 6 months). Recent appearances count more without arbitrarily discarding older history.
2. **Chi-squared test** — the dashboard shows whether observed frequencies significantly deviate from a fair uniform distribution. With ~415 draws the answer is typically "no" — hot/cold labels are entertainment, not prediction.
3. **Greedy portfolio coverage (games 1–5)** — all 35 main balls are sampled without replacement in EWMA-probability order and partitioned into 5 games of 7, guaranteeing every ball appears at least once in the weekly batch.
4. **Diverse fill (games 6–18)** — EWMA-weighted random sampling with pair-diversity rejection: no two games share more than 4 main balls, preventing redundant near-duplicate picks.

> ⚠️ **Important disclaimer:** Powerball is a game of pure chance. Each draw is completely independent. Past frequencies have **zero** influence on future draws. This tool is for entertainment only. If gambling is causing you problems, contact [Gambling Help Online](https://www.gamblinghelponline.org.au) or call **1800 858 858**.

---

## Project structure

```
thursday-numbers/
├── scripts/
│   ├── scrape.py                     ← Fetch new draws from the web
│   ├── generate_picks.py             ← Generate 18 hot-number games
│   ├── email_picks.py                ← Send picks via Brevo
│   └── run_all.py                    ← Full pipeline entry point
├── web/                              ← Served by Cloudflare Pages
│   ├── VERSION                       ← Current version number
│   ├── index.html                    ← Static site
│   ├── app.js                        ← Vanilla JS analyser
│   ├── style.css                     ← Dark-themed styles
│   ├── _headers                      ← Cloudflare Pages HTTP security headers
│   ├── robots.txt                    ← Crawler policy
│   ├── sitemap.xml                   ← XML sitemap
│   ├── data/
│   │   └── powerball_draws.json      ← Draw data served to the web app
│   └── picks/
│       └── picks_history.json        ← Pick history served to the web app
├── .github/workflows/
│   ├── powerball-update.yml          ← GitHub Actions scrape (Friday 4am AEST)
│   └── email-picks.yml               ← GitHub Actions email (Thursday 10am AEST)
└── requirements.txt
```

---

## Running locally

```bash
git clone https://github.com/androidua/thursday-numbers.git
cd thursday-numbers

pip install -r requirements.txt

# Scrape any new draws
python scripts/scrape.py

# Generate picks (prints to console without saving)
python scripts/generate_picks.py --dry-run

# Full pipeline dry-run (no email sent, no files written)
python scripts/run_all.py --dry-run
```

The web app loads data via `fetch()`, so it needs HTTP — it won't work from `file://`. Use any simple server:

```bash
cd web
python -m http.server 8080
# Then open http://localhost:8080
```

---

## Setting up your own fork

### 1. Fork & clone

```bash
gh repo fork androidua/thursday-numbers --clone
cd thursday-numbers
```

### 2. Get a Brevo API key (free forever)

1. Sign up at [brevo.com](https://brevo.com) — free tier = 300 emails/day, no expiry
2. Top-right menu → your name → **SMTP & API → API Keys tab**
3. Click **"Generate a new API key"** → name it → Generate
4. Copy the key (shown once)
5. **Settings → Senders & IP Addresses → Senders → Add a new sender** — verify your sender email

### 3. Add GitHub Secrets

**Repo → Settings → Secrets and variables → Actions → New repository secret**

| Secret name | Value |
|---|---|
| `BREVO_API_KEY` | Your Brevo API key |
| `EMAIL_RECIPIENT` | Email address to receive picks |
| `EMAIL_SENDER` | Verified Brevo sender email |

### 4. Deploy with Cloudflare Pages

This project is designed for **Cloudflare Pages** (not GitHub Pages — no A records needed).

1. **Cloudflare Dashboard → Workers & Pages → Create → Pages → Connect to Git**
2. Select your forked `thursday-numbers` repo
3. Configure the build:
   - Framework preset: **None**
   - Build command: *(leave empty)*
   - Build output directory: `web`
4. Click **Save and Deploy**
5. Once deployed, go to **Custom domains → Add a domain** → enter your domain
6. Cloudflare automatically creates the DNS record — no manual A records required

Every push to `main` triggers an automatic Cloudflare Pages redeploy.

---

## Automation schedule

Two separate GitHub Actions workflows run on a schedule:

**`email-picks.yml`** — Thursday 10am AEST (Thursday 00:00 UTC)
- Generates 18 fresh hot-number picks from current draw data
- Sends a formatted HTML email via Brevo
- Commits updated `web/picks/picks_history.json` (powers the History tab)

**`powerball-update.yml`** — Friday 4am AEST (Thursday 18:00 UTC)
- Scrapes any new draws published after Thursday evening's draw
- Commits updated `web/data/powerball_draws.json`
- Cloudflare Pages auto-deploys on every push

---

## Data source

Draw data scraped from [australia.national-lottery.com](https://australia.national-lottery.com/powerball). Complete history from draw #1 (May 1996) through present.

Three format eras are stored in the data:
- **1996–2013** — 5 main balls from 1–45
- **2013–2018** — 6 main balls from 1–40
- **2018–present** — 7 main balls from 1–35, Powerball from 1–20 (current format)

All frequency analysis, charts, hot/cold picks, and trends use **current-format draws only** to avoid cross-era statistical pollution.

---

## Security & SEO

### SEO

| Practice | Implementation |
|---|---|
| Primary meta tags | `<title>`, `<meta name="description">`, `<meta name="robots">` |
| Canonical URL | `<link rel="canonical" href="https://thursdaynumbers.com/">` |
| Open Graph | `og:type`, `og:title`, `og:description`, `og:url`, `og:site_name`, `og:locale` |
| Twitter / X Card | `twitter:card`, `twitter:title`, `twitter:description` |
| Schema.org JSON-LD | `WebApplication` structured data (name, URL, description, free offer) |
| Semantic HTML | Page title is an `<h1>`; logical heading hierarchy throughout |
| Sitemap | `web/sitemap.xml` — referenced in `robots.txt` |
| Crawler policy | `web/robots.txt` — `Allow: /` with sitemap pointer |

### Security

All HTTP security headers are applied at the Cloudflare edge via `web/_headers`:

| Header | Value / Purpose |
|---|---|
| `Content-Security-Policy` | `default-src 'none'`; allowlist-only for scripts, styles, images, and fetch — no `unsafe-inline` |
| `X-Frame-Options` | `DENY` — prevents clickjacking |
| `X-Content-Type-Options` | `nosniff` — prevents MIME-sniffing attacks |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | Disables camera, mic, geolocation, payment, USB, and FLoC |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` — enforces HTTPS |
| `X-XSS-Protection` | `1; mode=block` — legacy XSS filter for older browsers |

Additional hardening:
- **Subresource Integrity (SRI)** — Chart.js CDN locked to a SHA-384 hash; tampered files are rejected by the browser
- **`rel="noopener noreferrer"`** on all external links — prevents `window.opener` access and referrer leakage
- **No inline styles in JS** — all dynamic styles use CSS classes, enabling a strict `style-src 'self'` CSP with no `unsafe-inline`
- **No secrets in repo** — Brevo API key and email addresses are GitHub Secrets only; `web/` contains zero credentials

---

## Tech stack

| Layer | Choice | Reason |
|---|---|---|
| Hosting | Cloudflare Pages | Domain on Cloudflare; auto-deploys on push; no extra DNS setup |
| Frontend | Vanilla HTML/CSS/JS + Chart.js (CDN) | No build step — static files only |
| Scraping | Python + requests + BeautifulSoup | Simple, reliable |
| Email | Brevo REST API (via requests) | Free forever tier; no extra SDK needed |
| Automation | GitHub Actions cron | Free, serverless |
| Data | JSON files in repo | Simple, version-controlled |

---

## Changelog

### v1.7.20 — 2026-05-18
- Chore: Added cache-bust query strings to `<link href="style.css?v=X.X.X">` and `<script src="app.js?v=X.X.X">` in `index.html`. Without this, Cloudflare Pages deploys correctly but iOS Safari keeps serving the old CSS/JS from local cache — users reported the v1.7.19 scoreboard fix as "still broken" while the bytes on the wire were already correct. Bumping the query string per release forces a clean fetch. Documented as a mandatory version-bump step in CLAUDE.md and MEMORY.md so this never recurs.
- Docs: Captured two project-specific lessons in CLAUDE.md — (a) scope mobile table-collapse rules to a table ID, never `.table-wrap`, to prevent specificity collisions between sibling tables; (b) check `/VERSION` and live CSS before re-debugging a user-reported regression, since 9/10 of "still broken" reports on this site are stale-cache.

### v1.7.19 — 2026-05-16
- Fix: Scoreboard detail rows were expanded by default on phones (≤600px). Root cause was a CSS specificity collision — the History tab's mobile row-collapse rule `.table-wrap tbody tr { display: flex; ... }` (specificity 0,0,1,2) was overriding `.scoreboard-detail { display: none; }` (0,0,1,0), because both tables share the `.table-wrap` wrapper. Scoped the History mobile block to `#history-table` so its rules no longer leak into the Scoreboard. Wider mobile audit of the other five tabs found no further issues — charts are responsive, the Picker grid reflows 3→2→1 col cleanly, and the nav strip already has an edge-fade hint at ≤700px.

### v1.7.18 — 2026-05-16
- Fix: `wait_for_url` after Add to cart was set up after the click, so it missed the navigation event and timed out — the resulting crash closed the browser context and erased the just-filled cart. Replaced with `wait_for_load_state("domcontentloaded")` + a brief settle; the script no longer enforces a specific destination URL (oz lotteries may route through `/cart`, `/cart/checkout`, or a transitional page) and prints whatever URL we ended up at. Removed the now-unused `CART_URL` constant.

### v1.7.17 — 2026-05-16
- Fix: strict-mode violation on game 3+ in `automate_picks.py` — during the page's picker slide animation the previous game's picker briefly stays mounted while the new one renders, so `input[id="N"]` matched two elements. Scoped all selectors to the current game's `nth(game_index)` row via `game_row.locator(...)`.

### v1.7.16 — 2026-05-16
- Fix: Powerball number entry on ozlotteries.com — three compounded defects identified by live DOM inspection:
  1. **PB selection silently toggled the wrong checkbox** since the feature was first written. The page emits two `<input id="N">` per `N ∈ 1..20` (main grid + PB grid); HTML for/id resolution hits the first match, so `label[data-id="numberGrids_powerball_numberItem"][for="N"]` always toggled the MAIN grid's input.
  2. Hidden `<input>` (opacity:0, absolute, same rect as the label) intercepts pointer events, tripping Playwright's actionability check on `label.click()`.
  3. Sticky `lotterySubNavigation` covers the top ~114px of viewport, blocking scrolled-into-view labels.
- Switched to `input[data-id="numberGrids_<type>_hiddenCheckbox"][id="N"]` selectors with `dispatch_event("click")`, which targets the correct grid and fires a real DOM click that React's onChange picks up while bypassing actionability checks.
- Removed now-redundant `cellsContainer.click()` accordion call — the page auto-advances after the 8th selection (PB). Added a condition-based wait for the next game's picker to render before the loop continues; skipped for the last game.

### v1.7.15 — 2026-05-16
- Fix: game 1 timeout caused by "Play favourite numbers" tooltip overlaying the number picker — Playwright's occlusion check blocked all label clicks until the tooltip cleared; now explicitly clicks the tooltip X button before the fill loop (Escape was unreliable); `[data-id="tooltipInfo_root"] button[type="button"]` with 3s timeout, no-op if tooltip absent

### v1.7.14 — 2026-05-16
- Fix: game 1 picker timeout — remove `is_visible()` guard + explicit `wait_for` in `select_numbers_for_game`; for game 0 skip accordion click entirely (picker pre-opened on page load); for games 2–18 click `gameNumberSelect_gameRowCellsContainer` header instead of full row; rely on Playwright click() actionability auto-wait throughout

### v1.7.13 — 2026-05-16
- Fix: replace 800ms fixed wait after game-count select with condition-based wait (`nth(17).wait_for(visible)`) — fixes game 1 and 2 picker timeouts caused by React re-render not finishing in time; replace fragile `[class*="NumberPickerWrapper"]` selector with stable `label[data-id="numberGrids_numbers_numberItem"]` wait; handle game 0 accordion defensively

### v1.7.12 — 2026-05-16
- Fix: switch number clicks from JS `element.click()` to Playwright `locator.click()` — JS synthetic click only fires the `click` event and misses React's `onPointerDown`/`onMouseDown` handlers; Playwright fires the full native mouse event sequence (pointerdown, mousedown, mouseup, click); also fix Add to Cart selector to `[data-id="addToCart_button"]` to avoid strict-mode ambiguity with a second button on the page

### v1.7.11 — 2026-05-16
- Fix: PB grid uses a different `data-id` from main-ball grid (35 main labels confirmed, PB labels have a different attribute); `click_pb()` now tries `data-id="numberGrids_powerball_numberItem"` first, then falls back to text-matching across all non-main labels and reports the actual `data-id` found; `click_main()` split into separate function for clarity

### v1.7.10 — 2026-05-16
- Fix: Oz Lotteries lazy-renders pickers — only the open game's `NumberPickerWrapper` is mounted (always exactly 1, not 18); `wait_for_function` now checks `!!querySelector(...)` (1 picker) not `length >= 18`; game row accordion is explicitly clicked for games 2-18 before filling; `querySelector` replaces index-based `pickers[N]` lookup; PB "ok:1" warning added to detect single-label edge case

### v1.7.9 — 2026-05-15
- Fix: number-filling rewritten to use game-index-scoped DOM targeting instead of offsetHeight visibility check; `offsetHeight > 0` is unreliable when the site uses `overflow:hidden` collapse (all 18 pickers appear open); direct `picker[N].querySelector(label)` bypasses accordion state entirely; JS `element.click()` still fires React events on hidden elements via event delegation; added per-click success/failure return and first-game diagnostic showing picker count and open count

### v1.7.8 — 2026-05-15
- Fix: number-filling rewritten to use JS-based clicking scoped to the currently open picker (offsetHeight > 0), bypassing React remount timing and multi-picker DOM ambiguity; games auto-advance so accordion management removed entirely; tooltip dismissed with Escape before filling

### v1.7.7 — 2026-05-14
- Fix: password step now uses `input[type="password"]` selector instead of `#loginRegisterEmail_password` — avoids React remount timing issue where the ID-based locator fails during component re-render after email submit; final login button corrected to data-id selector

### v1.7.6 — 2026-05-14
- Fix: login now waits for `networkidle` after email submit before looking for the password field — gives Oz Lotteries' email-check API call time to complete and the password step to render

### v1.7.5 — 2026-05-14
- Fix: `Fill Powerball Numbers.command` now runs `git pull origin main` on every launch — no more manual pulls needed after fixes

### v1.7.4 — 2026-05-14
- Fix: login "Continue" button now targeted by `data-id="loginRegisterEmail_submit"` instead of role+name — eliminates strict mode violation caused by "Continue with Apple" button also matching the role/name selector

### v1.7.3 — 2026-05-14
- Fix: `automate_picks.py` now auto-generates fresh picks if the latest entry is 6+ days old, so the script always enters this week's numbers regardless of whether the GitHub Actions workflow has already run
- Fix: login flow — final submit button after password step corrected to "Continue" (matching Oz Lotteries two-step login UI)

### v1.7.2 — 2026-05-14
- Fix: Oz Lotteries login updated for two-step ("email-first") flow — email is now submitted first, then the script waits for the password field to become visible before filling it and clicking "Log in"

### v1.7.1 — 2026-05-14
- Fix: Added `Cache-Control: no-cache` for `index.html` in `web/_headers` — browsers now always revalidate the HTML before serving from cache, so new deployments surface immediately without requiring a hard refresh. Reduced `stale-while-revalidate` on `app.js`/`style.css` from 24h to 1h to limit stale JS exposure after deployments

### v1.7.0 — 2026-05-14
- Feature: **Oz Lotteries Powerball automation** — new `scripts/automate_picks.py` reads the latest 18 picks from `picks_history.json`, opens Chrome via Playwright, logs in to ozlotteries.com, switches to "Pick your numbers" mode, selects 18 games, fills every ball for all 18 games, and stops at the cart for manual payment. `Fill Powerball Numbers.command` at the project root is a double-clickable macOS launcher. `.env.example` added as credential template. Local one-time setup: `pip install playwright python-dotenv && playwright install chromium`

### v1.6.2 — 2026-05-14
- Copy: Scoreboard page reframed from personal ("your picks") to public-facing — panel now describes the site's automated Thursday workflow emailing 18 picks to its creator, with the scoreboard as the public track record. Removed all "your/you" language. Stat label renamed to "Prize Wins"; column header to "Best Result"; division chart and weekly breakdown subtitles updated to match

### v1.6.1 — 2026-05-14
- Scoreboard reframed as personal — "Your Personal Scoreboard" with copy clarifying these are the 18 games delivered to the user's Thursday email, scored against the actual draw. Stat labels updated: Emails Tracked / Games Played / Your Prize Hits / Best Result. Footnote: "Auto-updates every Friday morning AEST after the draw is announced"
- Scoreboard rows are now expandable — clicking a week reveals all 18 emailed picks for that draw, with main balls rendered green when they matched the actual winning numbers and the PB ringed in green when it matched
- Scoreboard now filters to Thursday-cron email runs only — the 8 dev/test entries from 2026-03-15 (Sunday) that were written while the v1.5.5 commit-after-email fix was being developed are no longer scored. `scripts/score_history.py` adds an `is_email_run()` helper using day-of-week, and surfaces the excluded count via a new `skipped_non_email` field on the scoreboard payload. Real emailed weeks tracked: 8 (since 2026-03-19)
- `scoreboard.json` now embeds each game's emailed picks (`main` + `powerball`) alongside the match summary, so the UI can render the actual numbers without a second fetch of `picks_history.json`
- Verified: all four recent emails (2026-04-16, 2026-04-23, 2026-04-30, 2026-05-07) match `picks_history.json` byte-for-byte — picks emailed = picks stored = picks scored

### v1.6.0 — 2026-05-13
- Feature: **Scoreboard tab** — new `scripts/score_history.py` joins `picks_history.json` against `powerball_draws.json`, maps each game to its Australian Powerball division (Div 1–9), and produces `web/scoreboard.json`. New "🏆 Scoreboard" tab on the site shows weeks scored, total games, any-prize count and rate, best division ever hit, a division-hits bar chart, and a per-week breakdown table. Auto-refreshes via `powerball-update.yml` every Thursday evening AEST after the scrape. Backfills all existing 16 weeks (288 games) on first run. Picks-vs-draw matching uses the earliest draw with `date >= generated_at[:10]` (handles same-day Thursday match and degrades gracefully); entries generated after the most recent recorded draw are flagged "pending"
- Feature: **Seeded determinism** in `scripts/generate_picks.py` — seed derived from `YYYY-MM-DD-<len(draws)>` so the same UTC date + same dataset produces byte-identical picks. Lets the user reproduce the emailed batch locally from the public data with no hidden state. Seed value included in `picks_history.json` for transparency. Web app deliberately remains non-deterministic (the site is for experimentation)
- Improvement: **Web app coverage parity** — `generateGamesLocal()` in `web/app.js` now matches the Python script's two-phase generator for `hot` and `mixed` modes at 18 games. Phase 1 (games 1–5) guarantees every main ball 1–35 appears at least once; Phase 2 (games 6–18) enforces pair-diversity (no two games share more than 4 main balls). `cold` and `random` strategies unchanged (coverage doesn't apply by design)
- Workflow: `powerball-update.yml` now runs `score_history.py` after the scrape and commits `web/scoreboard.json` alongside the draws JSON
- Headers: `web/_headers` — added short-cache + SWR rule for `/scoreboard.json` matching the existing pattern for data/picks JSON

### v1.5.23 — 2026-04-17
- Statistical: add split-pot avoidance prior to EWMA scoring. Multiplicatively down-weights numbers 1–31 (dates) by 0.90 and "lucky" 7/11 by 0.85. Does not change win probability — Powerball is random — but raises expected payout ~10–30% per win by reducing pot-split dilution. 13 and 32–35 unchanged (underpicked in practice). Applied in `scripts/generate_picks.py` (`compute_ewma_scores`) and `web/app.js` (`computeEwmaWeights`), so both the Thursday email and the "Hot Numbers" / "Balanced Draw" picker strategies inherit the bias. "Cold" and "True Random" strategies unaffected. Dashboard hot-ball display uses raw counts and remains an honest record of observed history.

### v1.5.22 — 2026-04-17
- Performance: add explicit `Cache-Control` rules in `_headers` (short + SWR for JSON data, long for static assets) — fewer revalidation round-trips
- Performance: `preconnect` + `dns-prefetch` to jsdelivr CDN — ~100–200ms faster first chart render on cold networks
- Performance: convert `og-image.png` (109KB) → `og-image.webp` (24KB) — 77% size reduction; PNG preserved on disk as fallback
- Security: add `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Resource-Policy: same-origin` headers (defence-in-depth)
- Reliability: `app.js` — add `fetchWithRetry()` (2 attempts, 500ms backoff) around draws and VERSION fetches; matches the retry discipline already present in `scrape.py`
- Reliability: `app.js` — add global error handlers (`error` + `unhandledrejection`) so uncaught exceptions surface to console instead of failing silently
- Reliability: `scrape.py` — reject out-of-range or duplicate balls before append (main 1–35, PB 1–20) — data-integrity safety net for the append-only draws file
- Reliability: both workflows — add `timeout-minutes: 10`, shared `concurrency` group (`cancel-in-progress: false`), and `set -euo pipefail` on all multi-line shell steps — prevents hung runners and silent cascading failures
- Reliability: workflow commit steps now use explicit `if/else` around the no-staged-changes branch so intent is auditable in logs

### v1.5.21 — 2026-04-09
- powerball-update.yml: auto-update sitemap.xml lastmod on every successful data scrape
- index.html: add FAQPage schema.org JSON-LD (5 Q&As) for Google rich results eligibility

### v1.5.20 — 2026-04-09
- app.js: replace all innerHTML on JSON-sourced data with safe DOM construction (textContent); add JSON structure validation after fetch
- scrape.py: add 3-attempt exponential backoff retry (2s/4s/8s) on network errors

### v1.5.19 — 2026-04-09
- CSP: add explicit `object-src 'none'`; HSTS: add `preload` directive
- generate_picks.py + scrape.py: guard against empty data file with early exit and clear error message
- Chart.js script tag: add `async` to remove render-blocking on initial page load

### v1.5.18 — 2026-04-09
- Security/reliability hardening: pin scipy upper bound (<2.0), fix latent HTTPError variable scope bug in email_picks.py, add theme-color meta tag, noscript fallback, aria-label on history search input, update sitemap lastmod

### v1.5.17 — 2026-04-02
- Add Powerball diversity: pre-sample 18 distinct PBs without replacement (EWMA-weighted) across all 18 games, covering 90% of the PB pool every week vs old formula's fixed 5 PBs (25% coverage)

### v1.5.16 — 2026-04-02
- Upgrade statistical formula: replace raw frequency counting with EWMA scoring (α=0.03, half-life ≈23 draws/6 months) in both `generate_picks.py` and `app.js`
- Upgrade game generation: two-phase greedy portfolio coverage — games 1–5 guarantee all 35 main balls appear in every weekly batch; games 6–18 use EWMA-weighted sampling with pair-diversity rejection
- Add chi-squared goodness-of-fit test: dashboard now shows whether ball frequency distribution significantly deviates from uniform (p-value displayed inline)
- Improve mixed-mode picker: sum bounds now use data-adaptive empirical 5th/95th percentiles instead of hardcoded constants; add consecutive-pair constraint (covers 98.1% of historical draws)

### v1.5.15 — 2026-03-20
- Fix: change `[skip ci]` to `[skip actions]` in workflow commit messages so Cloudflare Pages deploys auto-commits (draw data + picks history)

### v1.5.14 — 2026-03-15
- Fix: increase CSS specificity of `.hist-pb-col { display: none }` so it correctly overrides the more specific `.table-wrap tbody td { display: block }` rule on mobile — removes duplicate powerball in history rows

### v1.5.13 — 2026-03-15
- Fix: nav tabs wrapped in `.nav-tabs` sub-div so donate button is always visible on mobile (not scrolled off-screen)
- Fix: CSS mask-gradient fade on nav right edge hints there are more tabs on mobile
- Fix: `.ball-pair` wrapper keeps each ball+frequency count together in flex-wrap layouts
- Fix: history table converts to flex card layout on mobile; PB shown inline with main balls

### v1.5.12 — 2026-03-15
- Feature: Ko-fi donation button added to sticky nav bar (right-aligned on desktop, hidden on mobile <480px)

### v1.5.11 — 2026-03-15
- Fix: wrap ball numbers in no-href `<a>` tags — prevents Apple Mail iOS from auto-linking numbers as phone numbers
- Fix: add 16px left padding to Powerball column for visual separation from main balls

### v1.5.10 — 2026-03-15
- Fix: add `x-apple-data-detectors="false"` to ball `<td>` elements — stops Apple Mail iOS treating numbers as phone links
- Fix: center games table via `align="center"` on wrapper cell and `margin:0 auto` on inner table

### v1.5.9 — 2026-03-15
- Fix: remove `width="100%"` from inner games table — Powerball column no longer pushed to far right; table now sizes to ball content
- Fix: add `<meta name="format-detection">` — suppresses Apple Mail iOS auto-linking ball numbers as phone numbers (was causing blue underlined text)

### v1.5.8 — 2026-03-15
- Fix: email now renders correctly on mobile (Apple Mail iOS, Yahoo Mail iOS)
- Added `<meta name="viewport">` to HTML email template (was missing)
- Added `<style>` block with `@media (max-width:600px)` — shrinks balls to 28px, reduces padding
- Changed container from fixed `width="600"` to `max-width:600px; width:100%` so email scales to viewport
- Added CSS classes (`ball`, `game-label`, `game-row`) alongside inline styles for media query targeting

### v1.5.7 — 2026-03-15
- Legal: replaced footer helpline with a full disclaimer panel (entertainment only, not legal/financial/gambling advice, gamble responsibly, helpline) added to all five tabs — Dashboard, Frequency, Trends, Picker, History

### v1.5.6 — 2026-03-15
- Legal: added gambling helpline link (gamblinghelponline.org.au + 1800 858 858) to the site footer — now visible on every tab, not just the Picker tab

### v1.5.5 — 2026-03-15
- Fix: `email-picks.yml` now commits `web/picks/picks_history.json` after each run — picks history was being generated but discarded; the History tab now updates weekly
- Fix: removed stale root `data/` directory (was one draw behind and unused by any script; scripts already read/write `web/data/powerball_draws.json` directly)
- Docs: corrected CLAUDE.md and README project structure to remove misleading dual-directory references

### v1.5.4 — 2026-03-15
- SEO: added `<lastmod>` to sitemap.xml; added `og:image:alt` and `og:image:type` meta tags; expanded meta description to ~160 chars; added `<link rel="preload">` for draw data JSON
- Security: removed deprecated `X-XSS-Protection` header; added `fullscreen=()` to `Permissions-Policy`
- Reliability: loading indicator shown while draw data fetches; removed unused `PICKS_URL` constant and dead `renderSingleGame` function
- Performance: Frequency and Trends charts now render lazily on first tab activation instead of at page load
- Repo: fixed stale SendGrid reference in README project tree; expanded `.gitignore`; removed stray `au_powerball_analyzer.jsx` from repo root

### v1.5.3 — 2026-03-14
- Added `og:image` (1200×630 branded preview) and `twitter:image` tags for iMessage / social link previews
- Upgraded Twitter card type to `summary_large_image`

### v1.5.2 — 2026-03-14
- Reverted email layout to previous light theme (white body, dark header)
- Replaced rainbow main ball colours with uniform indigo `#6366f1` (matches website `.ball-sm.main`)
- Replaced old powerball colour with `#a855f7` (matches website `.ball-sm.pb`)

### v1.5.1 — 2026-03-14
- Email redesigned to match website dark theme exactly: `#0f1117` background, `#1a1d27`/`#22263a` cards, `#2d3148` borders
- Main balls now use indigo gradient (`#6366f1→#4f46e5`) matching `.ball-sm.main` CSS
- Powerball now uses purple gradient (`#a855f7→#7e22ce`) matching `.ball-sm.pb` CSS
- Removed rainbow ball colours; replaced with consistent single-colour scheme
- Alternating row shading for readability across 18 games

### v1.5.0 — 2026-03-14
- Switched email provider from SendGrid (60-day trial) to Brevo (free forever, 300/day)
- Rewrote `email_picks.py` to use Brevo REST API via `requests` — no new SDK dependency
- Removed `sendgrid` from `requirements.txt`
- Added new `email-picks.yml` GitHub Actions workflow — runs Thursday 00:00 UTC (10am AEST), generates fresh picks and sends email
- Updated README setup instructions to reflect Brevo secrets (`BREVO_API_KEY`)

### v1.4.2 — 2026-03-14
- Schedule changed from Friday midnight UTC to Friday 4am AEST (Thursday 18:00 UTC)
- Workflow now calls `scrape.py` directly — email is a separate, not-yet-configured workflow
- Upgraded GitHub Actions to Node.js 24: `actions/checkout@v5`, `actions/setup-python@v6`

### v1.4.1 — 2026-03-12
- Number Picker: Hot strategy replaced with recency-weighted sampling across all 35 balls (linear weight: newest draw = 2×, oldest = 1×, all balls eligible)
- Number Picker: Mix Strategy replaced with Balanced Draw — rejection sampling against hypergeometric distribution constraints (sum in [87,165], 2–5 odd, 2–5 low)
- Number Picker: Cold strategy now uses cold Powerballs pool for PB selection
- Strategy card and explainer text updated to reflect new algorithms

### v1.4.0 — 2026-03-12
- Scraped complete historical dataset: draw #1 (1996-05-23) through #1555 (2026-03-05) — 1,555 draws total
- Added `scripts/scrape_historical.py` — one-time year-archive backfill script (23 HTTP requests for 28 years)
- Multi-era awareness: frequency analysis, trends, hot/cold picks, and number picker all filter to current-format draws only (7-ball, 1–35, 2018–present)
- Dashboard "Historical Draws" stat shows full 1,555-draw count; all analysis panels clarify they use 412 current-format draws
- Updated History tab to display all 1,555 draws

### v1.3.1 — 2026-03-12
- SEO: Open Graph, Twitter Card, canonical URL, robots meta, Schema.org JSON-LD structured data
- SEO: Page header promoted to `<h1>`; sitemap.xml and robots.txt added
- Security: Cloudflare Pages `_headers` file — CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, HSTS
- Security: SRI + crossorigin added to Chart.js CDN script tag
- Security: `rel="noopener noreferrer"` on all external links; inline styles in app.js replaced with CSS classes to enable strict CSP

### v1.3.0 — 2026-03-12
- Number Picker: complete game card redesign — vertical card layout with header, main balls section, and visually separated powerball row
- Replaced flat single-row layout with 3-column CSS Grid of cards for better readability at 18 games

### v1.2.5 — 2026-03-11
- Fix powerball clipped on game cards (remove overflow:hidden, widen card min-width to 370px)

### v1.2.4 — 2026-03-11
- Game cards: all balls on a single row (no wrapping), smaller ball size for compact layout

### v1.2.3 — 2026-03-11
- Number Picker: no results shown on load — results only appear after clicking Generate

### v1.2.2 — 2026-03-11
- Fix spacing between game count toggle and generate button

### v1.2.1 — 2026-03-11
- Number Picker: added 1-game / 18-games toggle below strategy selector

### v1.2.0 — 2026-03-11
- Number Picker redesigned to match JSX reference: dark strategy cards with explicit hex colors, full-width purple→pink gradient generate button
- Fixed strategy card white/unstyled rendering on iOS Safari (replaced `appearance: none` with `all: unset` + explicit hex values)
- Removed 1-game/18-game quantity toggle — picker always generates 18 games
- Updated strategy card descriptions to shorter, text-left layout
- Updated explainer section to paragraph format with colored labels

### v1.1.0 — 2026-03-11
- Number Picker redesign: strategy selector (Hot/Cold/Mix/Random), 1 or 18 game toggle
- Fixed strategy card and button styling (appearance: none reset for all browsers)
- Fixed "How Each Strategy Works" emoji inline alignment
- Header upgrade: deep indigo-to-purple gradient background, amber-orange-pink gradient title text, "Australia" eyebrow label

### v1.0.0 — 2026-03-11
- Initial release
- 412 draws (Apr 2018 – Mar 2026)
- Static web app: Dashboard, Frequency, Trends, Picker, History tabs
- Python pipeline: scrape → generate → email via SendGrid
- GitHub Actions: Friday midnight UTC cron, 3-week gap check
- Deployed on Cloudflare Pages

---

*Built with [Claude Code](https://claude.ai/code) · For entertainment only · Gamble responsibly*
