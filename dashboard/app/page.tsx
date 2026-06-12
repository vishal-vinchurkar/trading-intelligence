import { Disclaimer } from "@/components/Disclaimer";
import { QuantCard } from "@/components/QuantCard";
import { book, favourites, scan, topLongs, topShorts } from "@/lib/scan";

// The decision surface: the engine hunts the universe and pushes the highest-
// conviction setups front-and-centre, alongside the user's pinned watchlist.
// Everything is backed by the 10-year backtest banner up top.
export default function Home() {
  const bt = scan.backtest_meta;
  const b = book();
  const favs = favourites();
  const longs = topLongs(6);
  const shorts = topShorts(6);

  return (
    <div className="space-y-8">
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

      {/* Backtest credibility — the proof behind every signal */}
      <section className="rounded-xl border border-border bg-panel p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">
            Track record (10-year backtest)
          </h2>
          <span className="text-[11px] text-muted">
            {bt.date_range?.[0]}→{bt.date_range?.[1]} · {bt.samples?.toLocaleString()} samples · out-of-sample after {bt.oos_split}
          </span>
        </div>
        <div className="mt-3 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Stat label="Long/short 15d edge (alpha)" value={`${bt.long_short_edge_15d_pct ?? "—"}%`} />
          <Stat label="Names scored" value={`${bt.symbols ?? "—"}`} />
          <Stat label="Net book" value={`${b.longs}L / ${b.shorts}S`} />
          <Stat label="Actionable now" value={`${b.actionable}/${b.total}`} />
        </div>
        <p className="mt-3 text-[11px] leading-relaxed text-muted">{bt.note}</p>
      </section>

      {favs.length > 0 && (
        <Deck title="My Watchlist" subtitle="Your pinned names — always shown, regardless of score." signals={favs} />
      )}
      <Deck title="Top Longs" subtitle="Highest conviction; backtested hit-rate on each." signals={longs} />
      <Deck title="Top Shorts" subtitle="Weakest names by the score. Shorts judged on lagging the index, not absolute falls." signals={shorts} />
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[11px] text-muted">{label}</div>
      <div className="mt-0.5 font-mono text-lg">{value}</div>
    </div>
  );
}

function Deck({ title, subtitle, signals }: { title: string; subtitle: string; signals: ReturnType<typeof topLongs> }) {
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
