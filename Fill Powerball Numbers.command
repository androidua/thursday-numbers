#!/bin/bash
# =============================================================
#  Fill Powerball Numbers.command
#  Double-click this file in Finder on Thursday after receiving
#  the picks email. Chrome opens, logs in to Oz Lotteries, and
#  fills all 18 games. You review and pay in the browser.
#
#  This wrapper only *tries* to bring the checkout up to date.
#  Whether the numbers are actually today's emailed set is
#  enforced by scripts/automate_picks.py, which refuses to fill
#  anything else. Sync problems here are reported, never fatal —
#  the authoritative check is downstream, on the picks themselves.
# =============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

echo "==================================="
echo "  Oz Lotteries — Fill 18 Games"
echo "==================================="
echo ""

# A crashed git leaves .git/index.lock behind and every later pull dies with
# "Unable to create ... index.lock". The lock only means anything while a git
# process holds it, so an unowned one is debris. Left in place it silently
# freezes the checkout: on 2026-07-30 a lock from 10 days earlier had held this
# repo 5 commits back, and the automation filled the cart with locally
# regenerated numbers that matched no email.
lock_is_stale() {
    [ -f .git/index.lock ] || return 1
    # Age guard runs first: a lock younger than a minute may belong to a git
    # that is still working, even on a system where lsof is unavailable and so
    # reports no owner for everything.
    local now age
    now=$(date +%s)
    age=$(( now - $(stat -f %m .git/index.lock 2>/dev/null || echo "$now") ))
    [ "$age" -ge 60 ] || return 1
    ! lsof .git/index.lock >/dev/null 2>&1
}

sync_with_github() {
    local branch backup behind
    branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null)"

    if [ -z "$branch" ]; then
        echo "  Not a git checkout — skipping sync."
        return
    fi
    if [ "$branch" != "main" ]; then
        echo "  On branch '$branch', not main — skipping the pull."
        return
    fi

    if lock_is_stale; then
        echo "  Clearing stale .git/index.lock — no process holds it."
        rm -f .git/index.lock
    fi

    # picks_history.json is generated and committed by the email workflow, so a
    # local modification is always leftover from an earlier local run — and it
    # blocks the very merge that would bring today's picks in. Set it aside
    # instead of letting it wedge the sync.
    if ! git diff --quiet -- web/picks/picks_history.json 2>/dev/null; then
        backup="/tmp/picks_history.local-$(date +%Y%m%d-%H%M%S).json"
        cp web/picks/picks_history.json "$backup"
        git checkout -- web/picks/picks_history.json
        echo "  Local edits to picks_history.json set aside ($backup)."
    fi

    if ! git fetch --quiet origin; then
        echo "  Could not reach GitHub (offline?) — continuing with what is on disk."
        return
    fi

    if git merge --ff-only origin/main --quiet; then
        echo "  In sync with origin/main."
    else
        behind="$(git rev-list --count HEAD..origin/main 2>/dev/null || echo '?')"
        echo "  WARNING: could not fast-forward to origin/main ($behind commit(s) behind)."
        echo "           Local main has probably diverged. Inspect it with:"
        echo "               git -C \"$SCRIPT_DIR\" status"
    fi
}

echo "Syncing with GitHub (today's picks are committed there)..."
sync_with_github
echo ""

# Activate Python virtual environment if one exists in the project
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

python3 scripts/automate_picks.py "$@"
EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -ne 0 ]; then
    echo "Stopped without filling the cart (exit code $EXIT_CODE)."
    echo "Read the messages above — they say what to do next."
fi

echo "Press any key to close this window..."
read -r -n 1
