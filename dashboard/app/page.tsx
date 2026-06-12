"use client";

import { useState } from "react";
import { Disclaimer } from "@/components/Disclaimer";
import { QuantCard } from "@/components/QuantCard";
import {
  book,
  edgeFor,
  favourites,
  scan,
  topLongs,
  topShorts,
  type MarketFilter,
  type Signal,
} from "@/lib/scan";

const MARKETS: MarketFilter[] = ["All", "US", "India"];

// The decision surface. A market toggle keeps the US book and the India book
// cleanly separated — different sessions, currencies, benchmarks and (as the
// backtest shows) different edges — while "All" stays a cross-market discovery view.
export default function Home() {
  const [market, setMarket] = useState<MarketFilter>("All");
  const bt = scan.backtest_meta;
  const b = book(market);
  const edge = edgeFor(market);
  const favs = favourites(market);
  const longs = topLongs(market, 6);
  const shorts = topShorts(market, 6);

  return (
    <div className="space-y-7">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Top Signals</h1>
          <p className="mt-1 text-sm text-muted">
            A deterministic quant score ranks {scan.universe_size} names; the
            strongest setups surface here. Scan as of {scan.as_of}.
          </p>
        </div>
        <Disclaimer />
      </div>

      {/* Market toggle */}
      <div className="flex gap-1.5">
        {MARKETS.map((m) => (
          <button
            key={m}
            onClick={() => setMarket(m)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${
              market === m ? "bg-muted/20 text-white" : "bg-panel text-muted hover:text-white"
            }`}
          >
            {m}
          </button>
        ))}
      </div>

      {/* Backtest credibility — per the selected market */}
      <section className="rounded-xl border border-border bg-panel p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">
            Track record — {market} (10-year backtest)
          </h2>
          <span className="text-[11px] text-muted">
            {bt.date_range?.[0]}→{bt.date_range?.[1]} · out-of-sample after {bt.oos_split}
          </span>
        </div>
        <div className="mt-3 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Stat label={`${market} long/short 15d edge`} value={`${edge ?? "—"}%`} hint={market === "India" ? "≈flat this period" : undefined} />
          <Stat label="Names in view" value={`${b.total}`} />
          <Stat label="Net book" value={`${b.longs}L / ${b.shorts}S`} />
          <Stat label="Actionable now" value={`${b.actionable}/${b.total}`} />
        </div>
        <p className="mt-3 text-[11px] leading-relaxed text-muted">{bt.note}</p>
      </section>

      {favs.length > 0 && (
        <Deck title="My Watchlist" subtitle="Your pinned names — always shown, regardless of score." signals={favs} />
      )}
      <Deck title="Top Longs" subtitle="Highest conviction. Hit-rate is backtested on this market's own history." signals={longs} />
      <Deck title="Top Shorts" subtitle="Weakest names. Shorts judged on lagging the index, not absolute falls." signals={shorts} />
    </div>
  );
}

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div>
      <div className="text-[11px] text-muted">{label}</div>
      <div className="mt-0.5 font-mono text-lg">{value}</div>
      {hint && <div className="text-[10px] text-muted">{hint}</div>}
    </div>
  );
}

function Deck({ title, subtitle, signals }: { title: string; subtitle: string; signals: Signal[] }) {
  if (signals.length === 0) {
    return (
      <section>
        <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
        <p className="mt-2 text-sm text-muted">No names in this market match.</p>
      </section>
    );
  }
  return (
    <section>
      <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
      <p className="mb-3 text-xs text-muted">{subtitle}</p>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {signals.map((s) => (
          <QuantCard key={s.symbol} s={s} />
        ))}
      </div>
    </section>
  );
}
