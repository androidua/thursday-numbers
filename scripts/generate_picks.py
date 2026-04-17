#!/usr/bin/env python3
"""
generate_picks.py — Generate 18 Powerball games using EWMA-weighted frequency
analysis and greedy portfolio coverage. Saves results to picks history.

Statistical improvements over raw frequency counting:
  - EWMA scoring (α=0.03, half-life ≈23 draws / 6 months) replaces Counter.
    EWMA is stationary, interpretable, and better motivated than linear decay.
  - Chi-squared goodness-of-fit test against uniform distribution — attached
    to output so callers can see whether "hot" labels are statistically valid.
  - Two-phase game generation:
      Phase 1 (games 1–5): Weighted partition — all 35 main balls are sampled
        without replacement in EWMA-probability order, then split into 5 games
        of 7. Guarantees every main ball appears at least once in the batch.
      Phase 2 (games 6–18): EWMA-weighted sampling with pair-diversity
        rejection (no two games share more than 4 main balls).

Usage:
    python scripts/generate_picks.py
    python scripts/generate_picks.py --dry-run   # Print picks, don't save
"""

import argparse
import json
import math
import random
import sys
from datetime import datetime
from pathlib import Path

DATA_FILE  = Path(__file__).parent.parent / "web" / "data" / "powerball_draws.json"
PICKS_FILE = Path(__file__).parent.parent / "web" / "picks" / "picks_history.json"

NUM_GAMES         = 18
MAIN_BALLS        = 35
PB_BALLS          = 20
MAIN_PER_GAME     = 7
EWMA_ALPHA        = 0.03   # half-life = ln(0.5)/ln(1−α) ≈ 23 draws ≈ 6 months
GREEDY_PHASE_GAMES = 5     # games dedicated to full-coverage greedy phase

# Split-pot avoidance prior (v1.5.23). Multiplicative penalties applied to
# EWMA scores before sampling, biasing away from numbers humans overpick.
# Doesn't affect win probability (draws are random) but raises expected
# payout ~10–30% per win by reducing pot-split dilution.
#   • 1–31: down-weighted (date/birthday cluster)
#   • 7, 11: extra penalty (common "lucky" picks)
#   • 13: unchanged (underpicked due to unlucky superstition)
#   • 32–35: unchanged (beyond date range, already unpopular)
POPULARITY_PENALTY_MAIN = {b: 0.90 for b in range(1, 32)}
POPULARITY_PENALTY_MAIN[7]  = 0.85
POPULARITY_PENALTY_MAIN[11] = 0.85

POPULARITY_PENALTY_PB = {b: 0.95 for b in range(1, 21)}
POPULARITY_PENALTY_PB[7]  = 0.90
POPULARITY_PENALTY_PB[11] = 0.90


# ─── Data loading ────────────────────────────────────────────────────────────

def load_draws():
    with open(DATA_FILE) as f:
        all_draws = json.load(f)
    # Filter to current format: 7 main balls 1–35, PB 1–20 (Apr 2018+)
    return [d for d in all_draws if len(d["main"]) == 7]


# ─── EWMA scoring ────────────────────────────────────────────────────────────

def compute_ewma_scores(draws):
    """
    Compute EWMA scores for each ball using chronological draw history.

    Formula:  s_b[t] = α × 1[b ∈ draw_t] + (1−α) × s_b[t−1]
    Initial:  s_b[0] = MAIN_PER_GAME / MAIN_BALLS  (= expected base rate)

    α = 0.03 gives half-life ≈ 23 draws (~6 months at weekly cadence).
    Balls that appear more frequently in recent draws earn higher scores.
    Unlike linear decay, EWMA is stationary — the weight given to a draw
    k periods ago is always (1−α)^k, independent of total dataset size.

    Also accumulates raw counts for the chi-squared significance test.
    """
    alpha = EWMA_ALPHA

    # Initialise to expected base rate
    main_scores = {b: MAIN_PER_GAME / MAIN_BALLS for b in range(1, MAIN_BALLS + 1)}
    pb_scores   = {b: 1 / PB_BALLS               for b in range(1, PB_BALLS   + 1)}

    # Raw counts for chi-squared
    main_counts = {b: 0 for b in range(1, MAIN_BALLS + 1)}
    pb_counts   = {b: 0 for b in range(1, PB_BALLS   + 1)}

    for draw in draws:
        draw_set = set(draw["main"])
        for b in range(1, MAIN_BALLS + 1):
            appeared = 1 if b in draw_set else 0
            main_scores[b] = alpha * appeared + (1 - alpha) * main_scores[b]
            if appeared:
                main_counts[b] += 1

        pb = draw["powerball"]
        for b in range(1, PB_BALLS + 1):
            appeared = 1 if b == pb else 0
            pb_scores[b] = alpha * appeared + (1 - alpha) * pb_scores[b]
            if appeared:
                pb_counts[b] += 1

    # Split-pot avoidance: bias sampling away from overpicked numbers.
    # Raw counts (main_counts/pb_counts) are left untouched so the chi-squared
    # test still reports the true observed frequency distribution.
    for b in main_scores:
        main_scores[b] *= POPULARITY_PENALTY_MAIN.get(b, 1.0)
    for b in pb_scores:
        pb_scores[b] *= POPULARITY_PENALTY_PB.get(b, 1.0)

    return main_scores, pb_scores, main_counts, pb_counts


# ─── Chi-squared significance test ───────────────────────────────────────────

def chi_squared_test(obs, expected):
    """
    Pearson chi-squared goodness-of-fit test.
    Returns (statistic, p_value).  p_value is None if scipy is unavailable.
    """
    stat = sum((o - e) ** 2 / e for o, e in zip(obs, expected))
    try:
        from scipy.stats import chisquare
        _, p_value = chisquare(obs, f_exp=expected)
        return float(stat), float(p_value)
    except ImportError:
        return float(stat), None


def compute_chi_squared(counts, n_draws, pool_size, draws_per_ball):
    """Chi-squared test of observed ball frequencies against a uniform distribution."""
    expected_per_ball = n_draws * draws_per_ball / pool_size
    obs      = [counts[b] for b in range(1, pool_size + 1)]
    expected = [expected_per_ball] * pool_size
    return chi_squared_test(obs, expected)


# ─── Sampling helpers ────────────────────────────────────────────────────────

def weighted_sample(scores, n):
    """
    Sample n balls without replacement, probability proportional to EWMA scores.
    scores: dict {ball: weight}
    Returns a list of n ball numbers.
    """
    pool   = list(scores.items())   # [(ball, score), …]
    result = []
    while len(result) < n and pool:
        total = sum(s for _, s in pool)
        r = random.random() * total
        for i, (ball, score) in enumerate(pool):
            r -= score
            if r <= 0 or i == len(pool) - 1:
                result.append(ball)
                pool.pop(i)
                break
    return result


# ─── Game generation ─────────────────────────────────────────────────────────

def pair_diverse(candidate, existing_games, max_shared=4):
    """True if candidate shares ≤ max_shared balls with every existing game."""
    cset = set(candidate)
    for g in existing_games:
        if len(cset & set(g["main"])) > max_shared:
            return False
    return True


def generate_games(main_scores, pb_scores, n=NUM_GAMES):
    """
    Two-phase game generation with full main-ball and Powerball coverage.

    Powerball diversity (applied across all phases):
        Pre-sample n PBs without replacement using EWMA weights.  With n=18
        games and 20 possible PBs, this guarantees 18 distinct Powerballs —
        covering 90% of the PB pool every week.  The old approach drew from a
        fixed top-5 pool, repeating the same PBs 3–6 times and leaving 15 PBs
        with zero chance of appearing.

    Phase 1 — Greedy Coverage (games 1 to GREEDY_PHASE_GAMES):
        Sample all 35 main balls without replacement in EWMA-probability order,
        then partition into 5 consecutive games of 7.  This guarantees that
        every main ball appears at least once in the weekly batch, eliminating
        the coverage blind-spot of the old top-10-only approach.

    Phase 2 — Diverse Completion (remaining games):
        EWMA-weighted sampling from all 35 balls with pair-diversity rejection:
        any candidate that shares more than 4 balls with an existing game is
        discarded, preventing redundant near-duplicate picks.
    """
    games = []
    seen  = set()

    # ── Pre-sample diverse PBs (n unique PBs from 20, EWMA-weighted) ──────
    # n=18 < PB_BALLS=20, so sampling without replacement is always feasible.
    diverse_pbs = weighted_sample(pb_scores, n)

    # ── Phase 1: weighted full-coverage partition ──────────────────────────
    ordered = weighted_sample(main_scores, MAIN_BALLS)   # all 35, EWMA order
    covered = set()
    for i in range(GREEDY_PHASE_GAMES):
        main = tuple(sorted(ordered[i * MAIN_PER_GAME : (i + 1) * MAIN_PER_GAME]))
        covered.update(main)
        pb   = diverse_pbs[i]
        key  = (main, pb)
        seen.add(key)
        games.append({"game": i + 1, "main": list(main), "powerball": pb})

    print(f"  Phase 1 (coverage): all {len(covered)}/35 main balls covered in "
          f"{GREEDY_PHASE_GAMES} games")

    # ── Phase 2: diverse EWMA-weighted fill ───────────────────────────────
    pb_idx = GREEDY_PHASE_GAMES          # index into pre-sampled diverse_pbs
    max_attempts = (n - GREEDY_PHASE_GAMES) * 1000
    for _ in range(max_attempts):
        if len(games) >= n:
            break
        main = tuple(sorted(weighted_sample(main_scores, MAIN_PER_GAME)))
        pb   = diverse_pbs[pb_idx] if pb_idx < len(diverse_pbs) else weighted_sample(pb_scores, 1)[0]
        key  = (main, pb)
        if key not in seen and pair_diverse(main, games):
            seen.add(key)
            pb_idx += 1
            games.append({
                "game":      len(games) + 1,
                "main":      list(main),
                "powerball": pb,
            })

    if len(games) < n:
        raise RuntimeError(
            f"Could not generate {n} unique diverse games. Only produced {len(games)}."
        )

    distinct_pbs = len({g["powerball"] for g in games})
    print(f"  PB diversity    : {distinct_pbs}/{n} distinct Powerballs across {n} games")
    return games


# ─── Result assembly ─────────────────────────────────────────────────────────

def top_balls(scores, n):
    """Return top-n balls by score, sorted ascending."""
    return sorted(sorted(scores, key=scores.get, reverse=True)[:n])


def build_result(draws, games, main_scores, pb_scores,
                 chi2_main, p_main, chi2_pb, p_pb):
    first_date = draws[0]["date"]
    last_date  = draws[-1]["date"]
    return {
        "generated_at":    datetime.now().isoformat(timespec="seconds"),
        "draws_analysed":  len(draws),
        "data_range":      f"{first_date} to {last_date}",
        "ewma_alpha":      EWMA_ALPHA,
        "popularity_prior": "v1.5.23",
        "hot_main_balls":  top_balls(main_scores, 10),
        "hot_powerballs":  top_balls(pb_scores, 5),
        "freq_significant": p_main is not None and p_main < 0.05,
        "chi2_main":       round(chi2_main, 2),
        "chi2_main_p":     round(p_main, 4) if p_main is not None else None,
        "chi2_pb":         round(chi2_pb, 2),
        "chi2_pb_p":       round(p_pb, 4) if p_pb is not None else None,
        "games":           games,
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
    print(f"\n  Generated at  : {result['generated_at']}")
    print(f"  Draws used    : {result['draws_analysed']} ({result['data_range']})")
    print(f"  EWMA alpha    : {result['ewma_alpha']}  (half-life ≈23 draws / 6 months)")
    print(f"  Top main      : {result['hot_main_balls']}")
    print(f"  Top PBs       : {result['hot_powerballs']}")
    p = result.get("chi2_main_p")
    if p is not None:
        sig = "SIGNIFICANT" if result["freq_significant"] else "not significant (consistent with fair draw)"
        print(f"  Chi-squared   : χ²={result['chi2_main']}, p={p} — {sig}")
    print()
    for g in result["games"]:
        balls = "  ".join(f"{b:2d}" for b in g["main"])
        phase = "coverage" if g["game"] <= GREEDY_PHASE_GAMES else "diverse"
        print(f"  Game {g['game']:2d}:  [{balls}]  PB: {g['powerball']}  ({phase})")


# ─── Entry point ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate Powerball picks (EWMA scoring + greedy coverage)"
    )
    parser.add_argument("--dry-run", action="store_true", help="Don't save results")
    args = parser.parse_args()

    print("=== Powerball Pick Generator ===")
    draws = load_draws()
    if not draws:
        print("ERROR: No current-format draws found. Check that the data file exists and contains 7-ball draws.", file=sys.stderr)
        sys.exit(1)
    print(f"  Loaded {len(draws)} current-format draws (7-ball era, 2018+)")

    main_scores, pb_scores, main_counts, pb_counts = compute_ewma_scores(draws)

    chi2_main, p_main = compute_chi_squared(main_counts, len(draws), MAIN_BALLS, MAIN_PER_GAME)
    chi2_pb,   p_pb   = compute_chi_squared(pb_counts,   len(draws), PB_BALLS,   1)

    print(f"  Top main (EWMA) : {top_balls(main_scores, 10)}")
    print(f"  Top PBs  (EWMA) : {top_balls(pb_scores,  5)}")
    if p_main is not None:
        sig = "SIGNIFICANT" if p_main < 0.05 else "not significant (consistent with fair draw)"
        print(f"  Chi-squared     : χ²={chi2_main:.2f}, p={p_main:.4f} — {sig}")

    games  = generate_games(main_scores, pb_scores)
    result = build_result(draws, games, main_scores, pb_scores,
                          chi2_main, p_main, chi2_pb, p_pb)

    print_picks(result)

    if args.dry_run:
        print("\n  [dry-run] Skipping save.")
    else:
        save_result(result)

    print("=== Done ===")
    return result


if __name__ == "__main__":
    main()
