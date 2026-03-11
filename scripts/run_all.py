#!/usr/bin/env python3
"""
run_all.py — Entry point: scrape → generate picks → email → log.

Includes a 3-week gap check so GitHub Actions can run every Thursday
but only actually process when 3+ weeks have elapsed since the last run.

Usage:
    python scripts/run_all.py
    python scripts/run_all.py --dry-run        # Skip email, print picks
    python scripts/run_all.py --force          # Bypass the 3-week check
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

PICKS_FILE = Path(__file__).parent.parent / "picks" / "picks_history.json"
WEEKS_BETWEEN_RUNS = 3


def check_three_week_gap(force=False):
    """Return True if it's been 3+ weeks since the last run (or no runs yet)."""
    if force:
        print("  [--force] Bypassing 3-week gap check.")
        return True

    if not PICKS_FILE.exists():
        print("  No previous runs found — proceeding.")
        return True

    with open(PICKS_FILE) as f:
        history = json.load(f)

    if not history:
        print("  No previous runs found — proceeding.")
        return True

    last_run_str = history[-1].get("generated_at", "")
    try:
        last_run = datetime.fromisoformat(last_run_str)
    except ValueError:
        print(f"  Could not parse last run time '{last_run_str}' — proceeding.")
        return True

    weeks_elapsed = (datetime.now() - last_run).days / 7
    print(f"  Last run: {last_run_str} ({weeks_elapsed:.1f} weeks ago)")

    if weeks_elapsed < WEEKS_BETWEEN_RUNS:
        print(f"  Only {weeks_elapsed:.1f} weeks since last run ({WEEKS_BETWEEN_RUNS} required).")
        print("  Skipping this run. Use --force to override.")
        return False

    return True


def run_step(step_name, module_path, extra_args=None):
    """Run a Python script as a subprocess, exit on failure."""
    cmd = [sys.executable, str(module_path)]
    if extra_args:
        cmd.extend(extra_args)

    print(f"\n{'='*40}")
    print(f"Step: {step_name}")
    print(f"{'='*40}")

    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"\nERROR: '{step_name}' failed with exit code {result.returncode}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Run full Powerball pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Skip email send")
    parser.add_argument("--force", action="store_true", help="Bypass 3-week gap check")
    args = parser.parse_args()

    print("\n" + "=" * 50)
    print("  🎱  Thursday Numbers — Automated Pipeline")
    print("=" * 50)
    print(f"  Started at: {datetime.now().isoformat(timespec='seconds')}")
    print(f"  Mode: {'dry-run' if args.dry_run else 'live'}")

    if not check_three_week_gap(force=args.force):
        print("\nPipeline skipped — no action needed this week.")
        sys.exit(0)

    scripts_dir = Path(__file__).parent

    # Step 1: Scrape new draws
    scrape_args = ["--dry-run"] if args.dry_run else []
    run_step("Scrape new draws", scripts_dir / "scrape.py", scrape_args)

    # Step 2: Generate picks
    picks_args = ["--dry-run"] if args.dry_run else []
    run_step("Generate picks", scripts_dir / "generate_picks.py", picks_args)

    # Step 3: Send email
    email_args = ["--dry-run"] if args.dry_run else []
    run_step("Send email", scripts_dir / "email_picks.py", email_args)

    print("\n" + "=" * 50)
    print("  ✅  Pipeline complete!")
    print(f"  Finished at: {datetime.now().isoformat(timespec='seconds')}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
