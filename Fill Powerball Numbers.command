#!/bin/bash
# =============================================================
#  Fill Powerball Numbers.command
#  Double-click this file in Finder on Thursday after receiving
#  the picks email. Chrome opens, logs in to Oz Lotteries, and
#  fills all 18 games. You review and pay in the browser.
# =============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "==================================="
echo "  Oz Lotteries — Fill 18 Games"
echo "==================================="
echo ""

# Activate Python virtual environment if one exists in the project
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

python3 scripts/automate_picks.py
EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -ne 0 ]; then
    echo "Something went wrong (exit code $EXIT_CODE)."
    echo "Check the messages above for details."
fi

echo "Press any key to close this window..."
read -r -n 1
