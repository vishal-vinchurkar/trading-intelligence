import Link from "next/link";
import { notFound } from "next/navigation";
import { Disclaimer } from "@/components/Disclaimer";
import { getSignal, scan, type Label } from "@/lib/scan";

const labelChip: Record<Label, string> = {
  STRONG_BUY: "bg-bull/20 text-bull",
  BUY: "bg-bull/15 text-bull",
  NEUTRAL: "bg-neutral/15 text-neutral",
  SELL: "bg-bear/15 text-bear",
  STRONG_SELL: "bg-bear/20 text-bear",
};

export function generateStaticParams() {
  return scan.signals.map((s) => ({ symbol: s.symbol }));
}

export default async function TickerPage({ params }: { params: Promise<{ symbol: string }> }) {
  const { symbol: raw } = await params;
  const s = getSignal(decodeURIComponent(raw));
  if (!s) notFound();

  return (
    <div className="space-y-7">
      <div className="flex items-start justify-between gap-4">
        <div>
          <Link href="/" className="text-xs text-muted hover:text-white">← all signals</Link>
          <div className="mt-2 flex items-baseline gap-3">
            <h1 className="font-mono text-3xl font-bold">{s.symbol}</h1>
            <span className="text-sm text-muted">{s.market} · {s.sector} · {s.last_close}</span>
            {s.is_favourite && <span className="text-watch">★ watchlist</span>}
          </div>
        </div>
        <Disclaimer />
      </div>

      {/* Headline: score + label + backtested confidence */}
      <section className="rounded-xl border border-border bg-panel p-5">
        <div className="flex flex-wrap items-center gap-3">
          <span className={`rounded-lg px-3 py-1.5 text-lg font-bold ${labelChip[s.label]}`}>
            {s.label.replace("_", " ")}
          </span>
          <span className="font-mono text-2xl">{s.score.toFixed(0)}<span className="text-sm text-muted">/100</span></span>
          <span className="ml-auto text-xs text-muted">as of {s.as_of}</span>
        </div>
        <p className="mt-3 text-sm text-muted">
          Confidence here is <span className="text-white">not</span> a model's feeling — it's the{" "}
          <span className="text-white">backtested 15-day hit-rate</span> for this signal band:{" "}
          <span className="font-mono text-white">{s.calibration.hit_rate_15d ?? "—"}%</span>
          {s.calibration.oos_hit_rate_15d != null && (
            <> in-sample, <span className="font-mono text-white">{s.calibration.oos_hit_rate_15d}%</span> out-of-sample</>
          )}
          {s.calibration.samples != null && <> across {s.calibration.samples.toLocaleString()} historical setups.</>}
        </p>
      </section>

      {/* Score components — why the engine thinks what it thinks */}
      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">Why — score components</h2>
        <div className="space-y-2">
          {Object.entries(s.components).map(([name, c]) => (
            <div key={name} className="rounded-lg border border-border bg-panel p-3">
              <div className="flex items-center justify-between text-sm">
                <span className="capitalize">{name.replace("_", " ")} <span className="text-[11px] text-muted">({Math.round(c.weight * 100)}%)</span></span>
                <span className="font-mono">{c.score.toFixed(0)}</span>
              </div>
              <div className="mt-1.5 h-1 rounded-full bg-border">
                <div className={`h-1 rounded-full ${c.score >= 50 ? "bg-bull" : "bg-bear"}`} style={{ width: `${c.score}%` }} />
              </div>
              <div className="mt-1 text-[11px] text-muted">{c.reason}</div>
            </div>
          ))}
          <div className="text-[11px] text-muted">
            Timing modifier: {s.timing.adjustment > 0 ? "+" : ""}{s.timing.adjustment} ({s.timing.reason})
          </div>
        </div>
      </section>

      {/* The trade */}
      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">The trade</h2>
        {s.trade ? (
          <div className="rounded-xl border border-border bg-panel p-5">
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Field label="Direction" value={s.trade.direction.toUpperCase()} />
              <Field label="Entry" value={`${s.trade.entry}`} mono />
              <Field label="Stop" value={`${s.trade.stop}`} mono />
              <Field label="Target" value={`${s.trade.target}`} mono />
              <Field label="Risk/share" value={`${s.trade.risk_per_share}`} mono />
              <Field label="Reward/share" value={`${s.trade.reward_per_share}`} mono />
              <Field label="R:R" value={`${s.trade.risk_reward}`} mono />
              <Field label="Actionable" value={s.trade.actionable ? "Yes" : "Watch"} />
            </div>
            <p className={`mt-3 text-xs ${s.trade.actionable ? "text-bull" : "text-muted"}`}>{s.trade.note}</p>
          </div>
        ) : (
          <p className="text-sm text-muted">NEUTRAL — no directional setup. The engine sees no edge worth risking here.</p>
        )}
      </section>

      {/* Volatility-scaled expected move + levels */}
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="rounded-xl border border-border bg-panel p-5">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-muted">Expected move (1σ)</h3>
          <p className="mb-3 mt-1 text-[11px] text-muted">
            Sized to realised volatility ({s.volatility.annual_vol_pct}% annualised), not guessed.
          </p>
          <table className="w-full text-sm">
            <tbody>
              {(["5d", "15d", "30d"] as const).map((h) => (
                <tr key={h} className="border-t border-border">
                  <td className="py-1.5 text-muted">{h}</td>
                  <td className="py-1.5 font-mono">±{s.expected_move[h].sigma_pct}%</td>
                  <td className="py-1.5 font-mono text-muted">{s.expected_move[h].low} – {s.expected_move[h].high}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="rounded-xl border border-border bg-panel p-5">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-muted">Key levels</h3>
          <div className="mt-3 space-y-2 text-sm">
            <div><span className="text-muted">Resistance: </span><span className="font-mono">{s.key_levels.resistance.join(", ") || "—"}</span></div>
            <div><span className="text-muted">Support: </span><span className="font-mono">{s.key_levels.support.join(", ") || "—"}</span></div>
            <div><span className="text-muted">ATR(14): </span><span className="font-mono">{s.volatility.atr_14} ({s.volatility.atr_pct}%)</span></div>
          </div>
        </div>
      </section>
    </div>
  );
}

function Field({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wide text-muted">{label}</div>
      <div className={`mt-0.5 ${mono ? "font-mono" : ""}`}>{value}</div>
    </div>
  );
}
