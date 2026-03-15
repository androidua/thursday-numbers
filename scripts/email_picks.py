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

# Matches website CSS: .ball-sm.main (#6366f1) and .ball-sm.pb (#a855f7)
MAIN_COLOUR = "#6366f1"
PB_COLOUR   = "#a855f7"


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


def ball_html(number, colour, size=38):
    style = (
        f"display:inline-block;width:{size}px;height:{size}px;"
        f"line-height:{size}px;border-radius:50%;background:{colour};"
        f"color:#fff;font-weight:bold;font-size:14px;text-align:center;"
        f"margin:2px;font-family:Arial,sans-serif;"
    )
    return f'<span class="ball" style="{style}">{number}</span>'


def build_html(picks):
    draw_date   = picks["generated_at"][:10]
    draws_count = picks["draws_analysed"]
    data_range  = picks["data_range"]

    rows = []
    for g in picks["games"]:
        main_balls = "".join(ball_html(b, MAIN_COLOUR) for b in g["main"])
        pb = ball_html(g["powerball"], PB_COLOUR)
        rows.append(
            f'<tr class="game-row">'
            f'<td class="game-label" style="padding:6px 12px;color:#666;font-family:Arial,sans-serif;font-size:14px;white-space:nowrap;">Game {g["game"]}</td>'
            f'<td style="padding:6px 4px;" x-apple-data-detectors="false">{main_balls}</td>'
            f'<td style="padding:6px 4px;" x-apple-data-detectors="false">{pb}</td>'
            f"</tr>"
        )

    rows_html = "\n".join(rows)
    hot_main = ", ".join(str(b) for b in picks["hot_main_balls"])
    hot_pb   = ", ".join(str(b) for b in picks["hot_powerballs"])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="format-detection" content="telephone=no, date=no, address=no, email=no, url=no">
  <style>
    @media only screen and (max-width: 600px) {{
      .container {{ width: 100% !important; }}
      .header-cell {{ padding: 24px 16px !important; }}
      .stats-cell {{ padding: 16px !important; }}
      .games-cell {{ padding: 12px 8px 0 !important; }}
      .disclaimer-cell {{ padding: 16px !important; }}
      .footer-cell {{ padding: 12px 16px !important; }}
      .game-label {{ padding: 4px 6px !important; font-size: 12px !important; white-space: nowrap; }}
      .game-row td {{ padding: 3px 2px !important; }}
      .ball {{ width: 28px !important; height: 28px !important; line-height: 28px !important; font-size: 11px !important; margin: 1px !important; }}
      .th-game {{ padding: 6px !important; }}
      .th-main {{ padding: 6px 4px !important; }}
      .th-pb {{ padding: 6px 4px !important; }}
    }}
  </style>
</head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;padding:24px 0;">
    <tr><td align="center">
      <table class="container" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.1);max-width:600px;width:100%;">

        <!-- Header -->
        <tr><td class="header-cell" style="background:linear-gradient(135deg,#1a1a2e,#16213e);padding:32px;text-align:center;">
          <div style="font-size:36px;margin-bottom:8px;">🎱</div>
          <h1 style="color:#fff;margin:0;font-size:24px;font-weight:700;">Thursday Numbers</h1>
          <p style="color:#a0aec0;margin:8px 0 0;font-size:14px;">Your Powerball Picks — Draw week of {draw_date}</p>
        </td></tr>

        <!-- Stats -->
        <tr><td class="stats-cell" style="padding:20px 32px;background:#f8f9ff;border-bottom:1px solid #eee;">
          <p style="margin:0;font-size:13px;color:#555;">
            📊 Analysis based on <strong>{draws_count} draws</strong> ({data_range})<br>
            🔥 Hot main balls: <strong>{hot_main}</strong><br>
            🔮 Hot Powerballs: <strong>{hot_pb}</strong>
          </p>
        </td></tr>

        <!-- Table header -->
        <tr><td class="games-cell" style="padding:16px 32px 0;" align="center">
          <table cellpadding="0" cellspacing="0" style="margin:0 auto;">
            <thead>
              <tr style="background:#f0f0f0;">
                <th class="th-game" style="padding:8px 12px;text-align:left;font-size:12px;color:#666;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;white-space:nowrap;">Game</th>
                <th class="th-main" style="padding:8px;text-align:left;font-size:12px;color:#666;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">Main Numbers</th>
                <th class="th-pb" style="padding:8px;text-align:left;font-size:12px;color:#666;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;white-space:nowrap;">Powerball</th>
              </tr>
            </thead>
            <tbody>
{rows_html}
            </tbody>
          </table>
        </td></tr>

        <!-- Disclaimer -->
        <tr><td class="disclaimer-cell" style="padding:24px 32px;border-top:1px solid #eee;margin-top:16px;">
          <p style="margin:0;font-size:11px;color:#999;line-height:1.6;">
            ⚠️ Generated from statistical analysis of {draws_count} draws. Does not predict outcomes.<br>
            Powerball is a game of pure chance. Each draw is independent and random.
            Past results have zero statistical influence on future draws.<br>
            This tool is for entertainment only. Please gamble responsibly.<br>
            Help: <a href="https://www.gamblinghelponline.org.au" style="color:#999;">gamblinghelponline.org.au</a> or call <strong>1800 858 858</strong>.
          </p>
        </td></tr>

        <!-- Footer -->
        <tr><td class="footer-cell" style="background:#1a1a2e;padding:16px 32px;text-align:center;">
          <p style="margin:0;font-size:12px;color:#666;">
            <a href="https://thursdaynumbers.com" style="color:#7c8db5;text-decoration:none;">thursdaynumbers.com</a>
          </p>
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
