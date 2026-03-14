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

**v1.5.5** — see `web/VERSION` file.

---

## Versioning Rules

Use semantic versioning: `MAJOR.MINOR.PATCH`

| Digit | When to increment | Examples |
|---|---|---|
| MAJOR (1st) | Major redesign or large new feature set | Full UI overhaul, new analysis engine |
| MINOR (2nd) | New features or meaningful improvements | New chart, new tab, new script capability |
| PATCH (3rd) | Small fixes, typos, config tweaks | Bug fix, copy update, cron change |

**Rules:**
- Update `web/VERSION`, `README.md`, and `CLAUDE.md` whenever you make changes
- Display the version in the web app footer (loaded at runtime from `web/VERSION`)
- Mention the version in every commit message and README changelog
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
1. Runs `scripts/generate_picks.py` — generates 18 fresh hot-number games
2. Runs `scripts/email_picks.py` — sends HTML email via Brevo
3. Commits `web/picks/picks_history.json` if updated — powers the web app's History tab

**`powerball-update.yml`** — Thursday 18:00 UTC (= Friday 4am AEST / 5am AEDT):
1. Runs `scripts/scrape.py` — fetches any new draws since last recorded
2. Commits `web/data/powerball_draws.json` if new draws were found
3. Cloudflare Pages auto-deploys on every push to `main`

**Why the two-workflow split?** Email sends *before* the draw (10am) using prior data. Scrape runs *after* the draw (4am next day) to capture results. These are deliberately separate cron jobs.

**Actions versions (Node.js 24):** `actions/checkout@v5`, `actions/setup-python@v6`

---

## Project Structure

```
thursday-numbers/
├── CLAUDE.md                              ← this file
├── README.md                              ← public-facing project description
├── requirements.txt                       ← Python dependencies
├── .github/
│   └── workflows/
│       ├── powerball-update.yml           ← GitHub Actions scrape (Thursday 18:00 UTC = Friday 4am AEST)
│       └── email-picks.yml               ← GitHub Actions email (Thursday 00:00 UTC = 10am AEST)
├── scripts/
│   ├── scrape.py                          ← fetches new draws since last known draw
│   ├── scrape_historical.py               ← one-time backfill: year-archive pages 1996–2018
│   ├── generate_picks.py                  ← generates 18 hot-number games
│   ├── email_picks.py                     ← sends picks via Brevo REST API
│   └── run_all.py                         ← entry point: scrape → generate → email
└── web/                                   ← served by Cloudflare Pages
    ├── VERSION                            ← current version number (read by app.js)
    ├── index.html                         ← static site
    ├── app.js                             ← vanilla JS analyser (loads data via fetch)
    ├── style.css                          ← dark-themed styles
    ├── _headers                           ← Cloudflare Pages HTTP security headers (CSP, HSTS, etc.)
    ├── robots.txt                         ← crawler policy + sitemap reference
    ├── sitemap.xml                        ← XML sitemap for search engine indexing
    ├── data/
    │   └── powerball_draws.json           ← draw history; read/written by scripts; served to web app
    └── picks/
        └── picks_history.json             ← generated picks log; written by scripts; served to web app
```

**Single source of truth:** all scripts read from and write to `web/data/` and `web/picks/` directly. There is no separate root-level `data/` or `picks/` directory.

---

## What Has Been Built (v1.5.5)

### Data
- **1,556 draws** scraped from `australia.national-lottery.com` (complete history)
- Full range: **#1 (1996-05-23) → #1556 (2026-03-12)**
- Current-format draws used for analysis: **413** (#1144 2018-04-19 → #1556 2026-03-12)
- Stored in `web/data/powerball_draws.json` (single location — no root-level copy)
- Format: `{"draw": 1144, "date": "2018-04-19", "main": [4,5,9,13,25,32,33], "powerball": 7}`
- Pre-2018 draws have fewer main balls (5 or 6); `app.js` filters to `main.length === 7` for all analysis

### Python Scripts
- `scrape.py` — finds missing Thursdays, fetches each from australia.national-lottery.com
- `scrape_historical.py` — one-time backfill via year-archive pages; supports `--dry-run` and `--start-year`
- `generate_picks.py` — frequency analysis, top-10 hot main + top-5 hot PBs, 18 unique games
- `email_picks.py` — HTML email via Brevo REST API with coloured ball layout (indigo main, purple PB)
- `run_all.py` — full pipeline with `--dry-run` and `--force` flags, 3-week gap check

### Web App
- Dark-themed single-page app: Dashboard, Frequency, Recent Trends, Number Picker, History
- Number Picker supports 1-game or 18-game generation with 4 strategies (hot/cold/mixed/random)
- Game results displayed as card grid (3-col desktop, 2-col tablet, 1-col mobile)
- Chart.js from CDN with SRI integrity check — no build step
- Loads `data/powerball_draws.json` and `picks/picks_history.json` via `fetch()` (paths relative to `web/`)
- Version displayed in footer (read at runtime from `web/VERSION`)

---

## Script Details

### `scripts/scrape.py`
- URL pattern: `https://australia.national-lottery.com/powerball/results/DD-MM-YYYY`
- Main balls: `<li class="ball medium pb ball">N</li>`
- Powerball: `<li class="ball medium pb powerball">N</li>`
- `time.sleep(0.5)` between requests; User-Agent: `Mozilla/5.0`

### `scripts/generate_picks.py`
Output format per run:
```json
{
  "generated_at": "2026-03-05T10:00:00",
  "draws_analysed": 412,
  "data_range": "2018-04-19 to 2026-03-05",
  "hot_main_balls": [9, 7, 17, 11, 19, 18, 23, 14, 12, 30],
  "hot_powerballs": [2, 4, 6, 10, 3],
  "games": [
    {"game": 1, "main": [7, 9, 11, 17, 18, 19, 23], "powerball": 2}
  ]
}
```

### `scripts/email_picks.py`
- Subject: `🎱 Your Powerball Picks — Draw Week of [date]`
- HTML email with coloured ball table + plain text fallback
- Env vars: `BREVO_API_KEY`, `EMAIL_RECIPIENT`, `EMAIL_SENDER`

### `scripts/run_all.py`
- `--dry-run`: skip email send and data file writes
- `--force`: bypass the 3-week gap check
- Exits with code 1 on failure (GitHub Actions marks run as failed)

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

- **Total draws (all eras):** 1,555
- **Full range:** Draw #1 (1996-05-23) → Draw #1555 (2026-03-05)
- **Current-format draws (used for analysis):** 412 (Draw #1144, 2018-04-19 → Draw #1555, 2026-03-05)
- **Format eras:** 5-ball 1–45 (1996–2013, ~876 draws), 6-ball 1–40 (2013–2018, ~267 draws), 7-ball 1–35 + PB 1–20 (2018–present, 412 draws)
- **Hot main balls (current format):** 9, 7, 17, 11, 19, 18, 23, 14, 12, 30
- **Cold main balls (current format):** 31, 13, 26, 29, 8, 33, 35, 15, 34, 5
- **Hot Powerballs (current format):** 2, 4, 6, 10, 3

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
| Content-Security-Policy | `web/_headers` | `default-src 'none'`; allows only local scripts/styles, jsDelivr CDN, same-origin fetch |
| X-Frame-Options | `web/_headers` | `DENY` — prevents all iframe embedding (clickjacking) |
| X-Content-Type-Options | `web/_headers` | `nosniff` — prevents MIME-type confusion attacks |
| Referrer-Policy | `web/_headers` + `index.html` | `strict-origin-when-cross-origin` |
| Permissions-Policy | `web/_headers` | Blocks camera, mic, geolocation, payment, USB, FLoC |
| HSTS | `web/_headers` | `max-age=31536000; includeSubDomains` (supplementary to Cloudflare's own HSTS) |
| X-XSS-Protection | `web/_headers` | Legacy browser fallback |
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
| 3-week gap | Checked in `run_all.py` | cron can't do "every N weeks"; script skips if not enough time has passed |
| Number strategy | Hot numbers for all 18 games | User preference |
| Games per run | 18 | User buys 18 standard games per draw |
| Web framework | Vanilla JS + Chart.js CDN | No build step; Cloudflare Pages serves static files directly |
| Data storage | JSON files in repo | Simple, version-controlled, human-readable diffs |
| Branch strategy | Push directly to `main` | Solo project; no branching needed |
| Security headers | `web/_headers` file | Cloudflare Pages native approach — zero infrastructure, applied at edge |
| No inline styles in JS | CSS classes only | Keeps CSP clean (`style-src 'self'` with no `unsafe-inline`) |

---

## Important Disclaimers

> Powerball is a game of pure chance. Each draw is independent and random.
> Past results have zero statistical influence on future draws.
> This tool is for entertainment only. Please gamble responsibly.
> For help with gambling: gamblinghelponline.org.au or call 1800 858 858.

---

## Notes for Claude Code

- Always read this file first before starting any task
- **Always update `VERSION`, `CLAUDE.md`, and `README.md` when making changes**
- **Always push directly to `main`** — no branches
- The `data/powerball_draws.json` file is the single source of truth — never overwrite, only append
- All scripts should be runnable standalone: `python scripts/scrape.py`
- Use `argparse` for CLI flags; `json.dumps(..., indent=2)` for all JSON writes
- Write clear `print()` statements so GitHub Actions logs are readable
- The web app needs an HTTP server to run locally (uses `fetch()` for JSON)
- **Never add inline `style="..."` attributes to JS-generated HTML** — use CSS classes to preserve the strict CSP
- **If upgrading Chart.js**, recompute the SRI hash (see SRI maintenance rule above) and update `integrity` in `index.html`
- The `web/_headers` file controls all HTTP security headers — edit there, not in `index.html` meta tags (meta tags are a fallback only)
