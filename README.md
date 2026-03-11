# 🎱 Thursday Numbers

> **Every Thursday, smarter numbers.**

Statistical analysis of Australian Powerball historical draw data. Generates 18 hot-number game picks and emails them automatically every 3 weeks via SendGrid — all driven by a free GitHub Actions workflow.

🌐 **Live site:** [thursdaynumbers.com](https://thursdaynumbers.com) — hosted on Cloudflare Pages

**Current version: v1.2.4**

---

## What it does

| Feature | Detail |
|---|---|
| 📊 Web dashboard | Frequency charts, hot/cold numbers, recent trends, full draw history |
| 🎯 Number picker | 18 hot-number games per run (7 main + 1 Powerball each) |
| 🤖 Auto-update | GitHub Actions runs every Friday morning; script checks if 3+ weeks have passed |
| 📧 Email delivery | HTML email via SendGrid with all 18 games beautifully formatted |
| 📂 Data | 412+ draws from April 2018 onward, stored as a JSON file in the repo |

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
│   ├── data/
│   │   └── powerball_draws.json      ← Draw data served to the web app
│   └── picks/
│       └── picks_history.json        ← Pick history served to the web app
├── .github/workflows/
│   └── powerball-update.yml          ← GitHub Actions (Friday midnight UTC)
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

GitHub Actions runs **every Friday at midnight UTC** (= 10am AEST / 11am AEDT), after Thursday evening's Australian Powerball draw has been published.

The workflow:
- Scrapes any new draws
- Checks if 3+ weeks have passed since the last email
- If yes: generates 18 games → sends email → commits updated JSON files
- Cloudflare Pages auto-deploys on the next push

---

## Data source

Draw data scraped from [australia.national-lottery.com](https://australia.national-lottery.com/powerball). Data available from approximately April 2018 onward.

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
