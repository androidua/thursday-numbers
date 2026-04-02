# 🎱 Thursday Numbers

> **Every Thursday, smarter numbers.**

Statistical analysis of Australian Powerball historical draw data. Generates 18 hot-number game picks and emails them weekly via Brevo — all driven by a free GitHub Actions workflow.

🌐 **Live site:** [thursdaynumbers.com](https://thursdaynumbers.com) — hosted on Cloudflare Pages

**Current version: v1.5.17**

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
