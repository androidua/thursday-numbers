# 🎱 Thursday Numbers

> **Every Thursday, smarter numbers.**

Statistical analysis of Australian Powerball historical draw data. Generates 18 hot-number game picks and emails them automatically every 3 weeks via SendGrid — all driven by a free GitHub Actions workflow.

🌐 **Live site:** [thursdaynumbers.com](https://thursdaynumbers.com)

---

## What it does

| Feature | Detail |
|---|---|
| 📊 Web dashboard | Frequency charts, hot/cold numbers, recent trends, full draw history |
| 🎯 Number picker | 18 hot-number games per run (7 main + 1 Powerball each) |
| 🤖 Auto-update | GitHub Actions runs every Thursday; script checks if 3+ weeks have passed |
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
│   └── powerball_draws.json      ← Draw history (grows automatically)
├── picks/
│   └── picks_history.json        ← Log of every generated pick set
├── scripts/
│   ├── scrape.py                 ← Fetch new draws from the web
│   ├── generate_picks.py         ← Generate 18 hot-number games
│   ├── email_picks.py            ← Send picks via SendGrid
│   └── run_all.py                ← Full pipeline entry point
├── web/
│   ├── index.html                ← GitHub Pages static site
│   ├── app.js                    ← Vanilla JS analyser
│   └── style.css                 ← Dark-themed styles
├── .github/workflows/
│   └── powerball-update.yml      ← Scheduled GitHub Actions workflow
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

# Full pipeline dry-run (no email sent)
python scripts/run_all.py --dry-run
```

The web app (`web/index.html`) loads data via `fetch()`, so it needs to be served over HTTP — it won't work if you just open the file directly. Use any simple server:

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

1. Sign up at [sendgrid.com](https://sendgrid.com) (free tier = 100 emails/day)
2. **Settings → API Keys → Create API Key**
3. Choose **Restricted Access → Mail Send only**
4. Copy the key (shown once)
5. **Settings → Sender Authentication** — verify your sender email address

### 3. Add GitHub Secrets

In your forked repo: **Settings → Secrets and variables → Actions → New repository secret**

| Secret name | Value |
|---|---|
| `SENDGRID_API_KEY` | Your SendGrid API key |
| `EMAIL_RECIPIENT` | Email address to receive picks |
| `EMAIL_SENDER` | Verified SendGrid sender email |

### 4. Enable GitHub Pages

1. **Repo → Settings → Pages**
2. Source: **Deploy from branch → `main` → `/web` folder**
3. Custom domain: enter your domain (or use `<your-username>.github.io/thursday-numbers`)
4. Tick **Enforce HTTPS** after the SSL cert provisions (~5 min)

### 5. (Optional) Custom domain via Cloudflare

Add these DNS records in Cloudflare, with proxy set to **DNS only** (grey cloud):

| Type | Name | Content |
|---|---|---|
| A | @ | 185.199.108.153 |
| A | @ | 185.199.109.153 |
| A | @ | 185.199.110.153 |
| A | @ | 185.199.111.153 |
| CNAME | www | `<your-github-username>.github.io` |

Update `web/CNAME` with your domain name.

---

## Data source

Draw data scraped from [australia.national-lottery.com](https://australia.national-lottery.com/powerball) — the only public source with a per-draw URL pattern. Data available from approximately April 2018 onward.

---

## Tech stack

| Layer | Choice | Reason |
|---|---|---|
| Web frontend | Vanilla HTML/CSS/JS + Chart.js (CDN) | No build step — GitHub Pages serves static files directly |
| Scraping | Python + requests + BeautifulSoup | Simple, reliable |
| Email | SendGrid Python SDK | API key is send-only; safe for public repos |
| Automation | GitHub Actions cron | Free, serverless, no infrastructure needed |
| Data | JSON files in repo | Simple, version-controlled, human-readable diffs |

---

*Built with [Claude Code](https://claude.ai/code) · For entertainment only · Gamble responsibly*
