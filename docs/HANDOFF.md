# HANDOFF — Sovian / trading-intelligence (resume from a fresh session)

Single source of truth for picking up cold. Read this + `reference/competitor-n8n-daytrader.md` and you're current.

## What this is
A personal **real-money** quant signal tool (not a demo) for US + India equities.
Deterministic conviction score → backtested → trade construct → dashboard, with a
forward paper-trading ledger as the unbiased validator.
- **Live:** https://sovian-trading.vercel.app (Vercel team `sovian-projects`)
- **Repo:** github.com/vishal-vinchurkar/trading-intelligence (push via `gh`-auth'd https)
- **Owner priority (stated):** trust/validation FIRST (paper-trade before real capital), then everything else.

## Architecture map
| Area | Files | Notes |
|---|---|---|
| Universe | `data/universe.py` | 21 US + 12 India + benchmarks (SPY, ^NSEI) |
| History | `data/backfill.py` → `data/cache/*.csv` | 10y daily, yfinance (free), cache gitignored |
| Indicators | `indicators/technical.py` | RSI/MACD/SMA/Bollinger/ATR/realised-vol/expected-move/swing-pivot S/R |
| Quant score | `quant/score.py` | deterministic 0–100, price-only (so backtestable) |
| Backtests | `quant/backtest.py` (hold-to-horizon), `quant/backtest_rules.py` (exact trade), `quant/portfolio.py` (equity curve) | all net-of-cost, OOS |
| Trade construct | `quant/trade.py` | entry / 2×ATR stop / swing target / R:R gate 1.5 |
| Scan | `quant/scan.py` → `quant/latest_scan.json` + `dashboard/data/scan.json` | ranks universe, attaches calibration + tradeable flag + 120d price history |
| Forward ledger | `execution/ledger.py` (free reconcile), `execution/alpaca_paper.py` (optional broker) | `execution/ledger.json` gitignored |
| Dashboard | `dashboard/` (Next.js 15, Tailwind) | brand **Sovian**; Tradeable / Watchlist / Informational; SVG charts; localStorage ★ |
| LLM agents (legacy) | `agents/`, `orchestrator/` | technical/fundamental/arbitrator; predates the quant spine |

## Validated findings (net of cost, out-of-sample) — DO NOT overstate
- **US longs = the only tradeable edge:** ~57% win, +0.97%/trade, PF 1.54. Book: 24% CAGR vs SPY 13%, Sharpe 1.26 vs 0.76, maxDD −23% vs −34%.
- **India longs + all shorts = net-negative → "Informational", not trade signals.**
- **Survivorship bias is the big asterisk:** universe is today's winners → treat returns as an UPPER BOUND. The forward ledger is the honest test.

## Run it
```bash
source .venv/bin/activate
PYTHONPATH=. python -m data.backfill            # refresh 10y cache
PYTHONPATH=. python -m quant.backtest_rules     # validate the exact trade
PYTHONPATH=. python -m quant.portfolio          # equity curve vs SPY
PYTHONPATH=. python -m quant.scan               # regenerate scan.json (+ dashboard copy)
PYTHONPATH=. python -m execution.ledger record  # log today's tradeable signals
PYTHONPATH=. python -m execution.ledger reconcile
cd dashboard && npm run build                   # then: vercel deploy --prod --yes && vercel alias set <url> sovian-trading.vercel.app
```
Env: `.venv` is Python 3.9 → keep `from __future__ import annotations` in any module using `|` unions. Secrets in `.env` (GROQ, ALPHA_VANTAGE, SUPABASE live; FRED present; ALPACA empty).

## What's next (priority order)
1. **Cheapest/highest-integrity:** automate the ledger (daily cron: backfill→scan→record→reconcile) + add Alpaca paper keys. Let the unbiased track record compound.
2. **Point-in-time universe** — kill survivorship bias so the backtest is believable now. Highest-value rigor build.
3. **Phase B grounding** — macro (FRED) + fundamentals + earnings/event flag + hybrid LLM arbitrator. Most valuable for India (no price edge). **See `docs/PHASE-B-PLAN.md` — it's decomposed for parallel sessions.**
4. Telegram push delivery (from the competitor teardown — worth it as delivery).

## Conventions
- Commit messages end with the Co-Authored-By trailer. Branch before non-trivial work.
- Honesty rule: anything not backtestable (fundamentals, macro, news) is a **current-state overlay**, never folded into the backtested score.
- Push can hit transient `SSL_ERROR_SYSCALL` — just retry `git push`.
