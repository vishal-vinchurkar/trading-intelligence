"use client";

import { useCallback, useEffect, useState } from "react";
import { scan } from "./scan";

// Personal watchlist in the browser — no login, no DB. Seeded from the scan's
// default favourites, then owned by localStorage once the user starts pinning.
const KEY = "sovian.watchlist.v1";

export function useWatchlist() {
  // Start from the scan defaults so server-render and first paint agree; reconcile
  // with localStorage on mount.
  const [symbols, setSymbols] = useState<string[]>(scan.favourites);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(KEY);
      if (stored) setSymbols(JSON.parse(stored));
    } catch {
      /* ignore malformed storage */
    }
  }, []);

  const persist = (next: string[]) => {
    setSymbols(next);
    try {
      localStorage.setItem(KEY, JSON.stringify(next));
    } catch {
      /* ignore quota/availability */
    }
  };

  const toggle = useCallback((sym: string) => {
    setSymbols((prev) => {
      const next = prev.includes(sym) ? prev.filter((s) => s !== sym) : [...prev, sym];
      try {
        localStorage.setItem(KEY, JSON.stringify(next));
      } catch {
        /* ignore */
      }
      return next;
    });
  }, []);

  const has = useCallback((sym: string) => symbols.includes(sym), [symbols]);

  return { symbols, toggle, has, persist };
}
