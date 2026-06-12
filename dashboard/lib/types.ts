// Mirrors the Supabase schema in orchestrator/schema.sql and the agent JSON
// schemas in agents/prompts/*. Kept hand-written (no generated types) so the
// dashboard stays readable and the shape is obvious at a glance.

export type Verdict = "BUY" | "SELL" | "HOLD" | "WATCH";
export type Signal = "BULLISH" | "BEARISH" | "NEUTRAL";
export type Alignment = "ALIGNED" | "CONFLICTED" | "PARTIAL";
export type Direction = "UP" | "DOWN" | "NEUTRAL";

export interface Ticker {
  id: string;
  symbol: string;
  name: string | null;
  market: string; // 'US' | 'India'
  exchange: string | null;
  active: boolean;
  created_at: string;
}

export interface PredictionLeg {
  direction: Direction;
  magnitude: string; // e.g. "2-4%"
}

export interface Prediction {
  id: string;
  ticker_id: string;
  verdict: Verdict;
  confidence: number | null;
  signal_alignment: Alignment | null;
  reasoning: string | null;
  prediction_5d: PredictionLeg | null;
  prediction_15d: PredictionLeg | null;
  prediction_30d: PredictionLeg | null;
  invalidation: string | null;
  risk_reward: string | null;
  technical_signal: Signal | null;
  fundamental_signal: Signal | null;
  created_at: string;
}

// A prediction joined to its ticker — what the dashboard list renders.
export interface PredictionWithTicker extends Prediction {
  ticker: Ticker | null;
}

// Raw agent output rows (agent_outputs table). `output` is the full agent JSON.
export interface AgentOutput {
  id: string;
  ticker_id: string;
  agent: "technical" | "fundamental" | "arbitrator";
  output: Record<string, unknown>;
  model_used: string | null;
  created_at: string;
}
