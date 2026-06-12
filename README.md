# Trading Intelligence System

A multi-agent AI system that analyses US and Indian equities. Two AI analysts
run in parallel — one blind to fundamentals, one blind to price — and a third,
larger model arbitrates their reports into a final BUY/SELL/HOLD/WATCH verdict
with 5/15/30-day predictions. Every output is JSON, schema-validated, and stored.

**Runs entirely on free-tier models. No Anthropic API key required.**

> Experimental research tooling. Not financial advice.

## Architecture

```
ticker ──▶ fetch (Alpha Vantage / yfinance) ──▶ indicators
                                                   │
              ┌────────────────────────────────────┘
              ▼                         ▼
      Agent 1: Technical        Agent 2: Fundamental     ← parallel, isolated
        (Groq / Llama 4)          (Groq / Llama 4)
              └───────────┬────────────┘
                          ▼
                Agent 3: Arbitrator                       ← larger Groq model
              (Groq 70B / Ollama / manual Claude Code)
                          ▼
                  Supabase (optional)
```

Agent isolation is structural: Agent 1 never receives fundamentals, Agent 2
never receives price data; only Agent 3 sees both.

## Setup

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in the keys below
```

Run the Supabase migration in `orchestrator/schema.sql` (optional — the
pipeline runs without it via `--no-save`).

## Run

```bash
# India ticker (needs only GROQ_API_KEY — yfinance is keyless)
PYTHONPATH=. python -m orchestrator.orchestrator RELIANCE.NS --no-save

# US ticker (also needs ALPHA_VANTAGE_API_KEY)
PYTHONPATH=. python -m orchestrator.orchestrator AAPL --no-save

# Quality gate (schema + isolation checks)
PYTHONPATH=. python eval/validate.py NVDA --no-save
```

## Keys (all free)

| Key | For | Required? |
|-----|-----|-----------|
| `GROQ_API_KEY` | all three agents | **Yes** |
| `ALPHA_VANTAGE_API_KEY` | US OHLCV + fundamentals | For US tickers (India uses keyless yfinance) |
| `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` | persistence | Only to save results |
| `FRED_API_KEY`, `POLYGON_API_KEY` | macro / extra US quotes | Optional, later phases |

## Arbitrator without Anthropic

The Arbitrator runs on Groq by default (`ARBITRATOR_PROVIDER=groq`, a 70B-class
model). Alternatives:
- `ollama` — a local model on your machine, zero network cost.
- `manual` — `agent_arbitrator.build_manual_handoff()` emits a prompt you paste
  into Claude Code for a top-tier verdict at $0, then `parse_manual_verdict()`
  writes it back. Use for high-stakes tickers.

## Dashboard

A read-only Next.js dashboard (`dashboard/`) renders the latest signal per
ticker, a per-ticker detail view with all three raw agent outputs, and the
prediction history. It reads Supabase directly with the **anon key** (browser-
safe); the Python pipeline remains the only writer, using the service-role key.

```bash
cd dashboard
npm install
cp .env.local.example .env.local   # add NEXT_PUBLIC_SUPABASE_URL + ANON_KEY
npm run dev                          # http://localhost:3000
```

Enable browser read access once per project by running
`orchestrator/dashboard_policies.sql` in the Supabase SQL editor (RLS on, public
SELECT only — anon can never write). Deploys to Vercel as-is; set the two
`NEXT_PUBLIC_*` env vars in the Vercel project.

## Quant engine + backtest (the executional core)

Beyond the LLM agents, a **deterministic conviction score (0–100)** ranks every
name in the scan universe from price action alone — trend, 6-month momentum,
relative strength vs the benchmark, and volume flow, with an RSI entry-timing
modifier. Because it uses only price, it is computed **point-in-time across 10
years** and **backtested**: each signal carries its real, out-of-sample 15-day
hit-rate and alpha-vs-index, so the dashboard's "confidence" is an empirical
track record, not a model's feeling. Every actionable signal becomes a **trade**
— entry, 2×ATR stop, structural target, and a computed R:R gated at 1.5.

```bash
PYTHONPATH=. python -m data.backfill         # 10y daily history → data/cache/ (yfinance, free)
PYTHONPATH=. python -m quant.backtest         # hold-to-horizon backtest (net of cost)
PYTHONPATH=. python -m quant.backtest_rules   # rule-based: the EXACT trade, bar-by-bar
PYTHONPATH=. python -m quant.portfolio        # daily equity curve vs SPY
PYTHONPATH=. python -m quant.scan             # rank universe → scan.json (+ dashboard copy)
```

### What the backtest actually says (net of cost, out-of-sample)

The rule-based backtest simulates the *exact* trade the dashboard shows — entry
next open, 2×ATR stop, swing-resistance target, 20-day time-stop — net of realistic
costs (US ~10bps, India ~35bps) and a 1-bar execution lag. Findings, stated plainly:

- **US longs are the only tradeable edge:** ~57% win, +0.97% net/trade, profit
  factor 1.54 out-of-sample. As a daily-rebalanced book: **24% CAGR vs SPY's 13%,
  Sharpe 1.26 vs 0.76, max drawdown −23% vs −34%.**
- **India longs and all shorts were net-negative** — demoted to *informational*,
  not trade signals.
- **Survivorship caveat (loud, on purpose):** the universe is *today's* names, so
  those returns are an **upper bound, not a forward expectation.** The honest test
  is the forward ledger below.

### Forward paper-trading ledger (the unbiased test)

`execution/ledger.py` logs every tradeable signal now and grades it as the future
arrives — no broker needed (reconciles against free prices, same rules as the
backtest). `execution/alpaca_paper.py` optionally places real bracket orders on
Alpaca **paper** once `ALPACA_*` keys are set (dry-run by default).

```bash
PYTHONPATH=. python -m execution.ledger record      # log today's tradeable signals
PYTHONPATH=. python -m execution.ledger reconcile    # resolve closed trades, vs backtest
PYTHONPATH=. python -m execution.alpaca_paper         # dry-run paper orders (--live to place)
```

The dashboard (`dashboard/`, branded **Sovian**) renders **Tradeable now** (US
longs that cleared the backtest) + **My Watchlist** (click ★, persisted in
localStorage) + **Informational** from the bundled `scan.json` — with sparklines,
a price chart that draws entry/stop/target on the bars, and an evidence banner that
carries the survivorship caveat. No DB needed to run.

## Status

- ✅ Phases 1–3 — data pipeline, agents, Next.js dashboard
- ✅ Quant engine — deterministic score, point-in-time + rule-based backtest, portfolio curve
- ✅ Trust layer — net-of-cost validation, tradeable re-scoping, forward paper ledger (+ Alpaca paper)
- ✅ UX — Sovian brand, charts, clickable watchlist, honest evidence banner
- ◻ Phase B (next) — real macro (FRED) + fundamentals + earnings/event flag (esp. for India, where price alone has no edge); hybrid LLM arbitrator
- ⬜ Phase 4 — cron refresh + point-in-time universe (kill survivorship bias) + Telegram push
- ⬜ Phase 5 — Polymarket inputs
