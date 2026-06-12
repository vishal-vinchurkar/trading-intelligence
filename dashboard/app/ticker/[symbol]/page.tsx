import Link from "next/link";
import { notFound } from "next/navigation";
import { Disclaimer } from "@/components/Disclaimer";
import { PriceChart } from "@/components/PriceChart";
import { fmtPrice, getSignal, scan, type Label } from "@/lib/scan";

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
            <span className="text-sm text-muted">{s.market} · {s.sector} · {fmtPrice(s.market, s.last_close)}</span>
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
        <div className="mt-3 space-y-2">
          <div className="flex items-center gap-2 text-sm">
            {s.calibration.tradeable ? (
              <span className="rounded bg-bull/15 px-2 py-0.5 text-xs font-semibold text-bull">TRADEABLE</span>
            ) : (
              <span className="rounded bg-border px-2 py-0.5 text-xs text-muted">INFORMATIONAL</span>
            )}
            <span className="text-muted">{s.calibration.reason}</span>
          </div>
          <p className="text-sm text-muted">
            These numbers are from the <span className="text-white">rule-based backtest of this exact trade</span>
            {" "}(net of cost, out-of-sample):{" "}
            <span className="font-mono text-white">{s.calibration.win_rate ?? "—"}% win-rate</span>,{" "}
            <span className="font-mono text-white">{s.calibration.expectancy_pct ?? "—"}% net / trade</span>,{" "}
            <span className="font-mono text-white">PF {s.calibration.profit_factor ?? "—"}</span>
            {s.calibration.samples != null && <> across {s.calibration.samples.toLocaleString()} trades.</>}
          </p>
        </div>
      </section>

      {/* Price chart — 120d close + 50DMA with the trade levels drawn on it */}
      <section className="rounded-xl border border-border bg-panel p-5">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Chart — 120 sessions</h2>
          <span className="text-[11px] text-muted">
            <span className="text-watch">━</span> 50DMA · <span className="text-muted">┄</span> entry · <span className="text-bear">┄</span> stop · <span className="text-bull">┄</span> target
          </span>
        </div>
        <PriceChart s={s} />
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

      {/* Phase B context — fundamentals, events, macro (current-state overlays) */}
      {(s.quality || s.events || scan.macro[s.market]) && (
        <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="rounded-xl border border-border bg-panel p-5">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-muted">Fundamentals</h3>
            {s.quality ? (
              <div className="mt-2">
                <div className="flex items-baseline gap-2">
                  <span className="font-mono text-lg">{s.quality.score.toFixed(0)}</span>
                  <span className={`rounded px-1.5 py-0.5 text-[11px] ${s.quality.assessment === "CHEAP" ? "bg-bull/15 text-bull" : s.quality.assessment === "EXPENSIVE" ? "bg-bear/15 text-bear" : "bg-neutral/15 text-neutral"}`}>
                    {s.quality.assessment}
                  </span>
                </div>
                <ul className="mt-2 space-y-1 text-[11px] text-muted">
                  {s.quality.reasons.slice(0, 3).map((r, i) => <li key={i}>· {r}</li>)}
                </ul>
              </div>
            ) : (
              <p className="mt-2 text-xs text-muted">Not enriched (tradeable + watchlist only).</p>
            )}
            <p className="mt-3 text-[10px] text-muted">Current-state overlay — not in the backtested score.</p>
          </div>

          <div className="rounded-xl border border-border bg-panel p-5">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-muted">Event risk</h3>
            {s.events && s.events.next_earnings_date ? (
              <div className="mt-2 text-sm">
                <div className={s.events.event_within_horizon ? "text-neutral" : "text-muted"}>
                  {s.events.event_within_horizon ? "⚠ earnings soon" : "clear"}
                </div>
                <div className="mt-1 font-mono text-xs text-muted">
                  next earnings {s.events.next_earnings_date}
                  {s.events.days_to_earnings != null && ` (${s.events.days_to_earnings}d)`}
                </div>
                {s.events.event_within_horizon && (
                  <p className="mt-2 text-[11px] text-neutral">Within the trade horizon — size down or wait.</p>
                )}
              </div>
            ) : (
              <p className="mt-2 text-xs text-muted">No upcoming earnings flagged.</p>
            )}
          </div>

          <div className="rounded-xl border border-border bg-panel p-5">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-muted">Macro · {s.market}</h3>
            {scan.macro[s.market] ? (
              <div className="mt-2 space-y-1 text-xs">
                <div>regime <span className="font-mono text-white">{scan.macro[s.market]!.regime}</span></div>
                {scan.macro[s.market]!.ten_year != null && <div className="text-muted">10y <span className="font-mono">{scan.macro[s.market]!.ten_year}%</span></div>}
                {scan.macro[s.market]!.fx && <div className="text-muted">{scan.macro[s.market]!.fx!.pair} <span className="font-mono">{scan.macro[s.market]!.fx!.level}</span> ({scan.macro[s.market]!.fx!.trend})</div>}
                <div className="text-[10px] text-muted">as of {scan.macro[s.market]!.as_of}</div>
              </div>
            ) : (
              <p className="mt-2 text-xs text-muted">Unavailable.</p>
            )}
          </div>
        </section>
      )}

      {/* The trade */}
      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">The trade</h2>
        {s.trade ? (
          <div className="rounded-xl border border-border bg-panel p-5">
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Field label="Direction" value={s.trade.direction.toUpperCase()} />
              <Field label="Entry" value={fmtPrice(s.market, s.trade.entry)} mono />
              <Field label="Stop" value={fmtPrice(s.market, s.trade.stop)} mono />
              <Field label="Target" value={fmtPrice(s.market, s.trade.target)} mono />
              <Field label="Risk/share" value={fmtPrice(s.market, s.trade.risk_per_share)} mono />
              <Field label="Reward/share" value={fmtPrice(s.market, s.trade.reward_per_share)} mono />
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
                  <td className="py-1.5 font-mono text-muted">{fmtPrice(s.market, s.expected_move[h].low)} – {fmtPrice(s.market, s.expected_move[h].high)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="rounded-xl border border-border bg-panel p-5">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-muted">Key levels</h3>
          <div className="mt-3 space-y-2 text-sm">
            <div><span className="text-muted">Resistance: </span><span className="font-mono">{s.key_levels.resistance.map((r) => fmtPrice(s.market, r)).join(", ") || "—"}</span></div>
            <div><span className="text-muted">Support: </span><span className="font-mono">{s.key_levels.support.map((r) => fmtPrice(s.market, r)).join(", ") || "—"}</span></div>
            <div><span className="text-muted">ATR(14): </span><span className="font-mono">{fmtPrice(s.market, s.volatility.atr_14)} ({s.volatility.atr_pct}%)</span></div>
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
