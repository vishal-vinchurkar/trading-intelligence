#!/usr/bin/env bash
# Sovian weekly — re-validate the edge (slow). Run e.g. Sunday.
set -euo pipefail
REPO="/Users/vishal.vinchurkar/Documents/claude-projects/projects/trading-intelligence"
cd "$REPO"; source .venv/bin/activate; export PYTHONPATH="$REPO"
LOG="logs/weekly-$(date +%F).log"
{ echo "=== weekly $(date) ==="; python -m quant.backtest_rules; python -m quant.portfolio; echo done; } >> "$LOG" 2>&1
echo "weekly re-validation complete → $LOG"
