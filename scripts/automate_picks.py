#!/usr/bin/env python3
"""
Oz Lotteries Powerball automation.

Reads the latest 18 picks from web/picks/picks_history.json, opens Chrome,
logs in to ozlotteries.com, selects "Pick your numbers" mode, fills all 18
games, and stops at the cart. You handle payment.

Usage:
    python scripts/automate_picks.py           # opens browser, fills games
    python scripts/automate_picks.py --dry-run  # prints games, no browser
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import Playwright, TimeoutError as PlaywrightTimeout, sync_playwright

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

PICKS_PATH = ROOT / "web" / "picks" / "picks_history.json"
LOGIN_URL = "https://www.ozlotteries.com/my-account"
POWERBALL_URL = "https://www.ozlotteries.com/powerball"
CART_URL = "https://www.ozlotteries.com/cart"
GAME_COUNT = "18"


def load_latest_picks():
    with open(PICKS_PATH) as f:
        history = json.load(f)
    if not history:
        print("ERROR: picks_history.json is empty.")
        sys.exit(1)

    latest = history[-1]
    age_days = (datetime.now() - datetime.fromisoformat(latest["generated_at"])).days
    if age_days >= 6:
        print(f"  Picks are {age_days} days old — generating fresh picks for today...")
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "generate_picks.py")],
            cwd=ROOT,
        )
        if result.returncode != 0:
            print("  WARNING: generate_picks.py failed. Proceeding with existing picks.")
        else:
            with open(PICKS_PATH) as f:
                history = json.load(f)
            latest = history[-1]
            print(f"  Fresh picks ready ({latest['generated_at'][:10]}).")

    return latest


def print_games(entry):
    print(f"  Generated : {entry['generated_at'][:10]}")
    print(f"  Draws used: {entry['draws_analysed']}")
    for g in entry["games"]:
        print(f"  Game {g['game']:2d}: main={g['main']}  pb={g['powerball']}")


def do_login(page, email, password):
    page.goto(LOGIN_URL)
    page.wait_for_load_state("networkidle")

    # Step 1: submit email; wait for the email-check API call to settle
    page.locator("#loginRegisterEmail_email").fill(email)
    page.locator('[data-id="loginRegisterEmail_submit"]').click()
    page.wait_for_load_state("networkidle")

    # Step 2: fill password using type selector (avoids React remount ID issues)
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


def select_numbers_for_game(page, game_index, main_balls, powerball):
    # Oz Lotteries lazy-renders: only the open game's picker exists in the DOM.
    # For game 0 it is already open on page load. For N > 0 we click the game row
    # header to open it, which unmounts the previous game's picker and mounts the new one.

    if game_index > 0:
        game_rows = page.locator('[data-id="gameNumberSelect_gameRow"]')
        game_rows.nth(game_index).scroll_into_view_if_needed()
        game_rows.nth(game_index).click()

    # Wait for the single lazy-rendered picker to mount (always exactly 1 when open).
    page.wait_for_function(
        "() => !!document.querySelector('[class*=\"NumberPickerWrapper\"]')",
        timeout=10_000,
    )

    if game_index == 0:
        # Show the 'for' attribute format and total label count so we can confirm
        # whether main-ball and PB grids share the same attribute format.
        sample = page.evaluate("""() => {
            const picker = document.querySelector('[class*="NumberPickerWrapper"]');
            if (!picker) return 'no-picker';
            const labels = Array.from(
                picker.querySelectorAll('label[data-id="numberGrids_numbers_numberItem"]')
            );
            const fmt = l => '"' + l.getAttribute('for') + '":' + l.textContent.trim();
            const first = labels.slice(0, 3).map(fmt).join('  ');
            const last  = labels.slice(-3).map(fmt).join('  ');
            return '(' + labels.length + ' labels)  first: ' + first + '  ...last: ' + last;
        }""")
        print(f"    [debug] labels: {sample}")

    def js_click(num, is_powerball=False):
        # querySelector always returns the single mounted picker.
        # For numbers 1-20: if both main and PB grids use for="N", there are 2 labels;
        # PB grid follows main in DOM, so labels[-1] is the PB label.
        label_expr = "labels[labels.length - 1]" if is_powerball else "labels[0]"
        result = page.evaluate(f"""
            (() => {{
                const picker = document.querySelector('[class*="NumberPickerWrapper"]');
                if (!picker) return 'no-picker';
                const labels = Array.from(
                    picker.querySelectorAll(
                        'label[data-id="numberGrids_numbers_numberItem"][for="{num}"]'
                    )
                );
                if (!labels.length) return 'no-label-{num}';
                {label_expr}.click();
                return 'ok:' + labels.length;
            }})()
        """)
        if not result.startswith("ok"):
            print(f"    [warn] js_click num={num} pb={is_powerball}: {result}")
        elif is_powerball and result == "ok:1":
            print(f"    [warn] PB {num}: only 1 label found — may need different PB selector")
        page.wait_for_timeout(150)

    for num in main_balls:
        js_click(num)

    js_click(powerball, is_powerball=True)


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
    page.wait_for_load_state("networkidle")

    # Switch to "Pick your numbers" mode (away from QuickPick default).
    page.locator('label[for="chooseNumbers_manualPickGames"]').click()
    page.wait_for_timeout(500)

    # Select 18 games.
    page.locator("#numberOfGamesSelect").select_option(GAME_COUNT)
    page.wait_for_timeout(800)

    # Dismiss any tooltip overlays before filling numbers.
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)

    print(f"\nFilling {len(games)} games...")
    for i, game in enumerate(games):
        print(f"  Game {i + 1:2d}/{len(games)}: {game['main']} + pb {game['powerball']}")
        try:
            select_numbers_for_game(page, i, game["main"], game["powerball"])
        except PlaywrightTimeout:
            print(f"  WARNING: Timeout opening game {i + 1}. The page may have changed.")
            print("           Check the browser and continue manually if needed.")

    print("\nAll games filled. Clicking Add to cart...")
    page.get_by_role("button", name="Add to cart").click()
    page.wait_for_url(f"**{CART_URL}**", timeout=15_000)

    print("\nDone. Browser is open at the cart. Review your games and complete payment.")
    input("Press Enter here to close the browser when you are finished...")
    browser.close()
    return 0


def main():
    parser = argparse.ArgumentParser(description="Auto-fill Oz Lotteries Powerball picks")
    parser.add_argument("--dry-run", action="store_true", help="Print games without opening browser")
    args = parser.parse_args()

    entry = load_latest_picks()
    games = entry["games"]

    print(f"\nLoaded {len(games)} games from picks_history.json:")
    print_games(entry)

    if args.dry_run:
        print("\n[dry-run] No browser opened.")
        return 0

    with sync_playwright() as playwright:
        return run_automation(playwright, games)


if __name__ == "__main__":
    sys.exit(main())
