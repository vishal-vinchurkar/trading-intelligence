import type { Alignment, Direction, Signal, Verdict } from "./types";

// Tailwind classes keyed by verdict/signal. Centralised so the SignalCard,
// detail page, and badges stay visually consistent.

export const verdictStyles: Record<Verdict, { text: string; ring: string; chip: string }> = {
  BUY: { text: "text-bull", ring: "ring-bull/40", chip: "bg-bull/15 text-bull" },
  SELL: { text: "text-bear", ring: "ring-bear/40", chip: "bg-bear/15 text-bear" },
  HOLD: { text: "text-neutral", ring: "ring-neutral/40", chip: "bg-neutral/15 text-neutral" },
  WATCH: { text: "text-watch", ring: "ring-watch/40", chip: "bg-watch/15 text-watch" },
};

export function signalChip(signal: Signal | null): string {
  switch (signal) {
    case "BULLISH":
      return "bg-bull/15 text-bull";
    case "BEARISH":
      return "bg-bear/15 text-bear";
    default:
      return "bg-neutral/15 text-neutral";
  }
}

export function alignmentChip(a: Alignment | null): string {
  switch (a) {
    case "ALIGNED":
      return "bg-bull/15 text-bull";
    case "CONFLICTED":
      return "bg-bear/15 text-bear";
    default:
      return "bg-neutral/15 text-neutral";
  }
}

export function directionArrow(d: Direction | undefined): string {
  if (d === "UP") return "▲";
  if (d === "DOWN") return "▼";
  return "▬";
}

export function directionColor(d: Direction | undefined): string {
  if (d === "UP") return "text-bull";
  if (d === "DOWN") return "text-bear";
  return "text-muted";
}

export function confidencePct(c: number | null): string {
  if (c == null) return "—";
  // Accept either 0–1 floats or already-percent values.
  const pct = c <= 1 ? c * 100 : c;
  return `${Math.round(pct)}%`;
}

export function formatWhen(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}
