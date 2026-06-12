-- Trading Intelligence — schema v2 (quant engine + backtest era)
-- Additive migration. Run in the Supabase SQL editor after schema.sql.
-- NOTE: the dashboard currently renders from the bundled quant/scan.json, so
-- these tables are for the LIVE/cron path (Phase 4) — not required to demo.

-- 10-year daily price history — the feature store the backtest/scan read.
-- (The local CSV cache in data/cache/ is the working copy; this is the shared one.)
CREATE TABLE IF NOT EXISTS price_history (
  symbol TEXT NOT NULL,
  date   DATE NOT NULL,
  open   DOUBLE PRECISION,
  high   DOUBLE PRECISION,
  low    DOUBLE PRECISION,
  close  DOUBLE PRECISION,
  volume BIGINT,
  PRIMARY KEY (symbol, date)
);
CREATE INDEX IF NOT EXISTS idx_price_history_symbol ON price_history(symbol, date DESC);

-- The user's pinned watchlist (shown front-and-centre regardless of score).
ALTER TABLE tickers ADD COLUMN IF NOT EXISTS is_favourite BOOLEAN DEFAULT false;

-- Latest quant scan per name — ranked signals with trade construct + calibration.
CREATE TABLE IF NOT EXISTS signals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  symbol TEXT NOT NULL,
  as_of DATE NOT NULL,
  score DOUBLE PRECISION,
  label TEXT,                    -- STRONG_BUY..STRONG_SELL
  conviction DOUBLE PRECISION,
  components JSONB,
  trade JSONB,                   -- entry/stop/target/risk_reward/actionable
  calibration JSONB,             -- backtested hit-rate/alpha for the band
  volatility JSONB,
  expected_move JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (symbol, as_of)
);
CREATE INDEX IF NOT EXISTS idx_signals_asof ON signals(as_of DESC, conviction DESC);

-- Anchor price stored WITH each prediction so outcomes can compute realised
-- return point-in-time (the forward-accruing track record alongside the backtest).
ALTER TABLE predictions ADD COLUMN IF NOT EXISTS price_at_prediction DOUBLE PRECISION;
ALTER TABLE predictions ADD COLUMN IF NOT EXISTS quant_score DOUBLE PRECISION;

-- Read access for the browser (anon) — same pattern as dashboard_policies.sql.
ALTER TABLE price_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE signals       ENABLE ROW LEVEL SECURITY;
CREATE POLICY "public read price_history" ON price_history FOR SELECT USING (true);
CREATE POLICY "public read signals"       ON signals       FOR SELECT USING (true);
