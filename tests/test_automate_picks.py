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


# ─── Login: proof of a session, not absence of a form ────────────────────────
#
# Oz Lotteries renders the email step and the password step as separate
# components, so the email field is already gone before Login is clicked. The
# old "logged in once the email field disappears" check therefore passed
# instantly, the next navigation raced the in-flight POST /login, and the cart
# was sometimes filled under a guest session — surfacing only at checkout as a
# second login prompt (2026-10-08). These fakes reproduce that: every element
# "exists" and every wait succeeds, except the header's logged-in variant.

from types import SimpleNamespace

from playwright.sync_api import TimeoutError as PlaywrightTimeout


class FakeLocator:
    def __init__(self, page, selector):
        self.page, self.selector = page, selector

    def wait_for(self, **kwargs):
        if self.selector == automate_picks.LOGGED_IN_MARKER and not self.page.logged_in:
            raise PlaywrightTimeout("header never showed a signed-in account")

    @property
    def first(self):
        return self

    def __getattr__(self, name):  # fill, click, select_option, nth, locator, ...
        return lambda *args, **kwargs: self


class FakePage:
    url = automate_picks.POWERBALL_URL

    def __init__(self, logged_in, session_survives_navigation=True):
        self.logged_in = logged_in
        self.session_survives_navigation = session_survives_navigation

    def locator(self, selector):
        return FakeLocator(self, selector)

    def get_by_role(self, *args, **kwargs):
        return FakeLocator(self, "role")

    def goto(self, url):
        if url == automate_picks.POWERBALL_URL and not self.session_survives_navigation:
            self.logged_in = False

    def __getattr__(self, name):  # wait_for_load_state, wait_for_function, ...
        return lambda *args, **kwargs: None


class FakeBrowser:
    def __init__(self, page):
        self.page, self.closed = page, False

    def new_context(self):
        return self

    def new_page(self):
        return self.page

    def close(self):
        self.closed = True


GAMES = [{"game": i + 1, "main": [1, 2, 3, 4, 5, 6, 7], "powerball": 1} for i in range(18)]


@pytest.fixture
def cart(monkeypatch):
    """Run run_automation against a fake page; record which games got filled."""
    monkeypatch.setenv("OZ_EMAIL", "test@example.com")
    monkeypatch.setenv("OZ_PASSWORD", "not-a-real-password")
    monkeypatch.setattr("builtins.input", lambda *args: "")
    filled = []
    monkeypatch.setattr(
        automate_picks, "select_numbers_for_game",
        lambda page, i, total, main, pb: filled.append(i),
    )

    def run(page):
        browser = FakeBrowser(page)
        playwright = SimpleNamespace(chromium=SimpleNamespace(launch=lambda **kw: browser))
        return automate_picks.run_automation(playwright, GAMES), filled, browser

    return run


def test_login_is_not_reported_when_the_session_never_appears(capsys):
    """Regression: the email field vanishing is not evidence of a login."""
    ok = automate_picks.do_login(FakePage(logged_in=False), "test@example.com", "x")

    assert ok is False
    assert "Logged in." not in capsys.readouterr().out


def test_login_is_reported_once_the_header_shows_an_account(capsys):
    ok = automate_picks.do_login(FakePage(logged_in=True), "test@example.com", "x")

    assert ok is True
    assert "Logged in." in capsys.readouterr().out


def test_fills_nothing_when_login_is_not_confirmed(cart, capsys):
    code, filled, browser = cart(FakePage(logged_in=False))

    assert code == 1
    assert filled == []
    assert browser.closed
    assert "not logged in" in capsys.readouterr().out.lower()


def test_fills_nothing_when_the_session_is_lost_loading_powerball(cart, capsys):
    code, filled, browser = cart(FakePage(logged_in=True, session_survives_navigation=False))

    assert code == 1
    assert filled == []
    assert "not logged in" in capsys.readouterr().out.lower()


def test_fills_every_game_when_logged_in(cart):
    """Guards the fakes: the two refusals above must be refusals, not crashes."""
    code, filled, _ = cart(FakePage(logged_in=True))

    assert code == 0
    assert filled == list(range(18))
