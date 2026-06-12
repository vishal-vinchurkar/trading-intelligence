import Link from "next/link";
import type { Label, Signal } from "@/lib/scan";

const labelStyle: Record<Label, { chip: string; ring: string; bar: string }> = {
  STRONG_BUY: { chip: "bg-bull/20 text-bull", ring: "ring-bull/40", bar: "bg-bull" },
  BUY: { chip: "bg-bull/15 text-bull", ring: "ring-bull/25", bar: "bg-bull" },
  NEUTRAL: { chip: "bg-neutral/15 text-neutral", ring: "ring-border", bar: "bg-neutral" },
  SELL: { chip: "bg-bear/15 text-bear", ring: "ring-bear/25", bar: "bg-bear" },
  STRONG_SELL: { chip: "bg-bear/20 text-bear", ring: "ring-bear/40", bar: "bg-bear" },
};

// One scanned name: conviction score, the band's BACKTESTED hit-rate (the honest
// confidence), and — if the structure justifies it — a placeable trade with R:R.
export function QuantCard({ s }: { s: Signal }) {
  const st = labelStyle[s.label];
  const cal = s.calibration;
  const hit = cal.hit_rate_15d;

  return (
    <Link
      href={`/ticker/${encodeURIComponent(s.symbol)}`}
      className={`block rounded-xl border border-border bg-panel p-4 ring-1 ${st.ring} transition hover:border-muted/50`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-1.5">
            <span className="font-mono text-base font-semibold">{s.symbol}</span>
            {s.is_favourite && <span className="text-watch text-xs">★</span>}
          </div>
          <div className="text-[11px] text-muted">{s.market} · {s.sector}</div>
        </div>
        <span className={`rounded-md px-2 py-0.5 text-xs font-bold ${st.chip}`}>
          {s.label.replace("_", " ")}
        </span>
      </div>

      {/* Conviction score 0–100 */}
      <div className="mt-3 flex items-center gap-2">
        <span className="text-[10px] uppercase tracking-wide text-muted">score</span>
        <div className="relative h-1.5 flex-1 rounded-full bg-border">
          <div className={`absolute h-1.5 rounded-full ${st.bar}`} style={{ width: `${s.score}%` }} />
          <div className="absolute left-1/2 h-1.5 w-px bg-muted/50" />
        </div>
        <span className="font-mono text-sm">{s.score.toFixed(0)}</span>
      </div>

      {/* Backtested credibility + trade R:R */}
      <div className="mt-3 grid grid-cols-2 gap-2 border-t border-border pt-3 text-[11px]">
        <div>
          <div className="text-muted">15d hit (backtested)</div>
          <div className="font-mono">
            {hit == null ? "—" : `${hit}%`}
            {cal.alpha_15d_pct != null && (
              <span className="text-muted"> · α {cal.alpha_15d_pct > 0 ? "+" : ""}{cal.alpha_15d_pct}%</span>
            )}
          </div>
        </div>
        <div>
          <div className="text-muted">trade</div>
          {s.trade ? (
            <div className="font-mono">
              R:R {s.trade.risk_reward}
              <span className={s.trade.actionable ? "text-bull" : "text-muted"}>
                {s.trade.actionable ? " ✓" : " ·watch"}
              </span>
            </div>
          ) : (
            <div className="text-muted">no setup</div>
          )}
        </div>
      </div>
    </Link>
  );
}
