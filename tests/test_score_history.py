import score_history


# ── division mapping ─────────────────────────────────────────────────────────

def test_division_table_matches_official_rules():
    assert score_history.division_for(7, True) == "1"
    assert score_history.division_for(7, False) == "2"
    assert score_history.division_for(6, True) == "3"
    assert score_history.division_for(6, False) == "4"
    assert score_history.division_for(5, True) == "5"
    assert score_history.division_for(4, True) == "6"
    assert score_history.division_for(5, False) == "7"
    assert score_history.division_for(3, True) == "8"
    assert score_history.division_for(2, True) == "9"
    assert score_history.division_for(2, False) is None
    assert score_history.division_for(0, True) is None


# ── source-aware email-run detection ─────────────────────────────────────────

def test_source_field_wins_over_weekday():
    # Thursday-dated but explicitly local: must NOT count as an email run
    assert not score_history.is_email_run(
        {"generated_at": "2026-07-02T09:00:00", "source": "local"})
    assert score_history.is_email_run(
        {"generated_at": "2026-07-02T02:43:00", "source": "cron"})


def test_legacy_entries_fall_back_to_weekday_heuristic():
    assert score_history.is_email_run({"generated_at": "2026-07-02T02:43:00"})   # Thursday
    assert not score_history.is_email_run({"generated_at": "2026-03-15T10:00:00"})  # Sunday


# ── same-draw double-count guard ─────────────────────────────────────────────

def entry(ts, source="cron"):
    return {"generated_at": ts, "source": source,
            "games": [{"game": 1, "main": [1, 2, 3, 4, 5, 6, 7], "powerball": 9}]}


DRAWS = [{"draw": 1572, "date": "2026-07-02", "main": [6, 12, 17, 22, 24, 30, 32], "powerball": 2}]


def test_second_entry_for_same_draw_is_skipped():
    sb = score_history.build_scoreboard(
        [entry("2026-07-02T02:43:00"), entry("2026-07-02T09:00:00")], DRAWS)
    assert sb["weeks_scored"] == 1
    assert sb["skipped_duplicate_draw"] == ["2026-07-02T09:00:00"]
