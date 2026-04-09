#!/usr/bin/env python3
"""
scrape.py — Fetch new Australian Powerball draw results and append to data file.

Usage:
    python scripts/scrape.py
    python scripts/scrape.py --dry-run   # Print what would be fetched, don't save
"""

import argparse
import json
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DATA_FILE = Path(__file__).parent.parent / "web" / "data" / "powerball_draws.json"
BASE_URL = "https://australia.national-lottery.com/powerball/results/{}"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def load_draws():
    with open(DATA_FILE) as f:
        return json.load(f)


def save_draws(draws):
    with open(DATA_FILE, "w") as f:
        json.dump(draws, f, indent=2)
    print(f"  Saved {len(draws)} total draws to {DATA_FILE}")


def last_thursday_on_or_before(d: date) -> date:
    """Return the most recent Thursday on or before date d."""
    days_since_thursday = (d.weekday() - 3) % 7
    return d - timedelta(days=days_since_thursday)


def thursdays_between(start: date, end: date):
    """Yield every Thursday strictly after start, up to and including end."""
    d = start + timedelta(days=1)
    d = d + timedelta(days=(3 - d.weekday()) % 7)
    while d <= end:
        yield d
        d += timedelta(weeks=1)


def fetch_draw(draw_date: date):
    """Fetch a single draw from the website. Returns (main_balls, powerball) or None.
    Retries up to 3 times with exponential backoff (2s, 4s, 8s) on transient errors.
    """
    url = BASE_URL.format(draw_date.strftime("%d-%m-%Y"))
    for attempt in range(1, 4):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            break
        except requests.RequestException as e:
            if attempt < 3:
                delay = 2 ** attempt  # 2s, 4s, 8s
                print(f"  WARNING: Attempt {attempt}/3 failed for {draw_date}: {e}. Retrying in {delay}s...")
                time.sleep(delay)
            else:
                print(f"  WARNING: All 3 attempts failed for {draw_date}: {e}")
                return None

    soup = BeautifulSoup(resp.text, "html.parser")

    main_balls = []
    powerball = None

    for li in soup.find_all("li"):
        classes = li.get("class", [])
        text = li.get_text(strip=True)
        if not text.isdigit():
            continue
        val = int(text)
        if "powerball" in classes and "ball" in classes:
            powerball = val
        elif "ball" in classes and "pb" in classes and "powerball" not in classes:
            main_balls.append(val)

    if len(main_balls) != 7 or powerball is None:
        print(f"  WARNING: Unexpected data for {draw_date}: main={main_balls}, pb={powerball}")
        return None

    return sorted(main_balls), powerball


def main():
    parser = argparse.ArgumentParser(description="Scrape new Powerball draws")
    parser.add_argument("--dry-run", action="store_true", help="Don't save results")
    args = parser.parse_args()

    print("=== Powerball Scraper ===")
    draws = load_draws()
    if not draws:
        print("ERROR: Data file is empty. Cannot determine last draw number or date.", file=sys.stderr)
        sys.exit(1)
    print(f"  Loaded {len(draws)} existing draws")

    last_date = datetime.strptime(draws[-1]["date"], "%Y-%m-%d").date()
    last_draw_num = draws[-1]["draw"]
    print(f"  Last known draw: #{last_draw_num} on {last_date}")

    today = date.today()
    target_end = last_thursday_on_or_before(today)
    missing_thursdays = list(thursdays_between(last_date, target_end))

    if not missing_thursdays:
        print("  No new draws to fetch. Already up to date.")
        return

    print(f"  Fetching {len(missing_thursdays)} draw(s)...")

    new_draws = []
    next_draw_num = last_draw_num + 1

    for draw_date in missing_thursdays:
        print(f"  Fetching draw for {draw_date}...", end="", flush=True)
        result = fetch_draw(draw_date)
        if result:
            main_balls, powerball = result
            new_draws.append({
                "draw": next_draw_num,
                "date": draw_date.isoformat(),
                "main": main_balls,
                "powerball": powerball,
            })
            print(f" ✓  #{next_draw_num}: main={main_balls}, pb={powerball}")
            next_draw_num += 1
        else:
            print(f" ✗  skipped")
        time.sleep(0.5)

    if new_draws:
        print(f"\n  Found {len(new_draws)} new draw(s).")
        if args.dry_run:
            print("  [dry-run] Would have saved — skipping write.")
        else:
            draws.extend(new_draws)
            save_draws(draws)
    else:
        print("  No new draws were successfully fetched.")

    print("=== Done ===")


if __name__ == "__main__":
    main()
