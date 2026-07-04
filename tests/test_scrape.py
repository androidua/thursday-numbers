from datetime import date

import scrape


def li(classes, n):
    return f'<li class="{classes}">{n}</li>'


def page(mains, pb):
    lis = "".join(li("ball medium pb ball", n) for n in mains)
    if pb is not None:
        lis += li("ball medium pb powerball", pb)
    return f"<html><body><ul>{lis}</ul></body></html>"


def test_parse_valid_page():
    html = page([33, 4, 13, 25, 9, 5, 32], 7)
    assert scrape.parse_draw_page(html) == ([4, 5, 9, 13, 25, 32, 33], 7)


def test_parse_missing_powerball_returns_none():
    assert scrape.parse_draw_page(page([1, 2, 3, 4, 5, 6, 7], None)) is None


def test_parse_wrong_ball_count_returns_none():
    assert scrape.parse_draw_page(page([1, 2, 3, 4, 5, 6], 7)) is None


def test_parse_duplicate_main_ball_returns_none():
    assert scrape.parse_draw_page(page([1, 2, 3, 4, 5, 6, 6], 7)) is None


def test_parse_out_of_range_returns_none():
    assert scrape.parse_draw_page(page([1, 2, 3, 4, 5, 6, 36], 7)) is None
    assert scrape.parse_draw_page(page([1, 2, 3, 4, 5, 6, 7], 21)) is None


THURSDAYS = [date(2026, 6, 11), date(2026, 6, 18), date(2026, 6, 25)]


def test_collect_all_success_numbers_consecutively():
    fetch = lambda d: ([1, 2, 3, 4, 5, 6, 7], 9)
    new, failed = scrape.collect_new_draws(THURSDAYS, 1568, fetch)
    assert failed is None
    assert [d["draw"] for d in new] == [1569, 1570, 1571]
    assert [d["date"] for d in new] == ["2026-06-11", "2026-06-18", "2026-06-25"]


def test_collect_stops_at_first_failure():
    def fetch(d):
        if d == date(2026, 6, 18):
            return None                       # middle Thursday fails
        return ([1, 2, 3, 4, 5, 6, 7], 9)

    new, failed = scrape.collect_new_draws(THURSDAYS, 1568, fetch)
    assert failed == date(2026, 6, 18)
    # Only the draw BEFORE the failure is kept — never the one after,
    # which would otherwise be misnumbered and orphan the failed date.
    assert [d["draw"] for d in new] == [1569]
