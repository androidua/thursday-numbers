import random

import generate_picks


def test_run_source_cron_under_github_actions(monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    assert generate_picks.run_source() == "cron"


def test_run_source_local_otherwise(monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    assert generate_picks.run_source() == "local"


def test_generated_games_satisfy_all_invariants():
    random.seed("invariant-test")
    draws = generate_picks.load_draws()
    main_scores, pb_scores, _, _ = generate_picks.compute_ewma_scores(draws)
    games = generate_picks.generate_games(main_scores, pb_scores)

    assert len(games) == 18
    keys = set()
    for g in games:
        assert len(g["main"]) == 7 and len(set(g["main"])) == 7
        assert all(1 <= b <= 35 for b in g["main"])
        assert 1 <= g["powerball"] <= 20
        keys.add((tuple(g["main"]), g["powerball"]))
    assert len(keys) == 18  # no duplicate games

    # Phase 1 (games 1-5) covers every main ball exactly once
    covered = [b for g in games[:5] for b in g["main"]]
    assert sorted(covered) == list(range(1, 36))

    # Pair diversity: no two games share more than 4 main balls
    for i in range(18):
        for j in range(i + 1, 18):
            shared = set(games[i]["main"]) & set(games[j]["main"])
            assert len(shared) <= 4, f"games {i+1} and {j+1} share {len(shared)} balls"
