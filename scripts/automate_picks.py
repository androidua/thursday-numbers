#!/usr/bin/env python3
"""
Oz Lotteries Powerball automation.

Reads the latest 18 picks from web/picks/picks_history.json, opens Chrome,
logs in to ozlotteries.com, selects "Pick your numbers" mode, fills all 18
games, and stops at the cart. You handle payment.

This script is a pure consumer: it fills the cart with the numbers the
Thursday email delivered, or it stops. It never generates numbers of its own.

Usage:
    python scripts/automate_picks.py               # opens browser, fills games
    python scripts/automate_picks.py --dry-run     # prints games, no browser
    python scripts/automate_picks.py --allow-stale # fill picks that aren't today's email
"""

import argparse
import json
import os
import subprocess
import sys
import textwrap
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import (
    Error as PlaywrightError,
    Playwright,
    TimeoutError as PlaywrightTimeout,
    sync_playwright,
)

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

PICKS_PATH = ROOT / "web" / "picks" / "picks_history.json"
LOGIN_URL = "https://www.ozlotteries.com/my-account"
POWERBALL_URL = "https://www.ozlotteries.com/powerball"
GAME_COUNT = "18"


def today():
    """Indirection so tests can pin the date."""
    return date.today()


def picks_rejection_reason(entry, on_date):
    """Why `entry` must not be filled into the cart, or None if it's the real thing.

    Two conditions, both required:

    * Dated today. email-picks.yml generates and commits Thursday's picks at
      00:00 UTC (10am AEST) on the morning of the draw, so anything older
      belongs to a draw that has already been drawn.
    * source "cron" — proof the entry came from the GitHub Actions run that
      actually sent the email. A "local" entry is a *different* portfolio even
      when it carries today's date: generate_picks.py seeds on
      "<date>-<draw count>", so a checkout that is behind on draws produces a
      different seed and therefore 18 entirely different games.

    Both halves are load-bearing. On 2026-07-30 a stale .git/index.lock had
    frozen the checkout 2 draws back; the old code saw picks "14 days old",
    regenerated locally off 430 draws instead of 432, and filled the cart with
    numbers that appeared in no email.
    """
    generated_on = (entry.get("generated_at") or "")[:10]
    if generated_on != on_date.isoformat():
        return (f"the newest saved picks are dated {generated_on or 'unknown'}, "
                f"not today ({on_date.isoformat()})")
    if entry.get("source") != "cron":
        return (f"the newest saved picks are dated today but were generated "
                f"locally (source: {entry.get('source') or 'unknown'}), so they are "
                f"not the numbers the email delivered")
    return None


def commits_behind_origin():
    """How many commits origin/main is ahead of this checkout, or None if git can't say.

    Called only on the abort path, to convert a bare "wrong numbers" into the
    one fact that explains it. Failure to answer is not itself an error.
    """
    try:
        subprocess.run(
            ["git", "fetch", "--quiet", "origin", "main"],
            cwd=ROOT, timeout=30, check=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        out = subprocess.run(
            ["git", "rev-list", "--count", "HEAD..origin/main"],
            cwd=ROOT, timeout=15, check=True, capture_output=True, text=True,
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return None
    return int(out) if out.isdigit() else None


def analysis_line(entry):
    """The picks email's own header line, so it can be eyeballed against the inbox."""
    return (f"{entry.get('draws_analysed', '?')} draws "
            f"({entry.get('data_range', 'unknown range')})")


def refuse_stale_picks(entry, reason):
    print("")
    print("=" * 70)
    print("  STOPPED — these are not today's emailed numbers")
    print("=" * 70)
    print("")
    # Wrapped: this window is a double-clicked Terminal at its default width.
    print(textwrap.fill(f"{reason}.", width=68,
                        initial_indent="  Reason: ", subsequent_indent="          "))
    print("")
    print(f"  On disk: {analysis_line(entry)}")
    print(f"           generated {entry.get('generated_at', '?')}, "
          f"seed {entry.get('seed', '?')}, source {entry.get('source', '?')}")

    behind = commits_behind_origin()
    if behind:
        print("")
        print(f"  This checkout is {behind} commit(s) behind origin/main. Today's picks")
        print("  were committed there by the email workflow and have not arrived yet.")
    elif behind == 0:
        print("")
        print("  This checkout is level with origin/main, so the email workflow itself")
        print("  may not have run. Check the Actions tab for email-picks.yml.")

    print("")
    print("  Filling the cart now would buy numbers that match no email, so nothing")
    print("  has been filled. To get today's numbers:")
    print("")
    print(f'      cd "{ROOT}"')
    print("      git pull --ff-only origin main")
    print(f'      "{ROOT}/Fill Powerball Numbers.command"')
    print("")
    print("  If you really do want fresh locally-generated numbers (they will NOT")
    print("  match any email, and score_history.py will not score them):")
    print("")
    print("      python3 scripts/generate_picks.py")
    print("      python3 scripts/automate_picks.py --allow-stale")
    print("")
    sys.exit(1)


def load_latest_picks(allow_stale=False):
    with open(PICKS_PATH) as f:
        history = json.load(f)
    if not history:
        print("ERROR: picks_history.json is empty — nothing to fill.")
        sys.exit(1)

    latest = history[-1]
    reason = picks_rejection_reason(latest, today())
    if reason is None:
        return latest

    if allow_stale:
        print(f"  --allow-stale: {reason}.")
        print("  Filling them anyway, as you asked. Check them against your email.")
        return latest

    refuse_stale_picks(latest, reason)


def print_games(entry):
    print(f"  Generated : {entry['generated_at'][:10]} (source: {entry.get('source', '?')})")
    print(f"  Analysis  : {analysis_line(entry)}")
    print("              ^ must match the 'Analysis based on ...' line in your email")
    for g in entry["games"]:
        print(f"  Game {g['game']:2d}: main={g['main']}  pb={g['powerball']}")


def do_login(page, email, password):
    page.goto(LOGIN_URL)
    page.wait_for_load_state("domcontentloaded")

    # Step 1: submit email; wait for the password field to appear (condition-based,
    # not networkidle — the page keeps background requests open so it never idles).
    page.locator("#loginRegisterEmail_email").fill(email)
    page.locator('[data-id="loginRegisterEmail_submit"]').click()

    # Step 2: fill password using type selector (avoids React remount ID issues)
    page.locator('input[type="password"]').wait_for(state="visible", timeout=20_000)
    page.locator('input[type="password"]').fill(password)
    page.get_by_role("button", name="Login", exact=True).click()

    # Wait until the login form disappears (redirected away or account loaded)
    try:
        page.wait_for_function(
            "!document.querySelector('#loginRegisterEmail_email')",
            timeout=20_000,
        )
        print("  Logged in.")
    except PlaywrightTimeout:
        print("WARNING: Login may have failed or is taking too long. Check the browser.")


def select_numbers_for_game(page, game_index, total_games, main_balls, powerball):
    # Target the hidden <input> directly, not label[for=N]. The page emits
    # two <input id="N"> per N in 1..20 (one in the main grid, one in the PB
    # grid); HTML for/id resolution hits the first, so PB labels for 1..20
    # toggle the MAIN grid's input instead of the PB input. The data-id
    # "numberGrids_<type>_hiddenCheckbox" uniquely scopes each grid.
    #
    # dispatch_event("click") fires a real DOM click that React's onChange
    # handler responds to, while bypassing Playwright's actionability checks.
    # That sidesteps two occluders: the absolute-positioned hidden input
    # sitting on top of its own label, and the sticky lotterySubNavigation
    # bar that covers the top ~114px of the viewport.
    #
    # Scope all selectors to this game's row. During the page's slide
    # animation the previous game's picker can briefly stay mounted while
    # the new one is rendered, which causes input[id="N"] to resolve to
    # two elements and trips Playwright's strict-mode check.
    game_row = page.locator('[data-id="gameNumberSelect_gameRow"]').nth(game_index)

    for num in main_balls:
        game_row.locator(
            f'input[data-id="numberGrids_numbers_hiddenCheckbox"][id="{num}"]'
        ).dispatch_event("click")

    game_row.locator(
        f'input[data-id="numberGrids_powerball_hiddenCheckbox"][id="{powerball}"]'
    ).dispatch_event("click")

    # After the PB click the page auto-advances: the current game's picker
    # collapses and the next game's picker opens. Wait for that next picker
    # to render before the caller moves on. Skip after the last game.
    if game_index < total_games - 1:
        page.locator('[data-id="gameNumberSelect_gameRow"]').nth(game_index + 1).locator(
            '[data-id="numberGrids_numbers_numberItem"]'
        ).first.wait_for(state="visible", timeout=5_000)


def run_automation(playwright: Playwright, games: list):
    browser = playwright.chromium.launch(headless=False, slow_mo=250)
    context = browser.new_context()
    page = context.new_page()

    email = os.environ.get("OZ_EMAIL", "")
    password = os.environ.get("OZ_PASSWORD", "")
    if not email or not password:
        print("\nERROR: OZ_EMAIL and OZ_PASSWORD must be set in .env at the project root.")
        print("       Copy .env.example to .env and fill in your Oz Lotteries credentials.")
        browser.close()
        return 1

    print("\nLogging in...")
    do_login(page, email, password)

    print("Navigating to Powerball...")
    page.goto(POWERBALL_URL)
    # Use domcontentloaded, not networkidle: the Powerball page runs continuous
    # background requests (live jackpot poll, analytics), so it never reaches a
    # 500ms network-idle window and networkidle times out at 30s. Rely on the
    # condition-based waits below (visible manual-pick label + game rows) instead.
    page.wait_for_load_state("domcontentloaded")

    # Switch to "Pick your numbers" mode (away from QuickPick default).
    page.locator('label[for="chooseNumbers_manualPickGames"]').wait_for(
        state="visible", timeout=20_000
    )
    page.locator('label[for="chooseNumbers_manualPickGames"]').click()
    page.wait_for_timeout(500)

    # Select 18 games; wait until all rows are rendered (condition-based, not a fixed timeout).
    page.locator("#numberOfGamesSelect").select_option(GAME_COUNT)
    page.locator('[data-id="gameNumberSelect_gameRow"]').nth(17).wait_for(
        state="visible", timeout=20_000
    )

    # Dismiss the "Play favourite numbers" tooltip — it overlays the number picker
    # and causes Playwright's occlusion check to block label clicks for game 1.
    # Escape is unreliable; click the X button on the tooltip directly.
    try:
        page.locator('[data-id="tooltipInfo_root"] button[type="button"]').click(timeout=3_000)
        page.wait_for_timeout(200)
    except PlaywrightTimeout:
        pass  # No tooltip visible, continue

    print(f"\nFilling {len(games)} games...")
    for i, game in enumerate(games):
        print(f"  Game {i + 1:2d}/{len(games)}: {game['main']} + pb {game['powerball']}")
        try:
            select_numbers_for_game(page, i, len(games), game["main"], game["powerball"])
        except PlaywrightTimeout:
            print(f"  WARNING: Timeout on game {i + 1}. The page may have changed.")
            print("           Check the browser and continue manually if needed.")

    print("\nAll games filled. Clicking Add to cart...")
    # Use data-id to avoid ambiguity with a second "Add to cart" button on the page.
    page.locator('[data-id="addToCart_button"]').click()

    # Let the navigation settle. Don't enforce a specific URL — oz lotteries
    # may route through /cart, /cart/checkout, or a transitional page. Crashing
    # here would close the browser context and erase the filled cart.
    try:
        page.wait_for_load_state("domcontentloaded", timeout=15_000)
        page.wait_for_timeout(1_500)
    except PlaywrightTimeout:
        pass

    print(f"\nDone. Browser is at: {page.url}")
    print("Review your games and complete payment.")
    input("Press Enter here to close the browser when you are finished...")
    browser.close()
    return 0


def browser_was_closed(exc):
    """True when a Playwright error is just the user shutting the browser window.

    Matched on the message rather than the TargetClosedError class: that class
    lives in playwright._impl and is not re-exported from playwright.sync_api,
    but it subclasses the public Error and carries a stable message.
    """
    return "has been closed" in str(exc).lower()


def main():
    parser = argparse.ArgumentParser(description="Auto-fill Oz Lotteries Powerball picks")
    parser.add_argument("--dry-run", action="store_true", help="Print games without opening browser")
    parser.add_argument(
        "--allow-stale", action="store_true",
        help="Fill picks that are not today's emailed set (they will not match your email)",
    )
    args = parser.parse_args()

    entry = load_latest_picks(allow_stale=args.allow_stale)
    games = entry["games"]

    print(f"\nLoaded {len(games)} games from picks_history.json:")
    print_games(entry)

    if args.dry_run:
        print("\n[dry-run] No browser opened.")
        return 0

    with sync_playwright() as playwright:
        try:
            return run_automation(playwright, games)
        except PlaywrightError as exc:
            # Anything other than a closed browser is a real automation bug —
            # let the traceback through, it is the only lead for a DOM change.
            if not browser_was_closed(exc):
                raise
            print("\nThe browser was closed before the cart was submitted.")
            print("Nothing was purchased. Re-run when you're ready to finish.")
            return 1


if __name__ == "__main__":
    sys.exit(main())
