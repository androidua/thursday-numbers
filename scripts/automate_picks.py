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
    # Game 1 (index 0) is pre-opened on page load — no accordion click needed.
    # For games 2–18 click the cells-container header to open this game's picker,
    # which closes the previous game's picker automatically (single-expand accordion).
    #
    # No explicit wait_for — Playwright's click() auto-waits for each label to be
    # visible, stable, and actionable before firing the event sequence.

    if game_index > 0:
        page.locator('[data-id="gameNumberSelect_gameRow"]').nth(game_index).locator(
            '[data-id="gameNumberSelect_gameRowCellsContainer"]'
        ).click()

    for num in main_balls:
        page.locator(
            f'label[data-id="numberGrids_numbers_numberItem"][for="{num}"]'
        ).click()
        page.wait_for_timeout(100)

    page.locator(
        f'[data-id="numberGrids_powerball_numberItem"][for="{powerball}"]'
    ).click()
    page.wait_for_timeout(100)


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
            select_numbers_for_game(page, i, game["main"], game["powerball"])
        except PlaywrightTimeout:
            print(f"  WARNING: Timeout opening game {i + 1}. The page may have changed.")
            print("           Check the browser and continue manually if needed.")

    print("\nAll games filled. Clicking Add to cart...")
    # Use data-id to avoid ambiguity with a second "Add to cart" button on the page.
    page.locator('[data-id="addToCart_button"]').click()
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
