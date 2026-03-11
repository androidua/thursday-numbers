# Getting Started — Powerball Analyser Project

This folder contains everything you need to continue building this project in Claude Code.

## Files in this folder

| File | What it is |
|---|---|
| `CLAUDE.md` | Full project brief — Claude Code reads this first |
| `powerball_draws.json` | 412 scraped draws (Apr 2018 → Mar 2026) — goes into `data/` folder |
| `SETUP.md` | This file |

## Step 1 — Create your GitHub repo

1. Go to github.com → New repository
2. Name it: `thursday-numbers` (or whatever you like)
3. Set it to **Public**
4. Don't initialise with README (we'll push our own)

## Step 2 — Set up your local folder

```bash
mkdir thursday-numbers
cd thursday-numbers
git init
mkdir -p data scripts picks web .github/workflows
cp /path/to/powerball_draws.json data/powerball_draws.json
cp /path/to/CLAUDE.md .
```

## Step 3 — Open in Claude Code

```bash
claude
```

Then just say:
> "Read CLAUDE.md and start with Task 1 — build all four Python scripts."

## Step 4 — Add GitHub Secrets (after scripts are built)

Before the GitHub Action can run, you need 3 secrets in your repo:

1. Go to your repo on GitHub
2. Settings → Secrets and variables → Actions
3. Add these three:

| Name | Value |
|---|---|
| `SENDGRID_API_KEY` | Your SendGrid API key |
| `EMAIL_RECIPIENT` | The email address to receive picks |
| `EMAIL_SENDER` | Your verified sender email in SendGrid |

### Getting a SendGrid API key (free):
1. Sign up at sendgrid.com (free tier = 100 emails/day)
2. Go to Settings → API Keys → Create API Key
3. Choose **Restricted Access** → enable only **Mail Send**
4. Copy the key — you only see it once!
5. In SendGrid: go to Settings → Sender Authentication → verify your sender email

## Step 5 — Enable GitHub Pages

Once the web page is built (Task 2) — using your custom domain `thursdaynumbers.com`:
1. Repo → Settings → Pages
2. Source: Deploy from branch → `main` → `/web` folder
3. Custom domain → enter `thursdaynumbers.com`
4. Tick "Enforce HTTPS" once the SSL certificate is issued (takes ~5 min)
5. Your site will be live at: `https://thursdaynumbers.com`

See the Cloudflare DNS setup section in `CLAUDE.md` for the exact DNS records to add.

---

That's it. Claude Code + CLAUDE.md will handle the rest.
