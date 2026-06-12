"""10-year daily history backfill — the feature store the backtest reads.

yfinance gives 10+ years of daily bars free and keyless for both US and India,
so this is the cheap workhorse: pull once, cache locally as CSV, and the
backtest engine computes point-in-time signals off the cache (fast, offline,
no rate limits). Optionally syncs to Supabase `price_history` for the live
dashboard.

Run:
  PYTHONPATH=. python -m data.backfill                 # whole universe + benchmarks
  PYTHONPATH=. python -m data.backfill AAPL RELIANCE.NS # specific names
  PYTHONPATH=. python -m data.backfill --sync           # also push to Supabase
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yfinance as yf

from data import universe

CACHE_DIR = Path(__file__).parent / "cache"
DEFAULT_YEARS = 10


def cache_path(symbol: str) -> Path:
    # Symbols can contain '.' and '^'; keep filenames filesystem-safe.
    safe = symbol.replace("^", "_idx_").replace("/", "_")
    return CACHE_DIR / f"{safe}.csv"


def fetch_history(symbol: str, years: int = DEFAULT_YEARS) -> pd.DataFrame:
    """Daily OHLCV, normalised (lowercase cols, oldest→newest, naive DatetimeIndex)."""
    df = yf.Ticker(symbol).history(period=f"{years}y", interval="1d", auto_adjust=False)
    if df is None or df.empty:
        raise RuntimeError(f"No history for {symbol!r}")
    df = df.rename(
        columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
    )[["open", "high", "low", "close", "volume"]]
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df = df.sort_index()
    df["volume"] = df["volume"].fillna(0).astype("int64")
    return df.dropna(subset=["close"])


def load_cached(symbol: str) -> pd.DataFrame | None:
    """Read a cached series back as a normalised OHLCV frame, or None if absent."""
    p = cache_path(symbol)
    if not p.exists():
        return None
    df = pd.read_csv(p, parse_dates=["date"]).set_index("date")
    df.index.name = None
    return df


def backfill_one(symbol: str, years: int = DEFAULT_YEARS) -> int:
    df = fetch_history(symbol, years)
    CACHE_DIR.mkdir(exist_ok=True)
    out = df.copy()
    out.index.name = "date"
    out.to_csv(cache_path(symbol))
    return len(df)


def backfill_all(symbols: list[str], years: int = DEFAULT_YEARS, sync: bool = False) -> None:
    # Include benchmarks so relative strength / beta have their reference series.
    targets = list(dict.fromkeys(symbols + list(universe.BENCHMARKS.values())))
    rows_by_symbol: dict[str, int] = {}
    for sym in targets:
        try:
            n = backfill_one(sym, years)
            rows_by_symbol[sym] = n
            print(f"[ok]   {sym:14} {n} rows")
        except Exception as e:  # noqa: BLE001 — yfinance fails are expected/per-symbol
            print(f"[skip] {sym:14} {e}")
    print(f"\nCached {len(rows_by_symbol)}/{len(targets)} symbols → {CACHE_DIR}")

    if sync:
        _sync_to_supabase(rows_by_symbol.keys())


def _sync_to_supabase(symbols) -> None:
    """Upsert cached bars into Supabase `price_history` (for the live dashboard).

    Requires the price_history table from orchestrator/schema_v2.sql and the
    service-role key. Backtests do NOT need this — they read the local cache.
    """
    import os

    if not os.environ.get("SUPABASE_URL"):
        print("[sync] SUPABASE_URL not set — skipping Supabase sync.")
        return
    from orchestrator import supabase_client as db

    client = db.get_client()
    for sym in symbols:
        df = load_cached(sym)
        if df is None:
            continue
        records = [
            {
                "symbol": sym,
                "date": idx.strftime("%Y-%m-%d"),
                "open": float(r.open),
                "high": float(r.high),
                "low": float(r.low),
                "close": float(r.close),
                "volume": int(r.volume),
            }
            for idx, r in df.iterrows()
        ]
        # Chunk to stay well under request-size limits.
        for i in range(0, len(records), 1000):
            client.table("price_history").upsert(
                records[i : i + 1000], on_conflict="symbol,date"
            ).execute()
        print(f"[sync] {sym}: {len(records)} bars → Supabase")


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill daily price history into the local cache.")
    parser.add_argument("symbols", nargs="*", help="Specific symbols; default = whole universe.")
    parser.add_argument("--years", type=int, default=DEFAULT_YEARS)
    parser.add_argument("--sync", action="store_true", help="Also upsert into Supabase price_history.")
    args = parser.parse_args()

    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    syms = args.symbols or universe.symbols()
    backfill_all(syms, years=args.years, sync=args.sync)


if __name__ == "__main__":
    sys.exit(main())
