# 🎱 Thursday Numbers Analyser — Claude Code Project

## Project Summary

This is a full-stack web tool and automated pipeline for analysing Australian Powerball
historical draw data, generating statistically-informed number picks, and emailing results
on a scheduled basis via GitHub Actions.

Tagline: *"Every Thursday, smarter numbers."*

The end goal is a **public GitHub repository** containing:
1. A hosted static web page (GitHub Pages) with an interactive Powerball analyser
2. A Python automation script that scrapes new draws, generates 18 games of hot numbers,
   saves results to a JSON file, and emails them via SendGrid
3. A GitHub Actions workflow that runs the script automatically every 3 weeks

---

## What Has Already Been Done (in Claude.ai)

### Data
- Scraped **412 consecutive weekly draws** from `australia.national-lottery.com`
- Draw range: **#1144 (2018-04-19) → #1555 (2026-03-05)**
- Stored in `data/powerball_draws.json`
- Format per entry: `{"draw": 1144, "date": "2018-04-19", "main": [4,5,9,13,25,32,33], "powerball": 7}`
- The site only holds draws from ~2018 onward; earlier data is unavailable online

### Web App (React artifact — needs converting to static site)
- A React component was built in Claude.ai as a prototype (`src/ThursdayNumbers.jsx`)
- It contains all 412 draws hardcoded as a JS constant
- Tabs: Dashboard, Frequency charts, Recent Trends, Number Picker, History
- Uses: `recharts` for charts, Tailwind CSS for styling
- **This needs to be converted** into a proper static GitHub Pages site (see Task 2 below)

### Analysis Logic (already proven, needs to be extracted to Python)
- "Hot numbers" = top 10 most frequently drawn main balls across all draws
- "Cold numbers" = bottom 10 least frequently drawn
- Number picker generates 7 unique main balls + 1 Powerball per game
- Hot strategy: pool from top 10 main balls + top 5 Powerballs
- 18 games are generated per run (18 standard Powerball games)

---

## Project Structure to Build

```
thursday-numbers/
├── CLAUDE.md                          ← this file
├── README.md                          ← public-facing project description
├── .github/
│   └── workflows/
│       └── powerball-update.yml       ← GitHub Actions schedule (every 3 weeks)
├── data/
│   └── powerball_draws.json           ← scraped draw history (412 draws, grows over time)
├── scripts/
│   ├── scrape.py                      ← fetches new draws since last known draw
│   ├── generate_picks.py              ← generates 18 hot-number games
│   ├── email_picks.py                 ← sends picks via SendGrid
│   └── run_all.py                     ← entry point: scrape → generate → email → save
├── picks/
│   └── picks_history.json             ← running log of all generated picks over time
├── web/
│   ├── index.html                     ← static GitHub Pages site
│   ├── app.js                         ← vanilla JS version of the React analyser
│   └── style.css                      ← styles
└── requirements.txt                   ← Python dependencies
```

---

## Task List (in priority order)

### Task 1 — Python Scripts

#### `scripts/scrape.py`
- Load `data/powerball_draws.json` to find the last known draw number and date
- Calculate the Thursday dates between then and today
- Fetch each missing draw from `australia.national-lottery.com/powerball/results/DD-MM-YYYY`
- Parse: 7 main balls + 1 Powerball from `<li class="ball ...">` elements
- Append new draws to `data/powerball_draws.json`
- Print a summary of how many new draws were added

**Scraping details:**
- URL pattern: `https://australia.national-lottery.com/powerball/results/DD-MM-YYYY`
- Australian Powerball draws every **Thursday**
- Parse with `requests` + `BeautifulSoup`
- Main balls: `<li class="ball medium pb ball">N</li>`
- Powerball: `<li class="ball medium pb powerball">N</li>`
- Add `time.sleep(0.5)` between requests to be polite
- User-Agent header: `Mozilla/5.0`

#### `scripts/generate_picks.py`
- Load `data/powerball_draws.json`
- Count frequency of each main ball (1–35) and each Powerball (1–20)
- Identify top 10 hot main balls and top 5 hot Powerballs
- Generate **18 complete games**, each with:
  - 7 unique main balls drawn randomly from the hot pool (no repeats within a game)
  - 1 Powerball drawn randomly from the hot Powerball pool
  - No duplicate games (all 18 must be unique combinations)
- Return a structured result dict including metadata and all 18 games
- Save result to `picks/picks_history.json` (append, don't overwrite)

**Output format per run:**
```json
{
  "generated_at": "2026-03-05T10:00:00",
  "draws_analysed": 412,
  "data_range": "2018-04-19 to 2026-03-05",
  "hot_main_balls": [9, 7, 17, 11, 19, 18, 23, 14, 12, 30],
  "hot_powerballs": [2, 4, 6, 10, 3],
  "games": [
    {"game": 1, "main": [7, 9, 11, 17, 18, 19, 23], "powerball": 2},
    ...18 total...
  ]
}
```

#### `scripts/email_picks.py`
- Use **SendGrid Python SDK** (`sendgrid` package)
- Read SendGrid API key from environment variable: `SENDGRID_API_KEY`
- Read recipient email from environment variable: `EMAIL_RECIPIENT`
- Read sender email from environment variable: `EMAIL_SENDER`
- Generate a clean HTML email (see email format below)
- Send and log success/failure

**Email format:**
- Subject: `🎱 Your Powerball Picks — Draw Week of [date]`
- HTML body with a clean table showing all 18 games
- Each row: Game #, 7 coloured number balls, Powerball in purple
- Footer with disclaimer: "Generated from statistical analysis of X draws. Does not predict outcomes."
- Plain text fallback version included

#### `scripts/run_all.py`
- Entry point that runs: scrape → generate picks → email → log
- Accepts optional `--dry-run` flag (skip email, just print picks to console)
- Prints clear status messages at each step
- Exits with code 1 on any failure so GitHub Actions marks the run as failed

---

### Task 2 — Static Web Page (GitHub Pages)

Convert the React prototype into a **vanilla HTML/CSS/JS static page** so it works on
GitHub Pages without a build step.

- Single `web/index.html` file with embedded or linked JS/CSS
- Load draw data from `../data/powerball_draws.json` via `fetch()`
- Charts: use **Chart.js** (CDN) instead of recharts
- Same tabs as the React version: Dashboard, Frequency, Recent, Picker, History
- The Number Picker tab should show the same 18 hot games that were last generated
  (load from `picks/picks_history.json`, show the most recent run)
- Mobile responsive
- Host on GitHub Pages from the `web/` folder or root
- Custom domain: `thursdaynumbers.com` (registered on Cloudflare)
- A `CNAME` file must exist inside the `web/` folder containing just: `thursdaynumbers.com`

---

### Task 3 — GitHub Actions Workflow

File: `.github/workflows/powerball-update.yml`

```yaml
name: Powerball Auto-Update

on:
  schedule:
    - cron: '0 10 * * 4'   # Every Thursday at 10am UTC (8pm AEST)
                              # GitHub Actions doesn't support "every 3 weeks" natively
                              # so the script itself checks if 3 weeks have passed since last run
  workflow_dispatch:          # Allow manual trigger from GitHub UI

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python scripts/run_all.py
        env:
          SENDGRID_API_KEY: ${{ secrets.SENDGRID_API_KEY }}
          EMAIL_RECIPIENT: ${{ secrets.EMAIL_RECIPIENT }}
          EMAIL_SENDER: ${{ secrets.EMAIL_SENDER }}
      - name: Commit updated data
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/powerball_draws.json picks/picks_history.json
          git diff --staged --quiet || git commit -m "auto: update draws and picks [skip ci]"
          git push
```

**Important note on scheduling:**
GitHub Actions `cron` doesn't support "every N weeks" directly. Two options:
1. Run every Thursday, but inside `run_all.py` check if it's been 3+ weeks since last run — skip if not
2. Use a specific date-based cron (e.g. 1st Thursday of each month)
Implement **option 1** (check inside the script) for flexibility.

---

### Task 4 — README.md

Write a clear public README explaining:
- What the project does
- Live demo link: `https://thursdaynumbers.com`
- How to set up your own fork (SendGrid, GitHub Secrets)
- How the number generation works (with the disclaimer about randomness)
- How to run locally
- Data source attribution

---

## Environment Variables / GitHub Secrets Required

| Secret Name | Description | Where to get it |
|---|---|---|
| `SENDGRID_API_KEY` | SendGrid API key with Mail Send permission | sendgrid.com → Settings → API Keys |
| `EMAIL_RECIPIENT` | Email address to send picks to | Your email |
| `EMAIL_SENDER` | Verified sender email in SendGrid | Must be verified in SendGrid |

**How to add to GitHub:**
Repo → Settings → Secrets and variables → Actions → New repository secret

---

## Python Dependencies (`requirements.txt`)

```
requests==2.31.0
beautifulsoup4==4.12.3
sendgrid==6.11.0
```

---

## Key Technical Decisions Already Made

| Decision | Choice | Reason |
|---|---|---|
| Email provider | SendGrid | More secure for public repos; API key is send-only, not tied to personal email account |
| Scheduling | GitHub Actions cron | Free, no server needed, runs in cloud |
| Number strategy | Hot numbers only | User requested hot numbers for all 18 games |
| Games per run | 18 | User buys 18 standard games per draw |
| Web framework | Vanilla JS (no build step) | GitHub Pages works without CI build for static files |
| Custom domain | thursdaynumbers.com via Cloudflare | Domain registered on Cloudflare, pointed to GitHub Pages |
| Data storage | JSON files in repo | Simple, version-controlled, no database needed |
| Scraping source | australia.national-lottery.com | Only public source with per-draw URL pattern that works |

---

## Current Data Stats (as of last scrape)

- **Total draws:** 412
- **Range:** Draw #1144 (2018-04-19) → Draw #1555 (2026-03-05)
- **Hot main balls:** 9, 7, 17, 11, 19, 18, 23, 14, 12, 30
- **Cold main balls:** 31, 13, 26, 29, 8, 33, 35, 15, 34, 5
- **Hot Powerballs:** 2, 4, 6, 10, 3
- **Scraping note:** The source site only has data from ~2018 onward

---

## Important Disclaimers to Include Everywhere

> Powerball is a game of pure chance. Each draw is independent and random.
> Past results have zero statistical influence on future draws.
> This tool is for entertainment only. Please gamble responsibly.
> For help with gambling: gamblinghelponline.org.au or call 1800 858 858.

---

## Cloudflare DNS Setup (for thursdaynumbers.com)

To point `thursdaynumbers.com` to GitHub Pages, add these DNS records in Cloudflare:

| Type | Name | Content | Proxy |
|---|---|---|---|
| A | @ | 185.199.108.153 | DNS only (grey cloud) |
| A | @ | 185.199.109.153 | DNS only (grey cloud) |
| A | @ | 185.199.110.153 | DNS only (grey cloud) |
| A | @ | 185.199.111.153 | DNS only (grey cloud) |
| CNAME | www | YOUR-GITHUB-USERNAME.github.io | DNS only (grey cloud) |

**Important:** Set Cloudflare proxy to "DNS only" (grey cloud), not "Proxied" (orange cloud),
otherwise GitHub Pages SSL certificate provisioning will fail.

Then in GitHub: Repo → Settings → Pages → Custom domain → enter `thursdaynumbers.com`
GitHub will auto-provision an SSL certificate within a few minutes.

---

## How to Start in Claude Code

When opening this project in Claude Code, say:

> "Read CLAUDE.md and start with Task 1 — build all four Python scripts."

Then continue with:
> "Now do Task 2 — convert the React prototype to a static GitHub Pages site."

Then:
> "Now do Task 3 — create the GitHub Actions workflow."

Finally:
> "Do Task 4 — write the README."

---

## Notes for Claude Code

- Always read this file first before starting any task
- The `data/powerball_draws.json` file is the single source of truth — never overwrite it, only append
- All scripts should be runnable standalone: `python scripts/scrape.py`
- Use `argparse` for CLI flags where relevant
- Write clear `print()` statements so GitHub Actions logs are readable
- Test scraping with a small date range first before running on all missing draws
- The web page should work by just opening `web/index.html` locally (no server needed)
- Use `json.dumps(..., indent=2)` for all JSON writes to keep diffs readable in git
