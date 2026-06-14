"use client";

import { useState } from "react";
import { Disclaimer } from "@/components/Disclaimer";
import { QuantCard } from "@/components/QuantCard";
import { TickerSearch } from "@/components/TickerSearch";
import {
  book,
  getSignalsBySymbols,
  informational,
  scan,
  tradeable,
  type MarketFilter,
  type Signal,
} from "@/lib/scan";
import { useWatchlist } from "@/lib/useWatchlist";

const MARKETS: MarketFilter[] = ["All", "US", "India"];

export default function Home() {
  const [market, setMarket] = useState<MarketFilter>("All");
  const { symbols: watch, has, toggle } = useWatchlist();
  const ev = scan.evidence;
  const b = book(market);

  const watchSignals = getSignalsBySymbols(watch).filter(
    (s) => market === "All" || s.market === market
  );
  const td = tradeable(market);
  const info = informational(market);

  const star = { has, onToggleStar: toggle };

  return (
    <div className="space-y-7">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Signals</h1>
          <p className="mt-1 text-sm text-muted">
            A deterministic quant score ranks {scan.universe_size} names; only setups
            that cleared the backtest are marked tradeable. Scan as of {scan.as_of}.
          </p>
        </div>
        <Disclaimer />
      </div>

      {/* Data-freshness guard — never silently serve stale prices */}
      {scan.freshness?.is_stale && (
        <div className="rounded-xl border border-bear/40 bg-bear/10 px-4 py-3 text-sm font-medium text-bear">
          {scan.freshness.message} Prices below are out of date — do not trade off them until refreshed.
        </div>
      )}

      {/* Evidence — the validated edge, with the survivorship caveat in plain sight */}
      <section className="rounded-xl border border-border bg-panel p-5">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">
          What the backtest actually shows
        </h2>
        <div className="mt-3 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Stat label="US-long win-rate (OOS)" value={`${ev.us_long_oos.win_rate ?? "—"}%`} />
          <Stat label="Net edge / trade" value={`${ev.us_long_oos.expectancy_pct ?? "—"}%`} hint={`PF ${ev.us_long_oos.profit_factor ?? "—"}`} />
          <Stat label="Strategy CAGR vs SPY" value={`${ev.portfolio.cagr_pct ?? "—"}% / ${ev.benchmark.cagr_pct ?? "—"}%`} hint={`Sharpe ${ev.portfolio.sharpe ?? "—"} vs ${ev.benchmark.sharpe ?? "—"}`} />
          <Stat label="Max drawdown vs SPY" value={`${ev.portfolio.max_drawdown_pct ?? "—"}% / ${ev.benchmark.max_drawdown_pct ?? "—"}%`} />
        </div>
        <p className="mt-3 rounded-md border border-neutral/20 bg-neutral/5 px-3 py-2 text-[11px] leading-relaxed text-neutral">
          ⚠ {ev.caveats}
        </p>
        {ev.robustness?.robust && (
          <p className="mt-2 rounded-md border border-bull/20 bg-bull/5 px-3 py-2 text-[11px] leading-relaxed text-bull">
            ✓ Survivorship stress-test: the edge isn&apos;t carried by a few hindsight winners.
            Drop the top 5 contributors ({ev.robustness.drop_top5_removed?.join(", ")}) and it&apos;s
            still <span className="font-mono">+{ev.robustness.drop_top5_expectancy_pct}%/trade</span>;
            resampling the universe by name, the 5th-percentile edge is
            {" "}<span className="font-mono">+{ev.robustness.p05_expectancy_pct}%/trade</span> with
            {" "}<span className="font-mono">{Math.round((ev.robustness.share_positive ?? 0) * 100)}%</span> of
            draws positive. Bounds the bias — the forward ledger is still the only unbiased test.
          </p>
        )}
        {ev.attribution?.alpha_survives_vs_momentum && (
          <p className="mt-2 rounded-md border border-bull/20 bg-bull/5 px-3 py-2 text-[11px] leading-relaxed text-bull">
            ✓ Factor-neutralised vs momentum: this isn&apos;t just a momentum ETF repackaged.
            Controlling for the market (SPY) <em>and</em> the momentum factor (MTUM), the book keeps
            {" "}<span className="font-mono">+{ev.attribution.alpha_annual_pct}%/yr</span> of alpha
            (t&nbsp;=&nbsp;<span className="font-mono">{ev.attribution.alpha_t}</span>, Newey-West) —
            statistically significant selection edge beyond smart-beta you could buy for 15bps.
          </p>
        )}
        {ev.slippage?.robust && (
          <p className="mt-2 rounded-md border border-bull/20 bg-bull/5 px-3 py-2 text-[11px] leading-relaxed text-bull">
            ✓ Slippage stress-test: the edge isn&apos;t a fill-quality mirage. On top of commission
            + spread, it survives <span className="font-mono">~{ev.slippage.breakeven_bps} bps</span> of
            slippage before break-even; at a realistic 10 bps it&apos;s still
            {" "}<span className="font-mono">+{ev.slippage.expectancy_at_10bps_pct}%/trade</span>
            {" "}(vs <span className="font-mono">+{ev.slippage.base_expectancy_pct}%</span> frictionless).
          </p>
        )}
        {ev.walkforward?.robust && (
          <p className="mt-2 rounded-md border border-bull/20 bg-bull/5 px-3 py-2 text-[11px] leading-relaxed text-bull">
            ✓ Walk-forward: the edge isn&apos;t one lucky regime. Net-positive in
            {" "}<span className="font-mono">{ev.walkforward.years_positive}/{ev.walkforward.years_total} years</span>
            {" "}({Math.round((ev.walkforward.share_positive ?? 0) * 100)}%), median
            {" "}<span className="font-mono">+{ev.walkforward.median_expectancy_pct}%/trade</span>. Worst year was
            {" "}<span className="font-mono">{ev.walkforward.worst_year}</span> at
            {" "}<span className="font-mono">{ev.walkforward.worst_expectancy_pct}%</span> — the momentum
            drawdown, where this style is supposed to bleed.
          </p>
        )}
      </section>

      {/* Market toggle + book */}
      <div className="flex flex-wrap items-center justify-between gap-3">
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
        <div className="text-[11px] text-muted">
          {market} book: <span className="text-bull">{b.longs}L</span> /{" "}
          <span className="text-bear">{b.shorts}S</span> · {b.tradeable} tradeable
        </div>
      </div>

      {/* Watchlist — always shown so the add-ticker box is reachable even when empty. */}
      <section className="space-y-3">
        <div>
          <h2 className="text-lg font-semibold">My Watchlist</h2>
          <p className="text-sm text-muted">
            Search any scanned name to pin it, or click ★ on any card. Saved in your browser.
          </p>
        </div>
        <TickerSearch has={has} onToggleStar={toggle} />
        {watchSignals.length > 0 ? (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {watchSignals.map((s) => (
              <QuantCard key={s.symbol} s={s} starred={has(s.symbol)} onToggleStar={toggle} />
            ))}
          </div>
        ) : (
          <p className="rounded-lg border border-dashed border-border px-3 py-4 text-sm text-muted">
            No pinned names {market !== "All" && `in ${market} `}yet — search above to add one.
          </p>
        )}
      </section>

      <Deck
        title="Tradeable now"
        subtitle="US longs that cleared the backtest (net-positive expectancy out-of-sample). The R:R ✓/·wait flag tells you if today's entry is worth it."
        signals={td}
        star={star}
        empty="No tradeable signals in this market — the engine only validates US longs."
      />

      <Deck
        title="Informational — no validated edge"
        subtitle="Shorts and India longs were net-negative in the backtest. Shown for context; not trade signals."
        signals={info.slice(0, 9)}
        star={star}
        muted
      />
    </div>
  );
}

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div>
      <div className="text-[11px] text-muted">{label}</div>
      <div className="mt-0.5 font-mono text-base">{value}</div>
      {hint && <div className="text-[10px] text-muted">{hint}</div>}
    </div>
  );
}

function Deck({
  title,
  subtitle,
  signals,
  star,
  empty,
  muted,
}: {
  title: string;
  subtitle: string;
  signals: Signal[];
  star: { has: (s: string) => boolean; onToggleStar: (s: string) => void };
  empty?: string;
  muted?: boolean;
}) {
  return (
    <section className={muted ? "opacity-80" : undefined}>
      <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
      <p className="mb-3 text-xs text-muted">{subtitle}</p>
      {signals.length === 0 ? (
        <p className="text-sm text-muted">{empty ?? "Nothing here."}</p>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {signals.map((s) => (
            <QuantCard key={s.symbol} s={s} starred={star.has(s.symbol)} onToggleStar={star.onToggleStar} />
          ))}
        </div>
      )}
    </section>
  );
}
