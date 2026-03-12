#!/usr/bin/env python3
"""
scrape_historical.py — One-time backfill of all Australian Powerball draws
from 1996 up to (but not including) the first draw already in the data file.

Uses year-archive pages so each year is one HTTP request instead of ~52.

Usage:
    python scripts/scrape_historical.py --dry-run
    python scripts/scrape_historical.py
"""

import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DATA_FILE = Path(__file__).parent.parent / "web" / "data" / "powerball_draws.json"
ARCHIVE_URL = "https://australia.national-lottery.com/powerball/results-archive-{year}"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; thursday-numbers-bot/1.0)"}
SLEEP_BETWEEN_YEARS = 1.0  # seconds


def load_draws():
    with open(DATA_FILE) as f:
        return json.load(f)


def save_draws(draws):
    with open(DATA_FILE, "w") as f:
        json.dump(draws, f, indent=2)
    print(f"  Saved {len(draws)} total draws to {DATA_FILE}")


def parse_archive_page(year: int, stop_before_draw: int) -> list[dict]:
    """
    Fetch the archive page for *year* and return all draws found,
    stopping (exclusive) once draw number >= stop_before_draw.

    Each returned dict has keys: draw, date, main (list), powerball (int).
    """
    url = ARCHIVE_URL.format(year=year)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  WARNING: Failed to fetch {year} archive: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    draws = []
    skipped = 0

    # Each draw is a <tr> containing an <a href="/powerball/results/DD-MM-YYYY">
    for tr in soup.find_all("tr"):
        a = tr.find("a", href=re.compile(r"/powerball/results/\d{2}-\d{2}-\d{4}"))
        if not a:
            continue

        # --- Draw number ---
        link_text = a.get_text(separator=" ", strip=True)
        m = re.search(r"Draw\s+(\d+)", link_text, re.IGNORECASE)
        if not m:
            print(f"  WARNING: Could not parse draw number from '{link_text[:60]}'")
            continue
        draw_num = int(m.group(1))

        if draw_num >= stop_before_draw:
            skipped += 1
            continue

        # --- Date from href ---
        href = a["href"]  # e.g. /powerball/results/26-12-1996
        date_str_raw = href.rsplit("/", 1)[-1]  # DD-MM-YYYY
        draw_date = datetime.strptime(date_str_raw, "%d-%m-%Y").date().isoformat()

        # --- Balls ---
        main_balls = []
        powerball = None

        for li in tr.find_all("li"):
            classes = li.get("class", [])
            text = li.get_text(strip=True)
            if not text.isdigit():
                continue
            val = int(text)
            if "powerball" in classes and "ball" in classes:
                powerball = val
            elif "ball" in classes and "powerball" not in classes:
                main_balls.append(val)

        if not main_balls or powerball is None:
            print(f"  WARNING: Incomplete draw #{draw_num} ({draw_date}): "
                  f"main={main_balls}, pb={powerball} — skipping")
            continue

        draws.append({
            "draw": draw_num,
            "date": draw_date,
            "main": sorted(main_balls),
            "powerball": powerball,
        })

    if skipped:
        print(f"  Skipped {skipped} draw(s) already in dataset")

    return draws


def main():
    parser = argparse.ArgumentParser(description="Backfill historical Powerball draws")
    parser.add_argument("--dry-run", action="store_true",
                        help="Fetch and parse but don't write to file")
    parser.add_argument("--start-year", type=int, default=1996,
                        help="First year to fetch (default: 1996)")
    args = parser.parse_args()

    print("=== Historical Powerball Backfill ===")

    existing = load_draws()
    first_existing_draw = existing[0]["draw"]  # e.g. 1144
    first_existing_date = existing[0]["date"]
    print(f"  Existing data: {len(existing)} draws, first #{first_existing_draw} on {first_existing_date}")
    print(f"  Will fetch all draws before #{first_existing_draw}")

    # Determine year range: from start_year up to the year just before our data,
    # plus the year our data starts in case there are earlier draws in that year.
    first_year = datetime.strptime(first_existing_date, "%Y-%m-%d").year
    years = list(range(args.start_year, first_year + 1))
    print(f"  Fetching archive years: {years[0]}–{years[-1]}\n")

    historical = []
    seen_draws = set()

    for year in years:
        print(f"  Fetching {year} archive...", end=" ", flush=True)
        draws = parse_archive_page(year, stop_before_draw=first_existing_draw)

        # Deduplicate (shouldn't happen, but safety net)
        new_draws = [d for d in draws if d["draw"] not in seen_draws]
        for d in new_draws:
            seen_draws.add(d["draw"])

        historical.extend(new_draws)
        print(f"got {len(new_draws)} draws (total so far: {len(historical)})")

        if year < years[-1]:
            time.sleep(SLEEP_BETWEEN_YEARS)

    if not historical:
        print("\n  No historical draws found. Nothing to do.")
        return

    # Sort by draw number ascending
    historical.sort(key=lambda d: d["draw"])

    print(f"\n  Historical draws fetched: {len(historical)}")
    print(f"  Range: #{historical[0]['draw']} ({historical[0]['date']}) "
          f"→ #{historical[-1]['draw']} ({historical[-1]['date']})")

    # Check for gaps
    expected = set(range(historical[0]["draw"], historical[-1]["draw"] + 1))
    found = {d["draw"] for d in historical}
    missing = sorted(expected - found)
    if missing:
        print(f"  WARNING: {len(missing)} draw(s) missing from historical range: "
              f"{missing[:10]}{'...' if len(missing) > 10 else ''}")

    # Summarise format eras
    eras = {}
    for d in historical:
        count = len(d["main"])
        eras[count] = eras.get(count, 0) + 1
    print(f"  Main ball counts: {dict(sorted(eras.items()))}")

    if args.dry_run:
        print("\n  [dry-run] Would prepend historical draws — skipping write.")
    else:
        merged = historical + existing
        merged.sort(key=lambda d: d["draw"])

        # Safety: remove any duplicates by draw number
        seen = set()
        deduped = []
        for d in merged:
            if d["draw"] not in seen:
                deduped.append(d)
                seen.add(d["draw"])

        print(f"\n  Merged: {len(deduped)} total draws")
        save_draws(deduped)

    print("=== Done ===")


if __name__ == "__main__":
    main()
