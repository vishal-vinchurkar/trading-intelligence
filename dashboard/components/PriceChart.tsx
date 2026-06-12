import type { Signal } from "@/lib/scan";
import { fmtPrice } from "@/lib/scan";

// Detail-page price chart (SVG, no dependency): 120-day close + 50DMA, with the
// trade levels (entry/stop/target) and swing support/resistance drawn as guides —
// the "what is the chart showing" view a technician expects, grounded in the same
// numbers the engine used.
export function PriceChart({ s, height = 240 }: { s: Signal; height?: number }) {
  const h = s.history;
  if (!h || h.length < 2) return <p className="text-sm text-muted">No price history.</p>;

  const width = 720;
  const padR = 64; // room for the right-hand price axis labels
  const plotW = width - padR;

  const closes = h.map((p) => p.c);
  const levels: number[] = [];
  if (s.trade) levels.push(s.trade.entry, s.trade.stop, s.trade.target);
  s.key_levels.support.forEach((v) => levels.push(v));
  s.key_levels.resistance.forEach((v) => levels.push(v));
  const allVals = [...closes, ...h.map((p) => p.m).filter((v): v is number => v != null), ...levels];
  const min = Math.min(...allVals);
  const max = Math.max(...allVals);
  const span = max - min || 1;
  const n = closes.length;

  const x = (i: number) => (i / (n - 1)) * plotW;
  const y = (v: number) => height - ((v - min) / span) * (height - 16) - 8;

  const line = (vals: (number | null)[]) =>
    vals
      .map((v, i) => (v == null ? null : `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`))
      .filter(Boolean)
      .join(" ")
      .replace(/L(?=M)/g, ""); // tolerate gaps

  const up = closes[n - 1] >= closes[0];

  const guides: { v: number; label: string; color: string; dash?: string }[] = [];
  if (s.trade) {
    guides.push({ v: s.trade.entry, label: "entry", color: "#8b94a7" });
    guides.push({ v: s.trade.stop, label: "stop", color: "#ef4444", dash: "4 3" });
    guides.push({ v: s.trade.target, label: "target", color: "#22c55e", dash: "4 3" });
  }

  return (
    <svg viewBox={`0 0 ${width} ${height}`} width="100%" className="overflow-visible">
      {/* 50DMA */}
      <path d={line(h.map((p) => p.m))} fill="none" stroke="#3b82f6" strokeWidth={1} opacity={0.7} />
      {/* price */}
      <path d={line(closes)} fill="none" stroke={up ? "#22c55e" : "#ef4444"} strokeWidth={1.6} />
      {/* trade-level guides */}
      {guides.map((g) => (
        <g key={g.label}>
          <line x1={0} x2={plotW} y1={y(g.v)} y2={y(g.v)} stroke={g.color} strokeWidth={1} strokeDasharray={g.dash} opacity={0.8} />
          <text x={plotW + 4} y={y(g.v) + 3} fill={g.color} fontSize={10} fontFamily="ui-monospace, monospace">
            {g.label} {g.v}
          </text>
        </g>
      ))}
      {/* price axis: hi/lo */}
      <text x={plotW + 4} y={y(max) + 3} fill="#8b94a7" fontSize={10} fontFamily="ui-monospace, monospace">{max.toFixed(0)}</text>
      <text x={plotW + 4} y={y(min) + 3} fill="#8b94a7" fontSize={10} fontFamily="ui-monospace, monospace">{min.toFixed(0)}</text>
    </svg>
  );
}
