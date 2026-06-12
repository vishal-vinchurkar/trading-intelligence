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
PYTHONPATH=. python -m data.backfill      # 10y daily history → data/cache/ (yfinance, free)
PYTHONPATH=. python -m quant.backtest     # point-in-time backtest → quant/backtest_results.json
PYTHONPATH=. python -m quant.scan         # rank the universe → quant/scan.json + dashboard/data/scan.json
```

Honest limits (by design): the backtested score is **price-only** — free data has
no clean point-in-time fundamental history, so fundamentals stay a current-state
LLM overlay we don't claim to have backtested. Edges are **modest** (long side
~52–53% 15d hit, holds out-of-sample; short side ~noise in a secular bull) — which
is the truthful result for a price-only signal on liquid large-caps.

The dashboard (`dashboard/`) renders **Top Signals** (ranked conviction) + **My
Watchlist** (pinned favourites) from the bundled `scan.json` — no DB needed to
demo. Edit the universe in `data/universe.py` and favourites in `quant/scan.py`.

## Status

- ✅ Phase 1 — data pipeline (US + India) and indicators
- ✅ Phase 2 — agents 1/2/3 + async orchestrator
- ✅ Phase 3 — Next.js dashboard (Vercel)
- ✅ Quant engine — deterministic score, 10y point-in-time backtest, trade construct, scan/watchlist dashboard
- ◻ Phase B (next) — real macro (FRED) + wider fundamentals + earnings/event flag, fed into a hybrid LLM arbitrator
- ⬜ Phase 4 — cron refresh + forward outcome tracking (+ optional Telegram push)
- ⬜ Phase 5 — Polymarket inputs
