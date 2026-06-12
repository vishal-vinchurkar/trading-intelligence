"use client";

import { useMemo, useState } from "react";
import { fmtPrice, scan, type Signal } from "@/lib/scan";

// Search-and-pin any scanned name to the watchlist — including NEUTRAL names that
// never render a card in the decks. Pure client-side over scan.signals (all 55
// scanned names are in the bundle), so no rescan/round-trip. Tickers NOT in the
// universe can't be pinned here — they have no scored data yet; those go in
// data/universe.py + a rescan.
export function TickerSearch({
  has,
  onToggleStar,
}: {
  has: (s: string) => boolean;
  onToggleStar: (s: string) => void;
}) {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);

  const matches = useMemo(() => {
    const needle = q.trim().toUpperCase();
    if (!needle) return [];
    return scan.signals
      .filter(
        (s) =>
          s.symbol.toUpperCase().includes(needle) ||
          s.sector.toUpperCase().includes(needle)
      )
      .sort((a, b) => {
        // Exact/prefix symbol matches first, then alphabetical.
        const ap = a.symbol.toUpperCase().startsWith(needle) ? 0 : 1;
        const bp = b.symbol.toUpperCase().startsWith(needle) ? 0 : 1;
        return ap - bp || a.symbol.localeCompare(b.symbol);
      })
      .slice(0, 8);
  }, [q]);

  const unknown = q.trim().length > 0 && matches.length === 0;

  return (
    <div className="relative">
      <input
        value={q}
        onChange={(e) => {
          setQ(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        placeholder="Add to watchlist — type a ticker or sector (e.g. AAPL, ITC.NS, Energy)"
        className="w-full rounded-lg border border-border bg-panel px-3 py-2 text-sm outline-none placeholder:text-muted/60 focus:border-muted/50"
      />
      {open && (matches.length > 0 || unknown) && (
        <ul className="absolute z-20 mt-1 max-h-80 w-full overflow-auto rounded-lg border border-border bg-panel shadow-xl">
          {matches.map((s: Signal) => {
            const pinned = has(s.symbol);
            return (
              <li key={s.symbol}>
                <button
                  onMouseDown={(e) => e.preventDefault()} // keep focus so onBlur doesn't fire first
                  onClick={() => onToggleStar(s.symbol)}
                  className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm hover:bg-muted/10"
                >
                  <span className="flex items-baseline gap-2">
                    <span className="font-mono font-semibold">{s.symbol}</span>
                    <span className="text-[11px] text-muted">
                      {s.market} · {s.sector} · {fmtPrice(s.market, s.last_close)}
                    </span>
                  </span>
                  <span className="flex items-center gap-2">
                    <span className="rounded bg-border px-1.5 py-0.5 text-[10px] text-muted">
                      {s.label.replace("_", " ")}
                    </span>
                    <span className={pinned ? "text-watch" : "text-muted/40"}>{pinned ? "★" : "☆"}</span>
                  </span>
                </button>
              </li>
            );
          })}
          {unknown && (
            <li className="px-3 py-2 text-[11px] leading-relaxed text-muted">
              <span className="font-mono text-white">{q.trim().toUpperCase()}</span> isn&apos;t in the
              scanned universe yet. The engine only scores names with cached price history — ask to add
              it to <span className="font-mono">data/universe.py</span> and rerun the scan.
            </li>
          )}
        </ul>
      )}
    </div>
  );
}
