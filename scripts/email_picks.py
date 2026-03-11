#!/usr/bin/env python3
"""
email_picks.py — Send the latest Powerball picks via SendGrid.

Usage:
    python scripts/email_picks.py
    python scripts/email_picks.py --dry-run   # Print email body, don't send

Required environment variables:
    SENDGRID_API_KEY   — SendGrid API key with Mail Send permission
    EMAIL_RECIPIENT    — Destination email address
    EMAIL_SENDER       — Verified sender email in SendGrid
"""

import argparse
import json
import os
import sys
from pathlib import Path

PICKS_FILE = Path(__file__).parent.parent / "web" / "picks" / "picks_history.json"

BALL_COLOURS = ["#e74c3c", "#e67e22", "#f1c40f", "#2ecc71", "#3498db", "#9b59b6", "#1abc9c"]
PB_COLOUR = "#8e44ad"


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
    return f'<span style="{style}">{number}</span>'


def build_html(picks):
    draw_date = picks["generated_at"][:10]
    draws_count = picks["draws_analysed"]
    data_range = picks["data_range"]

    rows = []
    for g in picks["games"]:
        main_balls = "".join(
            ball_html(b, BALL_COLOURS[i % len(BALL_COLOURS)])
            for i, b in enumerate(g["main"])
        )
        pb = ball_html(g["powerball"], PB_COLOUR)
        rows.append(
            f"<tr>"
            f'<td style="padding:6px 12px;color:#666;font-family:Arial,sans-serif;font-size:14px;">Game {g["game"]}</td>'
            f'<td style="padding:6px 8px;">{main_balls}</td>'
            f'<td style="padding:6px 8px;">{pb}</td>'
            f"</tr>"
        )

    rows_html = "\n".join(rows)
    hot_main = ", ".join(str(b) for b in picks["hot_main_balls"])
    hot_pb = ", ".join(str(b) for b in picks["hot_powerballs"])

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;padding:24px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.1);">

        <!-- Header -->
        <tr><td style="background:linear-gradient(135deg,#1a1a2e,#16213e);padding:32px;text-align:center;">
          <div style="font-size:36px;margin-bottom:8px;">🎱</div>
          <h1 style="color:#fff;margin:0;font-size:24px;font-weight:700;">Thursday Numbers</h1>
          <p style="color:#a0aec0;margin:8px 0 0;font-size:14px;">Your Powerball Picks — Draw week of {draw_date}</p>
        </td></tr>

        <!-- Stats -->
        <tr><td style="padding:20px 32px;background:#f8f9ff;border-bottom:1px solid #eee;">
          <p style="margin:0;font-size:13px;color:#555;">
            📊 Analysis based on <strong>{draws_count} draws</strong> ({data_range})<br>
            🔥 Hot main balls: <strong>{hot_main}</strong><br>
            🔮 Hot Powerballs: <strong>{hot_pb}</strong>
          </p>
        </td></tr>

        <!-- Table header -->
        <tr><td style="padding:16px 32px 0;">
          <table width="100%" cellpadding="0" cellspacing="0">
            <thead>
              <tr style="background:#f0f0f0;">
                <th style="padding:8px 12px;text-align:left;font-size:12px;color:#666;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">Game</th>
                <th style="padding:8px;text-align:left;font-size:12px;color:#666;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">Main Numbers</th>
                <th style="padding:8px;text-align:left;font-size:12px;color:#666;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">Powerball</th>
              </tr>
            </thead>
            <tbody>
{rows_html}
            </tbody>
          </table>
        </td></tr>

        <!-- Disclaimer -->
        <tr><td style="padding:24px 32px;border-top:1px solid #eee;margin-top:16px;">
          <p style="margin:0;font-size:11px;color:#999;line-height:1.6;">
            ⚠️ Generated from statistical analysis of {draws_count} draws. Does not predict outcomes.<br>
            Powerball is a game of pure chance. Each draw is independent and random.
            Past results have zero statistical influence on future draws.<br>
            This tool is for entertainment only. Please gamble responsibly.<br>
            Help: <a href="https://www.gamblinghelponline.org.au" style="color:#999;">gamblinghelponline.org.au</a> or call <strong>1800 858 858</strong>.
          </p>
        </td></tr>

        <!-- Footer -->
        <tr><td style="background:#1a1a2e;padding:16px 32px;text-align:center;">
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
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Content, MimeType

    api_key = os.environ.get("SENDGRID_API_KEY")
    recipient = os.environ.get("EMAIL_RECIPIENT")
    sender = os.environ.get("EMAIL_SENDER")

    for var, val in [("SENDGRID_API_KEY", api_key), ("EMAIL_RECIPIENT", recipient), ("EMAIL_SENDER", sender)]:
        if not val:
            print(f"ERROR: Environment variable {var} is not set.", file=sys.stderr)
            sys.exit(1)

    draw_date = picks["generated_at"][:10]
    subject = f"🎱 Your Powerball Picks — Draw Week of {draw_date}"

    message = Mail(from_email=sender, to_emails=recipient, subject=subject)
    message.add_content(Content(MimeType.text, text_body))
    message.add_content(Content(MimeType.html, html_body))

    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        print(f"  Email sent! Status code: {response.status_code}")
    except Exception as e:
        print(f"ERROR: Failed to send email: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Send Powerball picks via SendGrid")
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
