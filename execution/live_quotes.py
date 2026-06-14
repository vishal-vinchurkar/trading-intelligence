"""Live-quote layer — near-real-time prices from Alpaca, to match your broker.

The signals are computed on END-OF-DAY closes (that's what's backtestable, and it
must stay that way — see the honesty rule). But the *displayed* price and any
*execution* decision should reflect the live market, not yesterday's close. This
fetches near-real-time trades from Alpaca's market-data API (free IEX feed, same
keys as the paper broker) so the dashboard/CLI can show a live price next to the
EOD close — and quantify the drift between them.

Design boundary (load-bearing): live quotes are for DISPLAY + EXECUTION only.
They never feed the conviction score or any backtest. Stale-data trust comes from
quant.freshness; this is the complementary "what's it doing right now" view.

Run:
  PYTHONPATH=. python -m execution.live_quotes AAPL MSFT SNOW   # compare live vs our close
  PYTHONPATH=. python -m execution.live_quotes                  # whole scan universe
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

DATA_BASE = "https://data.alpaca.markets"
SCAN_PATH = Path(__file__).parent.parent / "quant" / "latest_scan.json"


def _headers() -> dict:
    key, sec = os.environ.get("ALPACA_API_KEY"), os.environ.get("ALPACA_SECRET_KEY")
    if not (key and sec):
        raise RuntimeError("ALPACA_API_KEY / ALPACA_SECRET_KEY not set in .env")
    return {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec}


def latest_quotes(symbols: list[str], feed: str = "iex") -> dict[str, dict]:
    """Latest trade price per symbol via Alpaca snapshots (free IEX feed).

    Returns {symbol: {price, time}}. Symbols Alpaca can't price (e.g. Indian .NS
    names) are simply absent — Alpaca is US equities only."""
    us = [s for s in symbols if "." not in s and "^" not in s]  # Alpaca = US equities
    if not us:
        return {}
    out: dict[str, dict] = {}
    # Chunk to keep the query string sane.
    for i in range(0, len(us), 100):
        chunk = us[i:i + 100]
        q = urllib.parse.urlencode({"symbols": ",".join(chunk), "feed": feed})
        req = urllib.request.Request(f"{DATA_BASE}/v2/stocks/snapshots?{q}", headers=_headers())
        try:
            snaps = json.load(urllib.request.urlopen(req, timeout=20))
        except Exception as e:  # noqa: BLE001
            print(f"[live] snapshot fetch failed for {len(chunk)} syms: {e}")
            continue
        for sym, snap in snaps.items():
            trade = (snap or {}).get("latestTrade") or {}
            if trade.get("p"):
                out[sym] = {"price": float(trade["p"]), "time": trade.get("t")}
    return out


def compare_to_close(symbols: list[str]) -> list[dict]:
    """Live price vs our cached EOD close — surfaces the intraday drift."""
    from data.backfill import load_cached

    live = latest_quotes(symbols)
    rows = []
    for s in symbols:
        df = load_cached(s)
        close = float(df["close"].iloc[-1]) if df is not None and len(df) else None
        lq = live.get(s)
        px = lq["price"] if lq else None
        drift = round((px / close - 1) * 100, 2) if (px and close) else None
        rows.append({"symbol": s, "close": close, "live": px, "drift_pct": drift,
                     "live_time": lq["time"] if lq else None})
    return rows


def main() -> int:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    syms = sys.argv[1:]
    if not syms and SCAN_PATH.exists():
        syms = [s["symbol"] for s in json.loads(SCAN_PATH.read_text())["signals"]][:25]
    rows = compare_to_close(syms)
    print(f"\n{'symbol':8} {'EOD close':>10} {'live':>10} {'drift':>8}")
    for r in rows:
        d = f"{r['drift_pct']:+.2f}%" if r["drift_pct"] is not None else "—"
        live = f"{r['live']:.2f}" if r["live"] is not None else "(no US live)"
        close = f"{r['close']:.2f}" if r["close"] is not None else "—"
        print(f"{r['symbol']:8} {close:>10} {live:>10} {d:>8}")
    print("\nLive = Alpaca IEX last trade. EOD close = our backtest data. "
          "Signals use EOD; live is display/execution only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
