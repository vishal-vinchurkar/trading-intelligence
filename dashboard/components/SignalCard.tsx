import Link from "next/link";
import type { PredictionWithTicker } from "@/lib/types";
import {
  alignmentChip,
  confidencePct,
  directionArrow,
  directionColor,
  formatWhen,
  signalChip,
  verdictStyles,
} from "@/lib/display";

// One card per ticker: the arbitrator verdict, confidence, the two upstream
// agent signals (so the agree/conflict story is visible at a glance), and the
// 5/15/30-day prediction strip. Links to the per-ticker detail view.
export function SignalCard({ p }: { p: PredictionWithTicker }) {
  const symbol = p.ticker?.symbol ?? "—";
  const v = verdictStyles[p.verdict] ?? verdictStyles.WATCH;
  const legs = [
    { label: "5d", leg: p.prediction_5d },
    { label: "15d", leg: p.prediction_15d },
    { label: "30d", leg: p.prediction_30d },
  ];

  return (
    <Link
      href={`/ticker/${encodeURIComponent(symbol)}`}
      className={`block rounded-xl border border-border bg-panel p-5 ring-1 ${v.ring} transition hover:border-muted/50 hover:bg-panel/80`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-mono text-lg font-semibold tracking-tight">{symbol}</div>
          <div className="text-xs text-muted">
            {p.ticker?.name || p.ticker?.market || ""}
          </div>
        </div>
        <span className={`rounded-md px-2.5 py-1 text-sm font-bold ${v.chip}`}>
          {p.verdict}
        </span>
      </div>

      <div className="mt-4 flex items-center gap-2 text-xs">
        <span className="text-muted">confidence</span>
        <div className="h-1.5 flex-1 rounded-full bg-border">
          <div
            className={`h-1.5 rounded-full ${v.text.replace("text-", "bg-")}`}
            style={{ width: confidencePct(p.confidence) }}
          />
        </div>
        <span className={`font-mono ${v.text}`}>{confidencePct(p.confidence)}</span>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-1.5 text-[11px]">
        <span className={`rounded px-1.5 py-0.5 ${signalChip(p.technical_signal)}`}>
          T·{p.technical_signal ?? "—"}
        </span>
        <span className={`rounded px-1.5 py-0.5 ${signalChip(p.fundamental_signal)}`}>
          F·{p.fundamental_signal ?? "—"}
        </span>
        {p.signal_alignment && (
          <span className={`rounded px-1.5 py-0.5 ${alignmentChip(p.signal_alignment)}`}>
            {p.signal_alignment}
          </span>
        )}
      </div>

      <div className="mt-4 grid grid-cols-3 gap-2 border-t border-border pt-3">
        {legs.map(({ label, leg }) => (
          <div key={label} className="text-center">
            <div className="text-[10px] uppercase tracking-wide text-muted">{label}</div>
            <div className={`text-sm ${directionColor(leg?.direction)}`}>
              {directionArrow(leg?.direction)} {leg?.magnitude ?? "—"}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-3 text-[10px] text-muted">{formatWhen(p.created_at)}</div>
    </Link>
  );
}
