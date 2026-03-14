#!/usr/bin/env python3
"""
run_all.py — Entry point: scrape → generate picks → email → log.

Runs the full pipeline every week (no gap check).

Usage:
    python scripts/run_all.py
    python scripts/run_all.py --dry-run   # Skip email, print picks
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


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
    args = parser.parse_args()

    print("\n" + "=" * 50)
    print("  🎱  Thursday Numbers — Automated Pipeline")
    print("=" * 50)
    print(f"  Started at: {datetime.now().isoformat(timespec='seconds')}")
    print(f"  Mode: {'dry-run' if args.dry_run else 'live'}")

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
