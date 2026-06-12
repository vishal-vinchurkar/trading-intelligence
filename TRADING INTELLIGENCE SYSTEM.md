# Trading Intelligence System — Master Project Brief

> Complete context document for Claude Code. Read this entirely before writing a single line of code.

-----

## 1. What We Are Building

A **multi-agent AI trading intelligence platform** that performs real-time technical analysis, fundamental research, and arbitrated prediction for stocks in **US and Indian equity markets**, plus **prediction markets** (Polymarket).

This is a personal side project — not enterprise software. It must be:

- Near-zero ongoing cost
- Runnable from a MacBook Pro (M5, 24GB RAM)
- Extensible — start simple, layer complexity over time
- Opinionated in its predictions, not just a data aggregator

-----

## 2. The Problem It Solves

Manual trading research is slow, biased, and incomplete. A trader checking technicals may ignore macro signals. A fundamental analyst may miss momentum shifts. This system runs three independent AI agents in parallel — each with a defined role and no awareness of the others’ conclusions — then feeds both outputs to a fourth arbitrator agent that makes an unbiased, reasoned prediction.

-----

## 3. Target Markets

### USA

- Equities: NYSE, NASDAQ listed stocks
- Indices: S&P 500, NASDAQ 100, Dow Jones
- Data sources: Alpha Vantage (free), Polygon.io (free tier), FRED (macro, free)
- Trading hours: 9:30am–4:00pm ET (UTC-4/5)

### India

- Equities: NSE (National Stock Exchange), BSE (Bombay Stock Exchange)
- Indices: NIFTY 50, SENSEX, NIFTY Bank
- Data sources: Yahoo Finance (unofficial, free), NSE India API (public endpoints), Alpha Vantage India coverage
- Trading hours: 9:15am–3:30pm IST (UTC+5:30)

### Prediction Markets

- Polymarket (public API, free, no auth required)
- Focus: macro events, earnings outcomes, Fed decisions, RBI decisions

-----

## 4. Multi-Agent Architecture

### Overview

```
User Input (ticker + market)
        ↓
┌───────────────────────────────────┐
│  Agent 1          Agent 2         │  ← Run in PARALLEL
│  Technical        Fundamental     │
│  Analyst          Researcher      │
└────────┬──────────────┬───────────┘
         └──────┬───────┘
                ↓
          Agent 3: Arbitrator
          (receives both JSON outputs,
           makes final prediction)
                ↓
          Agent 4: Tech Implementor
          (infrastructure, deployment,
           cost optimisation decisions)
                ↓
     Supabase (persistence)
          ↓
     Vercel Dashboard (UI)
```

-----

### Agent 1: Technical Analyst

**Role:** Analyse price action and momentum signals only. No access to fundamentals.

**Inputs:**

- OHLCV data (Open, High, Low, Close, Volume) — last 90 days
- Real-time quote

**Computes:**

- RSI (14-period) — overbought/oversold
- MACD (12/26/9) — momentum and crossovers
- Moving averages: 20 SMA, 50 SMA, 200 SMA — trend direction
- Bollinger Bands (20, 2σ) — volatility and breakout signals
- Volume trend — accumulation vs distribution
- Support and resistance levels — key price zones
- Candlestick patterns — last 5 sessions

**Output (JSON):**

```json
{
  "agent": "technical",
  "ticker": "RELIANCE.NS",
  "market": "India/NSE",
  "timestamp": "ISO8601",
  "signal": "BULLISH | BEARISH | NEUTRAL",
  "confidence": 0.0–1.0,
  "timeframe": "SHORT | MEDIUM | LONG",
  "indicators": {
    "rsi": { "value": 58.3, "signal": "NEUTRAL" },
    "macd": { "value": 0.42, "signal": "BULLISH" },
    "ma_trend": "BULLISH",
    "bollinger": "WITHIN_BANDS",
    "volume": "ACCUMULATION"
  },
  "key_levels": {
    "support": [2840, 2780],
    "resistance": [2960, 3020]
  },
  "summary": "Plain English 2–3 sentence summary"
}
```

-----

### Agent 2: Fundamental Researcher

**Role:** Analyse business quality, valuation, and macro context only. No access to price charts.

**Inputs:**

- Financial ratios: P/E, P/B, EV/EBITDA, debt-to-equity, ROE, ROC
- Revenue and earnings growth (last 4 quarters)
- Recent news headlines (last 7 days)
- Macro context: relevant central bank rates, sector trends
- For India: FII/DII flow data where available

**Output (JSON):**

```json
{
  "agent": "fundamental",
  "ticker": "RELIANCE.NS",
  "market": "India/NSE",
  "timestamp": "ISO8601",
  "signal": "BULLISH | BEARISH | NEUTRAL",
  "confidence": 0.0–1.0,
  "horizon": "SHORT | MEDIUM | LONG",
  "valuation": {
    "pe_ratio": 28.4,
    "pb_ratio": 2.1,
    "assessment": "FAIR | OVERVALUED | UNDERVALUED"
  },
  "growth": {
    "revenue_yoy": 0.12,
    "earnings_yoy": 0.08,
    "trend": "ACCELERATING | STABLE | DECELERATING"
  },
  "macro": {
    "rate_environment": "NEUTRAL",
    "sector_outlook": "POSITIVE",
    "notes": "RBI hold, energy sector tailwinds"
  },
  "catalysts": ["Q2 earnings due in 3 weeks", "JIO subscriber growth"],
  "risks": ["Crude oil price sensitivity", "USD/INR headwind"],
  "summary": "Plain English 2–3 sentence summary"
}
```

-----

### Agent 3: Arbitrator

**Role:** Receive both agent outputs, identify alignment or conflict, stress-test both theses, and deliver a final actionable prediction. This agent is the most important — it must be the highest-capability model available.

**Inputs:**

- Agent 1 JSON output
- Agent 2 JSON output
- Current market context (trading session, recent volatility)

**Reasoning process (internal):**

1. Do technical and fundamental signals agree or conflict?
1. If conflict — which signal is more reliable given current market regime?
1. What is the most likely price scenario over 5, 15, 30 trading days?
1. What would invalidate this prediction?
1. What is the risk/reward ratio?

**Output (JSON):**

```json
{
  "agent": "arbitrator",
  "ticker": "RELIANCE.NS",
  "market": "India/NSE",
  "timestamp": "ISO8601",
  "verdict": "BUY | SELL | HOLD | WATCH",
  "confidence": 0.0–1.0,
  "signal_alignment": "ALIGNED | CONFLICTED | PARTIAL",
  "prediction": {
    "5_day": { "direction": "UP", "magnitude": "2–4%" },
    "15_day": { "direction": "UP", "magnitude": "5–8%" },
    "30_day": { "direction": "NEUTRAL", "magnitude": "±2%" }
  },
  "invalidation": "Close below 2780 support invalidates bullish thesis",
  "risk_reward": "1:2.4",
  "reasoning": "Detailed plain English paragraph — 5–8 sentences explaining the final call",
  "dissent": "Any aspect where technical and fundamental diverge and why it was weighted as it was"
}
```

-----

### Agent 4: Tech Implementor

**Role:** Infrastructure and architecture decision-making. Triggered when adding new features, optimising costs, or scaling the system. Not invoked on every trade signal.

**Responsibilities:**

- Choose free-tier vs paid services for each new requirement
- Design database schemas in Supabase
- Write Cloudflare Worker cron scripts for scheduled signal generation
- Optimise API call patterns to stay within free tiers
- Document infrastructure decisions

-----

## 5. Technology Stack

### AI / LLM Layer

|Component           |Tool                                             |Cost         |
|--------------------|-------------------------------------------------|-------------|
|Agents 1 & 2        |Llama 4 via Groq on Vercel AI SDK                |Free tier    |
|Agent 3 (Arbitrator)|Claude Enterprise (existing plan) via Claude Code|$0 additional|
|Orchestration       |Claude Code (CLI)                                |Existing plan|
|Local fallback      |Ollama on MacBook M5 (Llama 3.1 8B)              |Free         |

### Data Sources

|Data Type          |Source                             |Cost               |
|-------------------|-----------------------------------|-------------------|
|US equities OHLCV  |Alpha Vantage                      |Free (25 calls/day)|
|US real-time quotes|Polygon.io                         |Free tier          |
|India equities     |Yahoo Finance (yfinance Python lib)|Free               |
|India NSE data     |NSE India public endpoints         |Free               |
|Macro / rates      |FRED API                           |Free               |
|News headlines     |Alpha Vantage News                 |Free               |
|Prediction markets |Polymarket REST API                |Free               |

### Infrastructure

|Layer            |Tool                     |Cost     |
|-----------------|-------------------------|---------|
|Frontend         |Next.js on Vercel        |Free tier|
|Database         |Supabase (PostgreSQL)    |Free tier|
|Auth             |Supabase Auth            |Free     |
|Caching          |Upstash Redis            |Free tier|
|Scheduled signals|Cloudflare Workers (cron)|Free tier|
|DNS + CDN        |Cloudflare               |Free     |
|Domain           |Cloudflare Registrar     |~$10/yr  |
|Monitoring       |Vercel Analytics         |Free     |

**Estimated monthly cost: $0–$15** (only variable = if Alpha Vantage or Polygon paid tier needed)

### Local Development

- MacBook Pro M5 (24GB unified memory)
- Ollama for local model fallback
- Claude Code for orchestration and agent prompting
- Python 3.11+ for data fetching and indicator computation

-----

## 6. Data Flow — Step by Step

```
1. TRIGGER
   └── Manual: User enters ticker in dashboard
   └── Automated: Cloudflare Worker cron fires (every 30min during market hours)

2. ORCHESTRATOR (orchestrator.py via Claude Code)
   └── Validates ticker and identifies market (US or India)
   └── Fetches OHLCV from Alpha Vantage / yfinance
   └── Fetches fundamentals from Alpha Vantage / yfinance
   └── Fetches news from Alpha Vantage News API
   └── Fetches macro data from FRED

3. PARALLEL EXECUTION
   └── Calls Agent 1 (Technical) → Groq/Llama 4
   └── Calls Agent 2 (Fundamental) → Groq/Llama 4
   └── Both run simultaneously using asyncio

4. ARBITRATION
   └── Agent 1 JSON + Agent 2 JSON → Agent 3 (Arbitrator)
   └── Arbitrator is Claude via Claude Code (highest reasoning quality)
   └── Returns final verdict JSON

5. PERSISTENCE
   └── All three agent outputs saved to Supabase
   └── Tables: signals, tickers, predictions, market_data

6. DISPLAY
   └── Vercel dashboard polls Supabase
   └── Shows latest signal per ticker
   └── Shows signal history and prediction accuracy over time
```

-----

## 7. Supabase Schema

```sql
-- Tickers being tracked
CREATE TABLE tickers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  symbol TEXT NOT NULL,           -- e.g. 'RELIANCE.NS', 'AAPL'
  name TEXT,
  market TEXT NOT NULL,           -- 'US' or 'India'
  exchange TEXT,                  -- 'NSE', 'BSE', 'NYSE', 'NASDAQ'
  active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Raw agent outputs
CREATE TABLE agent_outputs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker_id UUID REFERENCES tickers(id),
  agent TEXT NOT NULL,            -- 'technical', 'fundamental', 'arbitrator'
  output JSONB NOT NULL,          -- full agent JSON
  model_used TEXT,                -- 'llama4-scout', 'claude-sonnet', etc.
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Final predictions (arbitrator output only, denormalised for fast reads)
CREATE TABLE predictions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker_id UUID REFERENCES tickers(id),
  verdict TEXT NOT NULL,          -- 'BUY', 'SELL', 'HOLD', 'WATCH'
  confidence FLOAT,
  signal_alignment TEXT,
  reasoning TEXT,
  prediction_5d JSONB,
  prediction_15d JSONB,
  prediction_30d JSONB,
  invalidation TEXT,
  risk_reward TEXT,
  technical_signal TEXT,
  fundamental_signal TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Outcome tracking (fill in later to measure accuracy)
CREATE TABLE outcomes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  prediction_id UUID REFERENCES predictions(id),
  actual_5d_return FLOAT,
  actual_15d_return FLOAT,
  actual_30d_return FLOAT,
  verdict_correct BOOLEAN,
  recorded_at TIMESTAMPTZ DEFAULT now()
);
```

-----

## 8. File Structure

```
trading-intelligence/
│
├── README.md
├── TRADING_INTELLIGENCE_SYSTEM.md   ← this file
│
├── orchestrator/
│   ├── orchestrator.py              ← main entry point, async runner
│   ├── market_utils.py              ← market hours, ticker validation
│   └── supabase_client.py           ← DB read/write helpers
│
├── data/
│   ├── fetcher_us.py                ← Alpha Vantage + Polygon for US
│   ├── fetcher_india.py             ← yfinance + NSE endpoints for India
│   ├── fetcher_macro.py             ← FRED API
│   ├── fetcher_news.py              ← Alpha Vantage News
│   └── fetcher_polymarket.py        ← Polymarket REST API
│
├── indicators/
│   └── technical.py                 ← RSI, MACD, SMA, Bollinger, Volume
│
├── agents/
│   ├── agent_technical.py           ← Agent 1 prompt + Groq/Llama 4 call
│   ├── agent_fundamental.py         ← Agent 2 prompt + Groq/Llama 4 call
│   ├── agent_arbitrator.py          ← Agent 3 prompt (Claude via Claude Code)
│   └── prompts/
│       ├── technical_system.md      ← System prompt for Agent 1
│       ├── fundamental_system.md    ← System prompt for Agent 2
│       └── arbitrator_system.md     ← System prompt for Agent 3
│
├── workers/
│   └── cron_signal.js               ← Cloudflare Worker cron job
│
├── dashboard/                       ← Next.js app deployed to Vercel
│   ├── app/
│   │   ├── page.tsx                 ← Main dashboard
│   │   ├── ticker/[symbol]/page.tsx ← Per-ticker detail view
│   │   └── api/
│   │       ├── trigger/route.ts     ← Manual signal trigger endpoint
│   │       └── signals/route.ts     ← Read signals from Supabase
│   ├── components/
│   │   ├── SignalCard.tsx           ← Verdict display component
│   │   ├── AgentOutputPanel.tsx     ← Expandable raw agent output
│   │   ├── PredictionChart.tsx      ← Historical predictions chart
│   │   └── TickerSearch.tsx         ← Search and add tickers
│   └── lib/
│       └── supabase.ts              ← Supabase client for frontend
│
├── .env.example                     ← All required env vars documented
└── requirements.txt                 ← Python dependencies
```

-----

## 9. Environment Variables

```bash
# Data APIs
ALPHA_VANTAGE_API_KEY=
POLYGON_API_KEY=
FRED_API_KEY=

# Supabase
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

# Groq (for Llama 4 via Vercel AI SDK)
GROQ_API_KEY=

# Cloudflare (for Workers cron)
CLOUDFLARE_ACCOUNT_ID=
CLOUDFLARE_API_TOKEN=

# Optional: Upstash Redis (caching)
UPSTASH_REDIS_REST_URL=
UPSTASH_REDIS_REST_TOKEN=
```

-----

## 10. Agent System Prompts (Starter Templates)

### Agent 1 — Technical Analyst System Prompt

```
You are a professional technical analyst with 20 years of experience in equity markets.
You analyse price action and momentum signals only.
You have NO access to company fundamentals, news, or macro data.
Your job is to assess the technical picture and output a structured JSON verdict.

Rules:
- Base your analysis ONLY on the OHLCV data and computed indicators provided
- Be specific about price levels — name exact support and resistance zones
- Do not hedge excessively — take a clear position
- Confidence below 0.4 should result in NEUTRAL signal
- Output ONLY valid JSON matching the schema provided. No prose outside the JSON.
```

### Agent 2 — Fundamental Researcher System Prompt

```
You are a fundamental equity analyst with deep expertise in US and Indian markets.
You analyse business quality, valuation, and macro context only.
You have NO access to price charts, technical indicators, or recent price action.
Your job is to assess whether a company is fundamentally sound and fairly valued.

Rules:
- For Indian stocks: factor in RBI policy, FII/DII flows, INR/USD dynamics
- For US stocks: factor in Fed policy, sector rotation, earnings cycle
- Be specific about valuation — is the current P/E justified by growth?
- Name specific catalysts and risks — not generic statements
- Output ONLY valid JSON matching the schema provided. No prose outside the JSON.
```

### Agent 3 — Arbitrator System Prompt

```
You are the final decision-maker in a three-stage investment research process.
You will receive two independent research reports: one technical, one fundamental.
The analysts who wrote them did not see each other's work.

Your job:
1. Identify whether the two signals agree, partially agree, or conflict
2. If they conflict, determine which signal deserves more weight given current market conditions
3. Produce a final actionable verdict: BUY, SELL, HOLD, or WATCH
4. Provide a specific prediction for 5, 15, and 30 trading days
5. State clearly what would invalidate your thesis

Rules:
- Do not average the two signals — make a real decision
- A conflicted signal is valid information, not a reason to say HOLD by default
- Be specific about price targets and time horizons
- Output ONLY valid JSON matching the schema provided. No prose outside the JSON.
```

-----

## 11. Build Sequence (Phase by Phase)

### Phase 1 — Foundation (Build First)

1. Set up Supabase project and run schema migrations
1. Build `fetcher_us.py` — Alpha Vantage OHLCV + fundamentals
1. Build `fetcher_india.py` — yfinance NSE/BSE data
1. Build `indicators/technical.py` — RSI, MACD, SMA, Bollinger
1. Test data pipeline end-to-end with 5 tickers (3 US, 2 India)

### Phase 2 — Agents

1. Build Agent 1 (Technical) with Groq/Llama 4
1. Build Agent 2 (Fundamental) with Groq/Llama 4
1. Build Agent 3 (Arbitrator) — Claude via Claude Code
1. Build `orchestrator.py` — async parallel execution of Agents 1 & 2

### Phase 3 — Dashboard

1. Scaffold Next.js app in `/dashboard`
1. Build `SignalCard` component — verdict + confidence display
1. Build `AgentOutputPanel` — expandable raw agent reasoning
1. Build `TickerSearch` — add/remove tracked tickers
1. Deploy to Vercel, connect to Supabase

### Phase 4 — Automation

1. Build Cloudflare Worker cron — fires every 30min during market hours
1. Handle market hours logic (US Eastern vs India IST)
1. Build `PredictionChart` — historical accuracy tracking

### Phase 5 — Prediction Markets (Later)

1. Build `fetcher_polymarket.py`
1. Add Polymarket signals as a fourth input to the Arbitrator
1. Add Polymarket market browser to dashboard

-----

## 12. Key Constraints and Rules

- **Never hardcode API keys** — always use environment variables
- **Respect free tier limits** — Alpha Vantage is 25 calls/day on free tier; cache aggressively in Supabase
- **Market hours awareness** — don’t run agents outside trading hours; log a “market closed” status instead
- **India timezone handling** — all stored timestamps in UTC; convert to IST for display only
- **Agent isolation** — Agents 1 and 2 must never receive each other’s outputs; only Agent 3 sees both
- **JSON schema enforcement** — validate all agent outputs against schema before saving to Supabase; retry once on malformed output
- **No financial advice disclaimer** — dashboard must display: “This is experimental research tooling. Not financial advice.”
- **Accuracy tracking** — every prediction must be stored with enough data to measure correctness later

-----

## 13. Starter Tickers

### USA

- AAPL (Apple — large cap tech)
- NVDA (NVIDIA — AI/semiconductor)
- JPM (JPMorgan — financials)

### India

- RELIANCE.NS (Reliance Industries — conglomerate)
- HDFCBANK.NS (HDFC Bank — banking)
- INFY.NS (Infosys — IT services)

-----

## 14. What Claude Code Should Do First

When you receive this brief, your first actions are:

1. Confirm you have read and understood all 14 sections
1. Ask if there are any clarifications needed before starting
1. Begin with **Phase 1, Step 1**: scaffold the project directory structure exactly as defined in Section 8
1. Then proceed to **Phase 1, Step 2**: build `fetcher_us.py` with Alpha Vantage integration
1. At each phase boundary, pause and confirm before proceeding

Do not skip phases. Do not build the dashboard before the data pipeline works.