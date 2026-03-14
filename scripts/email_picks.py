#!/usr/bin/env python3
"""
email_picks.py — Send the latest Powerball picks via Brevo transactional email API.

Usage:
    python scripts/email_picks.py
    python scripts/email_picks.py --dry-run   # Print email body, don't send

Required environment variables:
    BREVO_API_KEY    — Brevo API key with transactional email permission
    EMAIL_RECIPIENT  — Destination email address
    EMAIL_SENDER     — Verified sender email in Brevo
"""

import argparse
import json
import os
import sys
from pathlib import Path

import requests

PICKS_FILE = Path(__file__).parent.parent / "web" / "picks" / "picks_history.json"

# Matches website CSS: .ball-sm.main and .ball-sm.pb gradients exactly
MAIN_GRADIENT = "linear-gradient(135deg,#6366f1,#4f46e5)"
MAIN_FALLBACK = "#6366f1"
PB_GRADIENT   = "linear-gradient(135deg,#a855f7,#7e22ce)"
PB_FALLBACK   = "#a855f7"


def load_latest_picks():
    if not PICKS_FILE.exists():
        print("ERROR: No picks file found. Run generate_picks.py first.", file=sys.stderr)
        sys.exit(1)
    with open(PICKS_FILE) as f:
        history = json.load(f)
    if not history:
        print("ERROR: Picks history is empty.", file=sys.stderr)
        sys.exit(1)
    return history[-1]


def ball_html(number, gradient, fallback, size=34):
    # background-color is the Outlook fallback; background (gradient) overrides in all modern clients
    style = (
        f"display:inline-block;width:{size}px;height:{size}px;"
        f"line-height:{size}px;border-radius:50%;"
        f"background-color:{fallback};background:{gradient};"
        f"color:#fff;font-weight:700;font-size:13px;text-align:center;"
        f"margin:2px;font-family:Arial,sans-serif;"
    )
    return f'<span style="{style}">{number}</span>'


def build_html(picks):
    draw_date   = picks["generated_at"][:10]
    draws_count = picks["draws_analysed"]
    data_range  = picks["data_range"]

    rows = []
    for i, g in enumerate(picks["games"]):
        row_bg = "#22263a" if i % 2 == 0 else "#1a1d27"
        main_balls = "".join(ball_html(b, MAIN_GRADIENT, MAIN_FALLBACK) for b in g["main"])
        pb = ball_html(g["powerball"], PB_GRADIENT, PB_FALLBACK)
        rows.append(
            f'<tr style="background:{row_bg};">'
            f'<td style="padding:8px 14px;color:#8892a4;font-family:Arial,sans-serif;font-size:12px;'
            f'font-weight:600;text-transform:uppercase;letter-spacing:0.5px;white-space:nowrap;">'
            f'Game {g["game"]}</td>'
            f'<td style="padding:8px 6px;">{main_balls}</td>'
            f'<td style="padding:8px 6px;">{pb}</td>'
            f"</tr>"
        )

    rows_html = "\n".join(rows)
    hot_main  = ", ".join(str(b) for b in picks["hot_main_balls"])
    hot_pb    = ", ".join(str(b) for b in picks["hot_powerballs"])

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#0f1117;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f1117;padding:24px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0"
             style="background:#1a1d27;border-radius:12px;overflow:hidden;border:1px solid #2d3148;max-width:600px;">

        <!-- Header -->
        <tr><td style="background:#22263a;padding:32px;text-align:center;border-bottom:1px solid #2d3148;">
          <div style="font-size:36px;margin-bottom:8px;">🎱</div>
          <h1 style="color:#e2e8f0;margin:0;font-size:24px;font-weight:700;letter-spacing:-0.5px;">Thursday Numbers</h1>
          <p style="color:#8892a4;margin:8px 0 0;font-size:14px;">Your Powerball Picks — Draw week of {draw_date}</p>
        </td></tr>

        <!-- Stats bar -->
        <tr><td style="padding:16px 28px;background:#1a1d27;border-bottom:1px solid #2d3148;">
          <p style="margin:0;font-size:12px;color:#8892a4;line-height:1.9;">
            📊 Analysis based on <strong style="color:#e2e8f0;">{draws_count} draws</strong>
            &nbsp;·&nbsp; {data_range}<br>
            🔥 Hot main: <strong style="color:#e2e8f0;">{hot_main}</strong><br>
            🔮 Hot PBs: <strong style="color:#e2e8f0;">{hot_pb}</strong>
          </p>
        </td></tr>

        <!-- Column headers -->
        <tr style="background:#22263a;">
          <td style="padding:10px 14px;font-size:10px;color:#8892a4;font-weight:700;
                     text-transform:uppercase;letter-spacing:1px;">Game</td>
          <td style="padding:10px 6px;font-size:10px;color:#8892a4;font-weight:700;
                     text-transform:uppercase;letter-spacing:1px;">Main Numbers</td>
          <td style="padding:10px 6px;font-size:10px;color:#8892a4;font-weight:700;
                     text-transform:uppercase;letter-spacing:1px;">Powerball</td>
        </tr>

        <!-- Game rows -->
{rows_html}

        <!-- Disclaimer -->
        <tr><td colspan="3" style="padding:20px 28px;border-top:1px solid #2d3148;">
          <p style="margin:0;font-size:11px;color:#4a5568;line-height:1.7;">
            ⚠️ Generated from statistical analysis of {draws_count} draws. Does not predict outcomes.
            Powerball is a game of pure chance — past results have zero influence on future draws.
            For entertainment only. Please gamble responsibly.<br>
            Help: <a href="https://www.gamblinghelponline.org.au" style="color:#4a5568;">gamblinghelponline.org.au</a>
            or call <strong>1800 858 858</strong>.
          </p>
        </td></tr>

        <!-- Footer -->
        <tr><td colspan="3" style="background:#22263a;padding:14px 28px;text-align:center;border-top:1px solid #2d3148;">
          <a href="https://thursdaynumbers.com" style="color:#6366f1;text-decoration:none;font-size:12px;">
            thursdaynumbers.com
          </a>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


def build_plaintext(picks):
    draw_date = picks["generated_at"][:10]
    lines = [
        f"🎱 Your Powerball Picks — Draw week of {draw_date}",
        f"Analysis: {picks['draws_analysed']} draws ({picks['data_range']})",
        f"Hot main balls: {picks['hot_main_balls']}",
        f"Hot Powerballs: {picks['hot_powerballs']}",
        "",
        "Your 18 games:",
        "-" * 50,
    ]
    for g in picks["games"]:
        main_str = "  ".join(f"{b:2d}" for b in g["main"])
        lines.append(f"Game {g['game']:2d}: [{main_str}]  PB: {g['powerball']}")
    lines += [
        "",
        "-" * 50,
        f"Generated from statistical analysis of {picks['draws_analysed']} draws.",
        "Does not predict outcomes. For entertainment only.",
        "Help: gamblinghelponline.org.au | 1800 858 858",
        "thursdaynumbers.com",
    ]
    return "\n".join(lines)


def send_email(picks, html_body, text_body):
    api_key = os.environ.get("BREVO_API_KEY")
    recipient = os.environ.get("EMAIL_RECIPIENT")
    sender = os.environ.get("EMAIL_SENDER")

    for var, val in [("BREVO_API_KEY", api_key), ("EMAIL_RECIPIENT", recipient), ("EMAIL_SENDER", sender)]:
        if not val:
            print(f"ERROR: Environment variable {var} is not set.", file=sys.stderr)
            sys.exit(1)

    draw_date = picks["generated_at"][:10]
    subject = f"🎱 Your Powerball Picks — Draw Week of {draw_date}"

    payload = {
        "sender": {"name": "Thursday Numbers", "email": sender},
        "to": [{"email": recipient}],
        "subject": subject,
        "htmlContent": html_body,
        "textContent": text_body,
    }

    try:
        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={"api-key": api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        print(f"  Email sent! Status code: {response.status_code}")
    except requests.HTTPError:
        print(f"ERROR: Brevo API error {response.status_code}: {response.text}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to send email: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Send Powerball picks via Brevo")
    parser.add_argument("--dry-run", action="store_true", help="Print email, don't send")
    args = parser.parse_args()

    print("=== Email Sender ===")
    picks = load_latest_picks()
    print(f"  Loaded picks generated at {picks['generated_at']}")

    html_body = build_html(picks)
    text_body = build_plaintext(picks)

    if args.dry_run:
        print("\n--- Plain text version ---")
        print(text_body)
        print("\n[dry-run] Skipping send.")
    else:
        send_email(picks, html_body, text_body)

    print("=== Done ===")


if __name__ == "__main__":
    main()
