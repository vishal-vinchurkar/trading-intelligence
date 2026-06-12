import { createClient } from "@supabase/supabase-js";
import type {
  AgentOutput,
  PredictionWithTicker,
  Ticker,
} from "./types";

// Browser-safe client. Uses the anon key only; reads are gated by RLS policies
// (orchestrator/dashboard_policies.sql). The service role key NEVER reaches here.
const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

export const isSupabaseConfigured = Boolean(url && anonKey);

// Lazily created so a missing env var degrades to an empty-state dashboard
// instead of crashing the whole app at import time.
export function getSupabase() {
  if (!isSupabaseConfigured) {
    throw new Error(
      "Supabase is not configured. Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY."
    );
  }
  return createClient(url!, anonKey!);
}

/**
 * Latest prediction per ticker, newest first. The query pulls predictions joined
 * to their ticker, then we keep only the most recent row for each ticker_id so
 * the home grid shows one card per symbol.
 */
export async function fetchLatestSignals(): Promise<PredictionWithTicker[]> {
  if (!isSupabaseConfigured) return [];
  const supabase = getSupabase();
  const { data, error } = await supabase
    .from("predictions")
    .select("*, ticker:tickers(*)")
    .order("created_at", { ascending: false })
    .limit(500);

  if (error) throw error;

  const seen = new Set<string>();
  const latest: PredictionWithTicker[] = [];
  for (const row of (data ?? []) as PredictionWithTicker[]) {
    if (seen.has(row.ticker_id)) continue;
    seen.add(row.ticker_id);
    latest.push(row);
  }
  return latest;
}

/** All predictions for one symbol, newest first (for the detail-page history). */
export async function fetchTickerHistory(
  symbol: string
): Promise<{ ticker: Ticker | null; predictions: PredictionWithTicker[] }> {
  if (!isSupabaseConfigured) return { ticker: null, predictions: [] };
  const supabase = getSupabase();

  const { data: tickerRows, error: tErr } = await supabase
    .from("tickers")
    .select("*")
    .eq("symbol", symbol)
    .limit(1);
  if (tErr) throw tErr;
  const ticker = (tickerRows?.[0] as Ticker) ?? null;
  if (!ticker) return { ticker: null, predictions: [] };

  const { data, error } = await supabase
    .from("predictions")
    .select("*, ticker:tickers(*)")
    .eq("ticker_id", ticker.id)
    .order("created_at", { ascending: false });
  if (error) throw error;

  return { ticker, predictions: (data ?? []) as PredictionWithTicker[] };
}

/** The three raw agent outputs from the most recent run for a ticker_id. */
export async function fetchLatestAgentOutputs(
  tickerId: string
): Promise<AgentOutput[]> {
  if (!isSupabaseConfigured) return [];
  const supabase = getSupabase();
  const { data, error } = await supabase
    .from("agent_outputs")
    .select("*")
    .eq("ticker_id", tickerId)
    .order("created_at", { ascending: false })
    .limit(20);
  if (error) throw error;

  // Keep the newest row per agent type.
  const seen = new Set<string>();
  const out: AgentOutput[] = [];
  for (const row of (data ?? []) as AgentOutput[]) {
    if (seen.has(row.agent)) continue;
    seen.add(row.agent);
    out.push(row);
  }
  return out;
}
