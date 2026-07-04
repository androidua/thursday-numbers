#!/usr/bin/env python3
"""
check_data.py — Validate powerball_draws.json integrity and freshness.

Integrity (always enforced): contiguous draw numbering, strictly ascending
dates, valid current-format ball ranges. Freshness (enforced only with
--strict): the newest recorded draw must be the most recent Thursday on or
before today. The powerball-update workflow runs this AFTER its commit step
with --strict, so a broken scrape turns the workflow red (GitHub emails on
failure) without ever blocking a partial data commit.

Usage:
    python scripts/check_data.py            # integrity only; freshness is informational
    python scripts/check_data.py --strict   # also fail (exit 1) on stale data
"""

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

DATA_FILE = Path(__file__).parent.parent / "web" / "data" / "powerball_draws.json"


def last_thursday_on_or_before(d: date) -> date:
    return d - timedelta(days=(d.weekday() - 3) % 7)


def validate_integrity(draws):
    """Return a list of human-readable problems (empty list = healthy)."""
    if not draws:
        return ["data file is empty"]
    problems = []
    for prev, cur in zip(draws, draws[1:]):
        if cur["draw"] != prev["draw"] + 1:
            problems.append(f"draw numbering gap: #{prev['draw']} -> #{cur['draw']}")
        if cur["date"] <= prev["date"]:
            problems.append(f"dates not strictly ascending at draw #{cur['draw']}")
    for d in draws:
        if len(d["main"]) != 7:
            continue  # pre-2018 formats use different pools; only current format is validated
        if len(set(d["main"])) != 7 or any(b < 1 or b > 35 for b in d["main"]):
            problems.append(f"invalid main balls in draw #{d['draw']}: {d['main']}")
        if not (1 <= d["powerball"] <= 20):
            problems.append(f"invalid powerball in draw #{d['draw']}: {d['powerball']}")
    return problems


def check_freshness(draws, today):
    """Return (is_fresh, newest_date, expected_date)."""
    expected = last_thursday_on_or_before(today)
    newest = date.fromisoformat(draws[-1]["date"])
    return newest >= expected, newest, expected


def main():
    parser = argparse.ArgumentParser(description="Validate draw data integrity and freshness")
    parser.add_argument("--strict", action="store_true",
                        help="Exit 1 if data is stale (newest draw older than last expected Thursday)")
    args = parser.parse_args()

    print("=== Data Checker ===")
    with open(DATA_FILE) as f:
        draws = json.load(f)
    print(f"  Loaded {len(draws)} draws")

    problems = validate_integrity(draws)
    if problems:
        for p in problems:
            print(f"  INTEGRITY ERROR: {p}", file=sys.stderr)
        sys.exit(1)
    print("  Integrity     : OK (contiguous numbering, ascending dates, valid ranges)")

    fresh, newest, expected = check_freshness(draws, date.today())
    status = "OK" if fresh else "STALE"
    print(f"  Freshness     : {status} (newest draw {newest}, expected {expected})")
    if not fresh and args.strict:
        print("  ERROR: data is stale — the scrape likely failed. Investigate the source site.",
              file=sys.stderr)
        sys.exit(1)

    print("=== Done ===")


if __name__ == "__main__":
    main()
