"use client";

import Link from "next/link";
import { Sparkline } from "./Sparkline";
import { fmtPrice, type Label, type Signal } from "@/lib/scan";

const labelStyle: Record<Label, { chip: string; ring: string; bar: string }> = {
  STRONG_BUY: { chip: "bg-bull/20 text-bull", ring: "ring-bull/40", bar: "bg-bull" },
  BUY: { chip: "bg-bull/15 text-bull", ring: "ring-bull/25", bar: "bg-bull" },
  NEUTRAL: { chip: "bg-neutral/15 text-neutral", ring: "ring-border", bar: "bg-neutral" },
  SELL: { chip: "bg-bear/15 text-bear", ring: "ring-bear/25", bar: "bg-bear" },
  STRONG_SELL: { chip: "bg-bear/20 text-bear", ring: "ring-bear/40", bar: "bg-bear" },
};

// One scanned name: conviction score, the band's rule-based out-of-sample win-rate
// (the honest confidence), whether it's actually tradeable, and the trade R:R.
export function QuantCard({
  s,
  starred,
  onToggleStar,
}: {
  s: Signal;
  starred?: boolean;
  onToggleStar?: (sym: string) => void;
}) {
  const st = labelStyle[s.label];
  const cal = s.calibration;

  return (
    <Link
      href={`/ticker/${encodeURIComponent(s.symbol)}`}
      className={`relative block rounded-xl border border-border bg-panel p-4 ring-1 ${st.ring} transition hover:border-muted/50`}
    >
      {onToggleStar && (
        <button
          aria-label={starred ? "Remove from watchlist" : "Add to watchlist"}
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onToggleStar(s.symbol);
          }}
          className={`absolute right-3 top-3 text-base leading-none transition ${
            starred ? "text-watch" : "text-muted/40 hover:text-muted"
          }`}
        >
          {starred ? "★" : "☆"}
        </button>
      )}

      <div className="pr-6">
        <div className="font-mono text-base font-semibold">{s.symbol}</div>
        <div className="text-[11px] text-muted">
          {s.market} · {s.sector} · {fmtPrice(s.market, s.last_close)}
        </div>
      </div>

      <div className="mt-2">
        <span className={`rounded-md px-2 py-0.5 text-xs font-bold ${st.chip}`}>
          {s.label.replace("_", " ")}
        </span>
        {cal.tradeable ? (
          <span className="ml-1.5 rounded bg-bull/15 px-1.5 py-0.5 text-[10px] font-medium text-bull">
            TRADEABLE
          </span>
        ) : (
          <span className="ml-1.5 rounded bg-border px-1.5 py-0.5 text-[10px] text-muted">info</span>
        )}
      </div>

      {/* 120-day price sparkline */}
      <div className="mt-3">
        <Sparkline history={s.history} height={36} />
      </div>

      {/* Conviction score 0–100 */}
      <div className="mt-2 flex items-center gap-2">
        <span className="text-[10px] uppercase tracking-wide text-muted">score</span>
        <div className="relative h-1.5 flex-1 rounded-full bg-border">
          <div className={`absolute h-1.5 rounded-full ${st.bar}`} style={{ width: `${s.score}%` }} />
          <div className="absolute left-1/2 h-1.5 w-px bg-muted/50" />
        </div>
        <span className="font-mono text-sm">{s.score.toFixed(0)}</span>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 border-t border-border pt-3 text-[11px]">
        <div>
          <div className="text-muted">win-rate (OOS)</div>
          <div className="font-mono">
            {cal.win_rate == null ? "—" : `${cal.win_rate}%`}
            {cal.profit_factor != null && <span className="text-muted"> · PF {cal.profit_factor}</span>}
          </div>
        </div>
        <div>
          <div className="text-muted">trade</div>
          {s.trade ? (
            <div className="font-mono">
              R:R {s.trade.risk_reward}
              <span className={s.trade.actionable ? "text-bull" : "text-muted"}>
                {s.trade.actionable ? " ✓" : " ·wait"}
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
