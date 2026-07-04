from datetime import date

import check_data


def d(num, iso, main=None, pb=9):
    return {"draw": num, "date": iso, "main": main or [1, 2, 3, 4, 5, 6, 7], "powerball": pb}


CLEAN = [d(1570, "2026-06-18"), d(1571, "2026-06-25"), d(1572, "2026-07-02")]


def test_clean_data_has_no_problems():
    assert check_data.validate_integrity(CLEAN) == []


def test_numbering_gap_is_detected():
    problems = check_data.validate_integrity([d(1570, "2026-06-18"), d(1572, "2026-07-02")])
    assert any("numbering gap" in p for p in problems)


def test_non_ascending_dates_detected():
    problems = check_data.validate_integrity([d(1570, "2026-06-25"), d(1571, "2026-06-18")])
    assert any("ascending" in p for p in problems)


def test_invalid_balls_detected():
    problems = check_data.validate_integrity([d(1570, "2026-06-18", main=[1, 2, 3, 4, 5, 6, 36])])
    assert any("invalid main balls" in p for p in problems)
    problems = check_data.validate_integrity([d(1570, "2026-06-18", pb=21)])
    assert any("invalid powerball" in p for p in problems)


def test_empty_data_is_a_problem():
    assert check_data.validate_integrity([]) == ["data file is empty"]


def test_freshness_ok_when_newest_is_expected_thursday():
    fresh, newest, expected = check_data.check_freshness(CLEAN, today=date(2026, 7, 4))  # Saturday
    assert fresh and newest == date(2026, 7, 2) and expected == date(2026, 7, 2)


def test_freshness_fails_when_a_thursday_is_missing():
    stale = CLEAN[:-1]  # newest is 2026-06-25, but 2026-07-02 was expected
    fresh, newest, expected = check_data.check_freshness(stale, today=date(2026, 7, 4))
    assert not fresh and expected == date(2026, 7, 2)
