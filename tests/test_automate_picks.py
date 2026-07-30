"""Guards on the picks the cart-fill automation is allowed to use.

The whole point of automate_picks.py is to buy the numbers the Thursday email
delivered. generate_picks.py seeds itself on "<date>-<draw count>", so a
checkout even one draw behind produces a completely different 18-game
portfolio for the same date. That makes "regenerate locally when picks look
stale" a silent wrong-numbers bug, not a convenience — see the 2026-07-30
incident encoded in test_rejects_the_2026_07_30_incident_entry below.
"""

import json
from datetime import date

import pytest

import automate_picks


TODAY = date(2026, 7, 30)


def entry(generated_at, source="cron", **extra):
    e = {
        "generated_at": generated_at,
        "source": source,
        "draws_analysed": 432,
        "data_range": "2018-04-19 to 2026-07-23",
        "seed": "2026-07-30-432",
        "games": [{"game": 1, "main": [9, 13, 17, 19, 25, 32, 34], "powerball": 14}],
    }
    e.update(extra)
    return e


# ─── The gate ────────────────────────────────────────────────────────────────

def test_accepts_todays_cron_picks():
    assert automate_picks.picks_rejection_reason(
        entry("2026-07-30T01:53:06", source="cron"), TODAY
    ) is None


def test_rejects_picks_generated_locally_even_when_dated_today():
    reason = automate_picks.picks_rejection_reason(
        entry("2026-07-30T16:10:52", source="local"), TODAY
    )
    assert reason is not None
    assert "local" in reason.lower()


def test_rejects_last_weeks_cron_picks():
    reason = automate_picks.picks_rejection_reason(
        entry("2026-07-23T01:51:12", source="cron"), TODAY
    )
    assert reason is not None
    assert "2026-07-23" in reason


def test_rejects_entry_with_unknown_provenance():
    stale = entry("2026-07-30T01:53:06")
    del stale["source"]
    assert automate_picks.picks_rejection_reason(stale, TODAY) is not None


def test_rejects_entry_missing_generated_at_without_crashing():
    broken = entry("2026-07-30T01:53:06")
    del broken["generated_at"]
    assert automate_picks.picks_rejection_reason(broken, TODAY) is not None


def test_rejects_the_2026_07_30_incident_entry():
    """Regression: the exact entry that got filled into the cart by mistake.

    Dated the right day, but generated locally off a checkout stuck 2 draws
    behind (seed ...-430 instead of ...-432), so every one of the 18 games
    differed from the emailed set.
    """
    incident = {
        "generated_at": "2026-07-30T16:10:52",
        "draws_analysed": 430,
        "data_range": "2018-04-19 to 2026-07-09",
        "seed": "2026-07-30-430",
        "source": "local",
        "games": [{"game": 1, "main": [3, 10, 12, 25, 27, 29, 30], "powerball": 5}],
    }
    assert automate_picks.picks_rejection_reason(incident, TODAY) is not None


# ─── load_latest_picks: refuse rather than manufacture ────────────────────────

@pytest.fixture
def picks_file(tmp_path, monkeypatch):
    path = tmp_path / "picks_history.json"
    monkeypatch.setattr(automate_picks, "PICKS_PATH", path)
    return path


def write(path, entries):
    path.write_text(json.dumps(entries, indent=2))


def test_load_latest_picks_returns_todays_cron_entry(picks_file, monkeypatch):
    monkeypatch.setattr(automate_picks, "today", lambda: TODAY)
    write(picks_file, [entry("2026-07-30T01:53:06", source="cron")])

    assert automate_picks.load_latest_picks()["seed"] == "2026-07-30-432"


def test_load_latest_picks_aborts_on_stale_picks(picks_file, monkeypatch, capsys):
    monkeypatch.setattr(automate_picks, "today", lambda: TODAY)
    monkeypatch.setattr(automate_picks, "commits_behind_origin", lambda: 5)
    write(picks_file, [entry("2026-07-16T01:52:41", source="cron")])

    with pytest.raises(SystemExit) as exc:
        automate_picks.load_latest_picks()

    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "5 commit" in out          # tells the user why the checkout is behind
    assert "git pull" in out          # and how to fix it


def test_load_latest_picks_never_shells_out_to_generate_picks(picks_file, monkeypatch):
    """The silent-regeneration path must not exist in any form."""
    calls = []

    def record(cmd, *a, **kw):
        calls.append(cmd)
        raise AssertionError(f"unexpected subprocess call: {cmd}")

    monkeypatch.setattr(automate_picks, "today", lambda: TODAY)
    monkeypatch.setattr(automate_picks, "commits_behind_origin", lambda: None)
    monkeypatch.setattr(automate_picks.subprocess, "run", record)
    write(picks_file, [entry("2026-07-09T01:50:02", source="cron")])

    with pytest.raises(SystemExit):
        automate_picks.load_latest_picks()

    assert not any("generate_picks" in str(c) for c in calls)


def test_allow_stale_bypasses_the_gate(picks_file, monkeypatch, capsys):
    monkeypatch.setattr(automate_picks, "today", lambda: TODAY)
    write(picks_file, [entry("2026-07-16T01:52:41", source="cron")])

    picked = automate_picks.load_latest_picks(allow_stale=True)

    assert picked["generated_at"] == "2026-07-16T01:52:41"
    assert "not today" in capsys.readouterr().out.lower()


def test_empty_history_aborts(picks_file, monkeypatch):
    monkeypatch.setattr(automate_picks, "today", lambda: TODAY)
    write(picks_file, [])

    with pytest.raises(SystemExit):
        automate_picks.load_latest_picks()
