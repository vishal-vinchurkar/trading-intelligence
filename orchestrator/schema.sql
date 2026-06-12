-- Trading Intelligence System — Supabase schema
-- Run in the Supabase SQL editor (or via `supabase db push`).

-- Tickers being tracked
CREATE TABLE IF NOT EXISTS tickers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  symbol TEXT NOT NULL,           -- e.g. 'RELIANCE.NS', 'AAPL'
  name TEXT,
  market TEXT NOT NULL,           -- 'US' or 'India'
  exchange TEXT,                  -- 'NSE', 'BSE', 'NYSE', 'NASDAQ'
  active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (symbol)
);

-- Raw agent outputs (technical, fundamental, arbitrator)
CREATE TABLE IF NOT EXISTS agent_outputs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker_id UUID REFERENCES tickers(id),
  agent TEXT NOT NULL,            -- 'technical', 'fundamental', 'arbitrator'
  output JSONB NOT NULL,          -- full agent JSON
  model_used TEXT,                -- 'llama4-scout', 'claude-opus-4-8', etc.
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Final predictions (arbitrator output, denormalised for fast reads)
CREATE TABLE IF NOT EXISTS predictions (
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

-- Outcome tracking (filled in later to measure accuracy)
CREATE TABLE IF NOT EXISTS outcomes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  prediction_id UUID REFERENCES predictions(id),
  actual_5d_return FLOAT,
  actual_15d_return FLOAT,
  actual_30d_return FLOAT,
  verdict_correct BOOLEAN,
  recorded_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_outputs_ticker ON agent_outputs(ticker_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_ticker ON predictions(ticker_id, created_at DESC);
