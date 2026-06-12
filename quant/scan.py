"""Scan the whole universe → the ranked 'Top Signals' the dashboard shows.

For every name: compute the conviction score, size the volatility, build the
trade construct, and attach the band's BACKTESTED hit-rate (the honest, out-of-
sample calibration — this is what the dashboard shows instead of an LLM's made-up
confidence). The user never browses the universe; they read the top of this list
and their pinned favourites.

Writes quant/latest_scan.json, which the Next.js dashboard reads directly (no DB
migration needed to demo). A later cron can also push to Supabase.

Run:
  PYTHONPATH=. python -m quant.scan
"""

from __future__ import annotations

import json
from pathlib import Path

from data import universe
from data.backfill import load_cached
from indicators import technical as ta
from quant import score as qscore
from quant import trade as qtrade

OUT_PATH = Path(__file__).parent / "latest_scan.json"
BACKTEST_PATH = Path(__file__).parent / "backtest_results.json"

# The user's pinned watchlist — always shown front-and-centre regardless of score.
# Edit freely; these must exist in data/universe.py.
FAVOURITES = ["AAPL", "RELIANCE.NS"]


def _backtest() -> dict:
    return json.loads(BACKTEST_PATH.read_text()) if BACKTEST_PATH.exists() else {}


def _calibration(band: str, market: str | None, bt: dict) -> dict:
    """The band's backtested 15d hit-rate / alpha — validated on THIS market's own
    history (US signals on US, India on India), falling back to the blended set."""
    src = bt.get("by_market", {}).get(market) or bt
    ins = src.get("in_sample", {}).get(band, {})
    oos = src.get("out_of_sample", {}).get(band, {})
    return {
        "band": band,
        "market": market,
        "hit_rate_15d": ins.get("15d", {}).get("hit_rate"),
        "alpha_15d_pct": ins.get("15d", {}).get("mean_excess_pct"),
        "samples": ins.get("n"),
        "oos_hit_rate_15d": oos.get("15d", {}).get("hit_rate"),
        "oos_alpha_15d_pct": oos.get("15d", {}).get("mean_excess_pct"),
    }


def scan_one(symbol: str, bt: dict) -> dict | None:
    df = load_cached(symbol)
    if df is None or len(df) < 200:
        return None
    market = universe.market_of(symbol)
    bench = load_cached(universe.benchmark_for(symbol))
    bc = bench["close"] if bench is not None else None

    ind = ta.compute_all(df)
    sc = qscore.score(df, bc)
    direction = qtrade.direction_for(sc["label"])
    trade = qtrade.build(
        ind["last_close"], ind["volatility"]["atr_14"],
        ind["key_levels"]["support"], ind["key_levels"]["resistance"], direction,
    )
    return {
        "symbol": symbol,
        "market": market,
        "sector": universe.sector_of(symbol),
        "as_of": str(df.index[-1].date()),
        "last_close": ind["last_close"],
        "score": sc["score"],
        "label": sc["label"],
        "core": sc["core"],
        "conviction": round(abs(sc["score"] - 50), 1),  # distance from neutral → ranking key
        "components": sc["components"],
        "timing": sc["timing"],
        "volatility": ind["volatility"],
        "expected_move": ind["expected_move"],
        "key_levels": ind["key_levels"],
        "trade": trade,
        "calibration": _calibration(sc["label"], market, bt),
        "is_favourite": symbol in FAVOURITES,
    }


def run() -> dict:
    bt = _backtest()
    signals = [s for s in (scan_one(sym, bt) for sym in universe.symbols()) if s]
    # Rank by conviction (distance from neutral): strongest longs and shorts float up.
    signals.sort(key=lambda s: s["conviction"], reverse=True)
    as_of = max((s["as_of"] for s in signals), default=None)

    bt_meta = dict(bt.get("meta", {}))
    # Per-market edge so the dashboard banner can show US vs India separately.
    bt_meta["by_market"] = {
        mkt: {
            "long_short_edge_15d_pct": mv.get("long_short_edge_15d_pct"),
            "samples": mv.get("samples"),
            "symbols": mv.get("symbols"),
        }
        for mkt, mv in bt.get("by_market", {}).items()
    }
    result = {
        "as_of": as_of,
        "universe_size": len(signals),
        "backtest_meta": bt_meta,
        "favourites": FAVOURITES,
        "signals": signals,
    }
    OUT_PATH.write_text(json.dumps(result, indent=2))
    # Mirror into the dashboard so the Next.js app bundles the latest scan at build
    # time (no DB round-trip needed to demo). A later cron can push to Supabase too.
    dash = Path(__file__).parent.parent / "dashboard" / "data" / "scan.json"
    dash.parent.mkdir(parents=True, exist_ok=True)
    dash.write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    r = run()
    print(f"Scanned {r['universe_size']} names · as of {r['as_of']}\n")
    print(f"{'rank':>4}  {'symbol':12} {'score':>6} {'label':11} {'15d hit':>8} {'R:R':>5} {'act':>4}")
    for i, s in enumerate(r["signals"][:12], 1):
        cal = s["calibration"].get("hit_rate_15d")
        rr = s["trade"]["risk_reward"] if s["trade"] else None
        act = ("Y" if s["trade"] and s["trade"]["actionable"] else "—")
        fav = "★" if s["is_favourite"] else " "
        print(f"{i:>4}{fav} {s['symbol']:12} {s['score']:>6} {s['label']:11} {str(cal):>8} {str(rr):>5} {act:>4}")
    print(f"\nSaved → {OUT_PATH}")
