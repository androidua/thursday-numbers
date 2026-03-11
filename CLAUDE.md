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

**v1.3.1** — see `web/VERSION` file.

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

GitHub Actions (`powerball-update.yml`) runs **every Friday at midnight UTC**
= Friday 10am AEST / 11am AEDT.

**Why Friday?** Australian Powerball draws happen Thursday evening. Running Friday
morning ensures new results are always available before scraping.

The workflow:
1. Scrapes any new draws since last recorded
2. Checks if 3+ weeks have passed since last email was sent
3. If yes: generates 18 hot-number games → sends email → commits updated JSON
4. Cloudflare Pages auto-deploys the updated data on the next push

---

## Project Structure

```
thursday-numbers/
├── CLAUDE.md                              ← this file
├── README.md                              ← public-facing project description
├── requirements.txt                       ← Python dependencies
├── .github/
│   └── workflows/
│       └── powerball-update.yml           ← GitHub Actions (Friday midnight UTC)
├── data/
│   └── powerball_draws.json               ← scraped draw history (source of truth for scripts)
├── scripts/
│   ├── scrape.py                          ← fetches new draws since last known draw
│   ├── generate_picks.py                  ← generates 18 hot-number games
│   ├── email_picks.py                     ← sends picks via SendGrid
│   └── run_all.py                         ← entry point: scrape → generate → email
├── picks/
│   └── picks_history.json                 ← running log of all generated picks (scripts write here)
└── web/                                   ← served by Cloudflare Pages
    ├── VERSION                            ← current version number (read by app.js)
    ├── index.html                         ← static site
    ├── app.js                             ← vanilla JS analyser (loads data via fetch)
    ├── style.css                          ← dark-themed styles
    ├── data/
    │   └── powerball_draws.json           ← copy of draw data served to the web app
    └── picks/
        └── picks_history.json             ← copy of picks served to the web app
```

**Dual data directories explained:**
- `data/` and `picks/` at the repo root are used by the Python scripts
- `web/data/` and `web/picks/` are what the browser fetches via `fetch()`
- The GitHub Actions workflow commits the `web/` copies after each run

---

## What Has Been Built (v1.2.0)

### Data
- **412 draws** scraped from `australia.national-lottery.com`
- Draw range: **#1144 (2018-04-19) → #1555 (2026-03-05)**
- Stored in `data/powerball_draws.json`
- Format: `{"draw": 1144, "date": "2018-04-19", "main": [4,5,9,13,25,32,33], "powerball": 7}`
- The source site only holds draws from ~2018 onward

### Python Scripts
- `scrape.py` — finds missing Thursdays, fetches each from australia.national-lottery.com
- `generate_picks.py` — frequency analysis, top-10 hot main + top-5 hot PBs, 18 unique games
- `email_picks.py` — HTML email via SendGrid with coloured ball layout
- `run_all.py` — full pipeline with `--dry-run` and `--force` flags, 3-week gap check

### Web App
- Dark-themed single-page app: Dashboard, Frequency, Recent Trends, Number Picker, History
- Chart.js from CDN — no build step
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
- Env vars: `SENDGRID_API_KEY`, `EMAIL_RECIPIENT`, `EMAIL_SENDER`

### `scripts/run_all.py`
- `--dry-run`: skip email send and data file writes
- `--force`: bypass the 3-week gap check
- Exits with code 1 on failure (GitHub Actions marks run as failed)

---

## Environment Variables / GitHub Secrets

| Secret Name | Description |
|---|---|
| `SENDGRID_API_KEY` | SendGrid API key with Mail Send permission |
| `EMAIL_RECIPIENT` | Email address to receive picks |
| `EMAIL_SENDER` | Verified sender email in SendGrid |

Repo → Settings → Secrets and variables → Actions → New repository secret

---

## Current Data Stats

- **Total draws:** 412
- **Range:** Draw #1144 (2018-04-19) → Draw #1555 (2026-03-05)
- **Hot main balls:** 9, 7, 17, 11, 19, 18, 23, 14, 12, 30
- **Cold main balls:** 31, 13, 26, 29, 8, 33, 35, 15, 34, 5
- **Hot Powerballs:** 2, 4, 6, 10, 3

---

## Key Technical Decisions

| Decision | Choice | Reason |
|---|---|---|
| Hosting | Cloudflare Pages | Domain is on Cloudflare; auto-deploys on push; no A record setup needed |
| Email | SendGrid | API key is send-only; safe for public repos |
| Scheduling | GitHub Actions cron (Friday midnight UTC) | Runs after Thursday evening draws; free, serverless |
| 3-week gap | Checked in `run_all.py` | cron can't do "every N weeks"; script skips if not enough time has passed |
| Number strategy | Hot numbers for all 18 games | User preference |
| Games per run | 18 | User buys 18 standard games per draw |
| Web framework | Vanilla JS + Chart.js CDN | No build step; Cloudflare Pages serves static files directly |
| Data storage | JSON files in repo | Simple, version-controlled, human-readable diffs |
| Branch strategy | Push directly to `main` | Solo project; no branching needed |

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
