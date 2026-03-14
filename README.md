# 🎱 Thursday Numbers

> **Every Thursday, smarter numbers.**

Statistical analysis of Australian Powerball historical draw data. Generates 18 hot-number game picks and emails them weekly via SendGrid — all driven by a free GitHub Actions workflow.

🌐 **Live site:** [thursdaynumbers.com](https://thursdaynumbers.com) — hosted on Cloudflare Pages

**Current version: v1.4.2**

---

## What it does

| Feature | Detail |
|---|---|
| 📊 Web dashboard | Frequency charts, hot/cold numbers, recent trends, full draw history |
| 🎯 Number picker | 18 hot-number games per run (7 main + 1 Powerball each) |
| 🤖 Auto-update | GitHub Actions runs every Friday at 4am AEST; full pipeline runs every week |
| 📧 Email delivery | HTML email via SendGrid with all 18 games beautifully formatted |
| 📂 Data | 1,555 draws from May 1996 onward (complete history); analysis uses current-format draws (2018–present) |

---

## How the number generation works

1. **Frequency analysis** — counts how often each ball (main: 1–35, PB: 1–20) has appeared across all recorded draws.
2. **Hot pool** — picks the top 10 most-drawn main balls and top 5 Powerballs.
3. **Game generation** — randomly samples 7 unique balls from the hot main pool + 1 from the hot PB pool, 18 times with no duplicate games.

> ⚠️ **Important disclaimer:** Powerball is a game of pure chance. Each draw is completely independent. Past frequencies have **zero** influence on future draws. This tool is for entertainment only. If gambling is causing you problems, contact [Gambling Help Online](https://www.gamblinghelponline.org.au) or call **1800 858 858**.

---

## Project structure

```
thursday-numbers/
├── data/
│   └── powerball_draws.json          ← Draw history used by Python scripts
├── picks/
│   └── picks_history.json            ← Pick log written by Python scripts
├── scripts/
│   ├── scrape.py                     ← Fetch new draws from the web
│   ├── generate_picks.py             ← Generate 18 hot-number games
│   ├── email_picks.py                ← Send picks via SendGrid
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
│   └── powerball-update.yml          ← GitHub Actions (Friday 4am AEST)
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

### 2. Get a SendGrid API key (free)

1. Sign up at [sendgrid.com](https://sendgrid.com) — free tier = 100 emails/day
2. **Settings → API Keys → Create API Key → Restricted Access → Mail Send only**
3. Copy the key (shown once)
4. **Settings → Sender Authentication** — verify your sender email

### 3. Add GitHub Secrets

**Repo → Settings → Secrets and variables → Actions → New repository secret**

| Secret name | Value |
|---|---|
| `SENDGRID_API_KEY` | Your SendGrid API key |
| `EMAIL_RECIPIENT` | Email address to receive picks |
| `EMAIL_SENDER` | Verified SendGrid sender email |

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

GitHub Actions runs **every Friday at 4am AEST** (Thursday 18:00 UTC), after Thursday evening's Australian Powerball draw has been published.

The workflow:
- Scrapes any new draws
- Generates 18 games → sends email → commits updated JSON files
- Cloudflare Pages auto-deploys on the next push

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
- **No secrets in repo** — SendGrid API key and email addresses are GitHub Secrets only; `web/` contains zero credentials

---

## Tech stack

| Layer | Choice | Reason |
|---|---|---|
| Hosting | Cloudflare Pages | Domain on Cloudflare; auto-deploys on push; no extra DNS setup |
| Frontend | Vanilla HTML/CSS/JS + Chart.js (CDN) | No build step — static files only |
| Scraping | Python + requests + BeautifulSoup | Simple, reliable |
| Email | SendGrid Python SDK | API key is send-only; safe for public repos |
| Automation | GitHub Actions cron | Free, serverless |
| Data | JSON files in repo | Simple, version-controlled |

---

## Changelog

### v1.4.2 — 2026-03-14
- Schedule changed from Friday midnight UTC to Friday 4am AEST (Thursday 18:00 UTC)
- Removed 3-week email gap check — pipeline now runs and sends email every week

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
