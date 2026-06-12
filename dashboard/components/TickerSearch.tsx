"use client";

import { useMemo, useState } from "react";
import type { PredictionWithTicker } from "@/lib/types";
import { SignalCard } from "./SignalCard";

// Client-side filter + verdict toggle over the already-fetched signals. The
// pipeline adds new tickers (it's the source of truth for what's tracked), so
// this is search/filter over the live set rather than a write form — keeps the
// dashboard read-only against the anon key.
const VERDICTS = ["ALL", "BUY", "SELL", "HOLD", "WATCH"] as const;

export function TickerSearch({ signals }: { signals: PredictionWithTicker[] }) {
  const [q, setQ] = useState("");
  const [verdict, setVerdict] = useState<(typeof VERDICTS)[number]>("ALL");

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return signals.filter((s) => {
      if (verdict !== "ALL" && s.verdict !== verdict) return false;
      if (!needle) return true;
      const sym = s.ticker?.symbol?.toLowerCase() ?? "";
      const name = s.ticker?.name?.toLowerCase() ?? "";
      return sym.includes(needle) || name.includes(needle);
    });
  }, [signals, q, verdict]);

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search ticker or company…"
          className="w-full rounded-lg border border-border bg-panel px-3 py-2 text-sm outline-none placeholder:text-muted focus:border-muted/60 sm:max-w-xs"
        />
        <div className="flex flex-wrap gap-1.5">
          {VERDICTS.map((v) => (
            <button
              key={v}
              onClick={() => setVerdict(v)}
              className={`rounded-md px-2.5 py-1 text-xs font-medium transition ${
                verdict === v
                  ? "bg-muted/20 text-white"
                  : "bg-panel text-muted hover:text-white"
              }`}
            >
              {v}
            </button>
          ))}
        </div>
      </div>

      {filtered.length === 0 ? (
        <p className="mt-8 text-center text-sm text-muted">
          No signals match. Adjust the filter, or run the pipeline to add tickers.
        </p>
      ) : (
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((s) => (
            <SignalCard key={s.id} p={s} />
          ))}
        </div>
      )}
    </div>
  );
}
