#!/usr/bin/env python3
"""
generate_picks.py — Generate 18 hot-number Powerball games and save to picks history.

Usage:
    python scripts/generate_picks.py
    python scripts/generate_picks.py --dry-run   # Print picks, don't save
"""

import argparse
import json
import random
from collections import Counter
from datetime import datetime
from pathlib import Path

DATA_FILE = Path(__file__).parent.parent / "web" / "data" / "powerball_draws.json"
PICKS_FILE = Path(__file__).parent.parent / "web" / "picks" / "picks_history.json"

NUM_GAMES = 18
HOT_MAIN_COUNT = 10
HOT_PB_COUNT = 5
MAIN_PER_GAME = 7


def load_draws():
    with open(DATA_FILE) as f:
        return json.load(f)


def compute_frequencies(draws):
    main_counter = Counter()
    pb_counter = Counter()
    for draw in draws:
        for ball in draw["main"]:
            main_counter[ball] += 1
        pb_counter[draw["powerball"]] += 1
    return main_counter, pb_counter


def hot_numbers(counter, n):
    """Return the top-n most frequent numbers as a sorted list."""
    return sorted(ball for ball, _ in counter.most_common(n))


def generate_games(hot_main, hot_pb, n=NUM_GAMES):
    """Generate n unique games from the hot pools."""
    games = []
    seen = set()
    max_attempts = n * 1000

    for _ in range(max_attempts):
        if len(games) >= n:
            break
        main = tuple(sorted(random.sample(hot_main, MAIN_PER_GAME)))
        pb = random.choice(hot_pb)
        key = (main, pb)
        if key not in seen:
            seen.add(key)
            games.append({"game": len(games) + 1, "main": list(main), "powerball": pb})

    if len(games) < n:
        raise RuntimeError(
            f"Could not generate {n} unique games from pool of {len(hot_main)} hot balls. "
            f"Only produced {len(games)}."
        )
    return games


def build_result(draws, games, hot_main, hot_pb):
    first_date = draws[0]["date"]
    last_date = draws[-1]["date"]
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "draws_analysed": len(draws),
        "data_range": f"{first_date} to {last_date}",
        "hot_main_balls": hot_main,
        "hot_powerballs": hot_pb,
        "games": games,
    }


def save_result(result):
    PICKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    history = []
    if PICKS_FILE.exists():
        with open(PICKS_FILE) as f:
            history = json.load(f)
    history.append(result)
    with open(PICKS_FILE, "w") as f:
        json.dump(history, f, indent=2)
    print(f"  Saved to {PICKS_FILE} ({len(history)} total run(s))")


def print_picks(result):
    print(f"\n  Generated at : {result['generated_at']}")
    print(f"  Draws used   : {result['draws_analysed']} ({result['data_range']})")
    print(f"  Hot main     : {result['hot_main_balls']}")
    print(f"  Hot PBs      : {result['hot_powerballs']}")
    print()
    for g in result["games"]:
        balls = "  ".join(f"{b:2d}" for b in g["main"])
        print(f"  Game {g['game']:2d}:  [{balls}]  PB: {g['powerball']}")


def main():
    parser = argparse.ArgumentParser(description="Generate hot-number Powerball picks")
    parser.add_argument("--dry-run", action="store_true", help="Don't save results")
    args = parser.parse_args()

    print("=== Powerball Pick Generator ===")
    draws = load_draws()
    print(f"  Loaded {len(draws)} draws")

    main_counter, pb_counter = compute_frequencies(draws)
    hot_main = hot_numbers(main_counter, HOT_MAIN_COUNT)
    hot_pb = hot_numbers(pb_counter, HOT_PB_COUNT)
    print(f"  Hot main balls : {hot_main}")
    print(f"  Hot Powerballs : {hot_pb}")

    games = generate_games(hot_main, hot_pb)
    result = build_result(draws, games, hot_main, hot_pb)

    print_picks(result)

    if args.dry_run:
        print("\n  [dry-run] Skipping save.")
    else:
        save_result(result)

    print("=== Done ===")
    return result


if __name__ == "__main__":
    main()
