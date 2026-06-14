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

## Phase B — DONE (grounding overlays)
Built via two parallel sub-agents (contract-first, disjoint files) + integration:
- `data/fetcher_macro.py` — keyless macro regime (yfinance ^TNX/^IRX, USDINR), derived not guessed.
- `quant/quality.py` — current-state 0–100 fundamental quality score.
- `data/events.py` — next-earnings / event-within-horizon flag.
- `quant/scan.py` enriches tradeable + watchlist names (keyless, no AV-quota hit) with quality + events; macro per market. **All current-state overlays — NOT in the backtested score.** Surfaced on the dashboard detail page + ⚠ earnings chip on cards.
- Hybrid LLM narration: `agents/narrate.py` (Groq) — produces thesis+caution subordinate to the quant verdict. **WIRED (2026-06-12):** `quant/scan.py` calls `narrate()` for tradeable+favourites only (bounded Groq calls, ~18 names), stores `narration={thesis,caution}` on the signal; surfaced as a "Thesis" card under the headline on the dashboard detail page (`Narration` type in `lib/scan.ts`). Degrades to None on any Groq failure — never breaks the scan.

## Automation (live)
- `scripts/daily.sh` (backfill→scan→ledger record→reconcile→telegram) + `scripts/weekly.sh` (re-backtest). **Cron installed** (weekdays 07:30 local, Sun 09:00). `logs/` gitignored.
- `execution/telegram_push.py` — needs `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` in `.env` (prints if absent).
- Universe is now **55 names** (de-cherry-picked with laggards + SNOW/NOW); US-long edge held OOS (55% win, PF 1.43, 24.6% CAGR vs SPY 13.2%).

## Survivorship robustness — DONE (2026-06-12), in lieu of full point-in-time
Free price data (yfinance) **purges delisted tickers** (empirically confirmed: SIVB/FRC/WE/FTCH/TWTR return no data; reused tickers give the wrong entity), so a true point-in-time membership universe isn't buildable on this budget. Instead `quant/robustness.py` **bounds** the bias and answers the skeptic:
- **Leave-one-out by name**, **drop-top-K contributors**, **name-level bootstrap** (2000x, resample the SET OF NAMES — survivorship's unit) over US-long rule-based trades.
- Result: edge is robust. Drop top-5 winners (NVDA/AMD/META/PYPL/MSFT) → still +0.41%/trade; bootstrap 5th-pct +0.41%/trade, **100% of draws positive**.
- Writes `quant/robustness_results.json`; `quant/scan.py` folds a summary into `evidence.robustness`; surfaced as a green ✓ stress-test line under the caveat on the dashboard home. Runs in `scripts/weekly.sh`.
- **Honesty:** this BOUNDS, does not ELIMINATE, survivorship bias. The forward paper ledger is still the only unbiased test.

## Session 2026-06-14 — validation hardening + new strategy builds
Reframed by owner: this is a **serious product** (eventual subscription), not a portfolio piece.
Posture decided: **private validation first → RIA registration before any public launch.** No
public customers yet. Independent AI review (in `Claude Just Changed...md` chat) called it "not
investable as-is"; its 5 critiques are now tracked in **`docs/VALIDATION.md`**. Built this session:
- **`quant/attribution.py`** — MTUM factor-neutralisation (the sharpest critique). **+10.2%/yr alpha
  survives, t=4.0** (Newey-West) after controlling for SPY + MTUM. Edge is NOT repackaged smart-beta.
- **`quant/slippage.py`** — slippage stress; US-long edge survives **~42 bps** before break-even.
- **`quant/walkforward.py`** — temporal stability; net-positive in **8/10 years**. (No fitted params,
  so it's temporal partitioning, not parameter walk-forward — stated in the module.)
- All three folded into `quant/scan.py` `evidence.{attribution,slippage,walkforward}` and surfaced as
  green stress-test banners on the dashboard home (`dashboard/app/page.tsx` + types in `lib/scan.ts`).
  `scan.json` patched in place (preserving narration); dashboard typechecks clean.
- **`quant/wheel.py`** — options wheel backtest via Black-Scholes @ realised vol on free price data.
  Finding: income/low-vol play, ~matches buy&hold (~7.8% ROC), NOT alpha. Hypothesis-grade; needs real
  option chains + Alpaca to confirm (realised-vol pricing is conservative vs the vol-risk-premium).
- **`data/congress.py` + `quant/congress_signal.py`** — congressional alt-data overlay, SCAFFOLDED &
  key-ready. Pluggable adapters: Quiver (needs `QUIVER_API_KEY`), free House-Clerk XML index (real, no
  key, transaction detail needs PDF parsing — future), synthetic demo (logic validated solo). Backtest
  is **disclosure-lag-aware by construction** (enter next open AFTER disclosure, not the trade date).
- **`execution/telegram_bridge.py`** — two-way Telegram control channel (send + poll, offset-stated).
  Used for async Q&A while owner is away. State file gitignored.
- All session work is **uncommitted on `main`** (owner hasn't asked to commit).

## What's next (priority order)
1. **Blocked on user creds — Alpaca paper keys:** `.env` `ALPACA_API_KEY`/`ALPACA_SECRET_KEY` are empty. Code (`execution/alpaca_paper.py`) is ready; once keys are in, `python -m execution.alpaca_paper` places paper orders. Steps in chat 2026-06-12.
2. **Blocked on user creds — Telegram push:** `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` not yet in `.env` (BotFather + getUpdates). Code (`execution/telegram_push.py`) is ready; `daily.sh` already calls it (no-op print until tokens present).
3. **True point-in-time universe** — only if a paid delisted-history source (Polygon paid / Norgate) gets provisioned. Robustness harness is the free stand-in until then.

## Conventions
- Commit messages end with the Co-Authored-By trailer. Branch before non-trivial work.
- Honesty rule: anything not backtestable (fundamentals, macro, news) is a **current-state overlay**, never folded into the backtested score.
- Push can hit transient `SSL_ERROR_SYSCALL` — just retry `git push`.
