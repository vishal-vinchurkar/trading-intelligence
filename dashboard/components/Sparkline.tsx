import type { PricePoint } from "@/lib/scan";

// Dependency-free inline-SVG price sparkline. Coloured by net direction over the
// window so a card reads "up and to the right" (or not) at a glance.
export function Sparkline({
  history,
  width = 300,
  height = 40,
}: {
  history: PricePoint[];
  width?: number;
  height?: number;
}) {
  if (!history || history.length < 2) return null;
  const closes = history.map((p) => p.c);
  const min = Math.min(...closes);
  const max = Math.max(...closes);
  const span = max - min || 1;
  const n = closes.length;

  const x = (i: number) => (i / (n - 1)) * width;
  const y = (c: number) => height - ((c - min) / span) * (height - 4) - 2;

  const path = closes.map((c, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(c).toFixed(1)}`).join(" ");
  const up = closes[n - 1] >= closes[0];
  const stroke = up ? "#22c55e" : "#ef4444";

  return (
    <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height} preserveAspectRatio="none" aria-hidden>
      <path d={path} fill="none" stroke={stroke} strokeWidth={1.5} strokeLinejoin="round" />
    </svg>
  );
}
