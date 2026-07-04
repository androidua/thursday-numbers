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


def parse_draw_page(html):
    """Extract (sorted_main_balls, powerball) from a results page, or None.

    Validates the current-format ranges (7 unique mains in 1-35, PB 1-20) —
    corrupt or partial pages must never append silently into the data file.
    """
    soup = BeautifulSoup(html, "html.parser")

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
        return None
    if any(b < 1 or b > 35 for b in main_balls) or len(set(main_balls)) != 7:
        return None
    if powerball < 1 or powerball > 20:
        return None

    return sorted(main_balls), powerball


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

    time.sleep(0.5)  # politeness delay between page fetches

    result = parse_draw_page(resp.text)
    if result is None:
        print(f"  WARNING: Unexpected or invalid data for {draw_date}")
    return result


def collect_new_draws(missing_thursdays, last_draw_num, fetch_fn):
    """Fetch draws in date order, assigning consecutive draw numbers.

    STOPS at the first failure and returns (new_draws, failed_date). Continuing
    past a failure would assign the next draw the failed draw's number, and the
    failed date — then older than the newest saved date — would never be
    retried. Stopping keeps the file contiguous; the next run self-heals.
    """
    new_draws = []
    next_num = last_draw_num + 1
    for draw_date in missing_thursdays:
        print(f"  Fetching draw for {draw_date}...", end="", flush=True)
        result = fetch_fn(draw_date)
        if result is None:
            print(" ✗  failed")
            return new_draws, draw_date
        main_balls, powerball = result
        new_draws.append({
            "draw": next_num,
            "date": draw_date.isoformat(),
            "main": main_balls,
            "powerball": powerball,
        })
        print(f" ✓  #{next_num}: main={main_balls}, pb={powerball}")
        next_num += 1
    return new_draws, None


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

    new_draws, failed_date = collect_new_draws(missing_thursdays, last_draw_num, fetch_draw)
    if failed_date is not None:
        print(f"\n  WARNING: Stopped at {failed_date} — this and any later Thursdays "
              f"will be retried on the next run (keeps draw numbering contiguous).")

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
