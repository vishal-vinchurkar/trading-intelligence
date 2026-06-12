#!/usr/bin/env bash
# Sovian daily cycle — refresh data, rescan, log signals, reconcile outcomes, notify.
# Idempotent: ledger record dedupes; reconcile only closes resolved trades.
# Backtests are NOT re-run here (slow, stable) — see scripts/weekly.sh.
set -euo pipefail
REPO="/Users/vishal.vinchurkar/Documents/claude-projects/projects/trading-intelligence"
cd "$REPO"
source .venv/bin/activate
export PYTHONPATH="$REPO"
LOG="logs/daily-$(date +%F).log"
{
  echo "=== Sovian daily $(date) ==="
  python -m data.backfill                 # refresh 10y cache (incl. today's bar)
  python -m quant.scan                    # regenerate scan.json (+ dashboard copy)
  python -m execution.ledger record       # log today's tradeable signals
  python -m execution.ledger reconcile    # resolve any closed trades
  python -m execution.telegram_push --send # push (no-op print if no token)
  echo "=== done $(date) ==="
} >> "$LOG" 2>&1
echo "daily cycle complete → $LOG"
