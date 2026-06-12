"""Backtest the quant score over 10 years — the proof behind 'perfect BUY/SELL'.

For every name and (nearly) every day, compute the conviction score using ONLY
data available up to that day, then look forward 5/15/30 trading days and record
the realised return. Aggregate by score band → a hit-rate and mean forward return
that say, in numbers, whether a high score actually preceded gains.

Honesty rails:
  • Point-in-time: forward returns use shift(-h); scores use only past data.
  • Out-of-sample: the most recent 12 months are held out and reported separately,
    so we can see the edge on data the logic never informed.
  • Overlap: we step every STEP days to limit overlapping forward windows.
  • Price-only: the backtested score is technical (no fundamental look-ahead).

The vectorised scorer here is checked against quant.score.score() on the latest
row (see _consistency_check) so the live and backtested logic can't silently drift.

Run:
  PYTHONPATH=. python -m quant.backtest            # whole universe, writes results JSON
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from data import universe
from data.backfill import load_cached
from indicators import technical as ta
from quant.score import WEIGHTS, label_for, score as point_score

HORIZONS = [5, 15, 30]
STEP = 5                  # trading days between evaluation points (limits overlap)
OOS_MONTHS = 12           # most recent N months held out-of-sample
EXEC_LAG = 1              # you see the signal on close[i] but trade the NEXT session

# Realistic round-trip transaction cost in basis points (1 bp = 0.01%). The signal
# is only worth trading if its edge survives THIS. US large-caps on a zero-commission
# broker are mostly spread+slippage; India delivery carries STT + brokerage + stamp.
# Deliberately conservative — better to under-promise the net edge than oversell it.
COST_BPS = {"US": 10.0, "India": 35.0}
DEFAULT_COST_BPS = 20.0

RESULTS_PATH = Path(__file__).parent / "backtest_results.json"


def _squash_series(x: pd.Series, scale: float) -> pd.Series:
    return 50.0 + 50.0 * np.tanh(x / scale)


def score_series(df: pd.DataFrame, bench: pd.Series | None) -> pd.DataFrame:
    """Vectorised conviction score for EVERY date in df. Mirrors quant.score logic."""
    close = df["close"]
    s50 = ta.sma(close, 50)
    s200 = ta.sma(close, 200)

    # Trend (binary stack, vectorised)
    trend = pd.Series(50.0, index=close.index)
    trend += np.where(close > s50, 15, -15)
    has200 = s200.notna()
    trend += np.where(has200, np.where(close > s200, 15, -15), 0)
    trend += np.where(has200, np.where(s50 > s200, 20, -20), 0)
    trend = trend.clip(0, 100)

    # Momentum: 6m return + MACD histogram sign
    r6 = close / close.shift(126) - 1
    macd_line, signal_line, _ = ta.macd(close)
    hist = macd_line - signal_line
    momentum = (_squash_series(r6, 0.25) + np.where(hist > 0, 5, -5)).clip(0, 100)

    # Relative strength: 3m excess return vs benchmark
    if bench is not None:
        b = bench.reindex(close.index).ffill()
        excess = (close / close.shift(63) - 1) - (b / b.shift(63) - 1)
        relstr = _squash_series(excess, 0.10)
    else:
        relstr = pd.Series(50.0, index=close.index)

    # Flow: accumulation/distribution
    roll5 = df["volume"].rolling(5).mean()
    roll20 = df["volume"].rolling(20).mean()
    pchg = close - close.shift(5)
    flow = pd.Series(50.0, index=close.index)
    flow = flow.mask((roll5 > roll20) & (pchg > 0), 70.0)
    flow = flow.mask((roll5 > roll20) & (pchg < 0), 30.0)

    core = (
        WEIGHTS["trend"] * trend
        + WEIGHTS["momentum"] * momentum
        + WEIGHTS["relative_strength"] * relstr
        + WEIGHTS["flow"] * flow
    )

    # RSI timing modifier (−10..+10)
    rsi_v = ta.rsi(close)
    tmod = pd.Series(0.0, index=close.index)
    tmod = tmod.mask(rsi_v >= 70, -10.0 * ((rsi_v - 70) / 15).clip(upper=1.0))
    tmod = tmod.mask(rsi_v <= 30, +10.0 * ((30 - rsi_v) / 15).clip(upper=1.0))

    final = (core + tmod).clip(0, 100)
    return pd.DataFrame({"close": close, "score": final})


def _consistency_check(sym: str = "AAPL") -> None:
    """Vectorised score on the last row must match the live point-in-time scorer."""
    df = load_cached(sym)
    if df is None:
        return
    bench = load_cached(universe.benchmark_for(sym))
    bc = bench["close"] if bench is not None else None
    vec = float(score_series(df, bc)["score"].iloc[-1])
    live = point_score(df, bc)["score"]
    assert abs(vec - live) < 0.5, f"scorer drift on {sym}: vec={vec} live={live}"


def backtest_symbol(sym: str) -> pd.DataFrame:
    df = load_cached(sym)
    if df is None or len(df) < 260 + max(HORIZONS):
        return pd.DataFrame()
    bench = load_cached(universe.benchmark_for(sym))
    bc = bench["close"] if bench is not None else None
    ss = score_series(df, bc)
    # Benchmark aligned to the name's dates — for forward EXCESS returns (alpha).
    b_aligned = bc.reindex(ss.index).ffill() if bc is not None else None

    rows = []
    # Start at 200 (need 200DMA); stop early enough to have the longest forward window
    # AND the 1-bar execution lag (you can't trade the close that generated the signal).
    start, end = 200, len(df) - max(HORIZONS) - EXEC_LAG - 1
    for i in range(start, end, STEP):
        sc = ss["score"].iloc[i]
        if pd.isna(sc):
            continue
        e = i + EXEC_LAG                 # entry bar — the session AFTER the signal
        c0 = ss["close"].iloc[e]
        rec = {"symbol": sym, "market": universe.market_of(sym), "date": ss.index[i],
               "score": float(sc), "band": label_for(float(sc))}
        for h in HORIZONS:
            fwd = float(ss["close"].iloc[e + h] / c0 - 1.0)
            rec[f"fwd_{h}d"] = fwd
            if b_aligned is not None and not pd.isna(b_aligned.iloc[e]):
                bfwd = float(b_aligned.iloc[e + h] / b_aligned.iloc[e] - 1.0)
                rec[f"ex_{h}d"] = fwd - bfwd  # gross alpha vs benchmark
            else:
                rec[f"ex_{h}d"] = fwd
        rows.append(rec)
    return pd.DataFrame(rows)


def _band_stats(g: pd.DataFrame) -> dict:
    """Per-band, per-horizon stats on NET-of-cost alpha P&L.

    net_{h}d is the trade's realised alpha after the round-trip cost and the
    1-bar execution lag, direction-aware (a short profits when the name lags).
    Hit-rate = share of trades with positive NET alpha. We keep the gross alpha
    too so the cost drag is visible."""
    out = {"n": int(len(g))}
    for h in HORIZONS:
        net, ex = g[f"net_{h}d"].dropna(), g[f"ex_{h}d"]
        hit = (net > 0).mean() if len(net) else float("nan")
        out[f"{h}d"] = {
            "hit_rate": None if pd.isna(hit) else round(float(hit) * 100, 1),       # NET
            "net_alpha_pct": None if not len(net) else round(float(net.mean()) * 100, 2),
            "gross_alpha_pct": round(float(ex.mean()) * 100, 2),
            "mean_abs_pct": round(float(g[f"fwd_{h}d"].mean()) * 100, 2),
        }
    return out


BANDS = ["STRONG_BUY", "BUY", "NEUTRAL", "SELL", "STRONG_SELL"]


def _by_band(frame: pd.DataFrame) -> dict:
    return {b: (_band_stats(g) if len(g := frame[frame["band"] == b]) else {"n": 0}) for b in BANDS}


def _edge(frame: pd.DataFrame) -> float | None:
    # Average NET alpha per directional trade at 15d (after cost + execution lag).
    # This is the honest "is there money here per trade" number.
    net = frame["net_15d"].dropna()
    return round(float(net.mean()) * 100, 2) if len(net) else None


def aggregate_frame(frame: pd.DataFrame, split_date: pd.Timestamp) -> dict:
    """In-/out-of-sample band stats + long/short edge for one slice (all, or one market)."""
    return {
        "samples": int(len(frame)),
        "symbols": int(frame["symbol"].nunique()),
        "long_short_edge_15d_pct": _edge(frame),
        "in_sample": _by_band(frame[frame["date"] <= split_date]),
        "out_of_sample": _by_band(frame[frame["date"] > split_date]),
    }


def aggregate(all_rows: pd.DataFrame, split_date: pd.Timestamp) -> dict:
    overall = aggregate_frame(all_rows, split_date)
    by_market = {
        mkt: aggregate_frame(all_rows[all_rows["market"] == mkt], split_date)
        for mkt in sorted(all_rows["market"].dropna().unique())
    }
    return {
        "meta": {
            "samples": overall["samples"],
            "symbols": overall["symbols"],
            "date_range": [str(all_rows["date"].min().date()), str(all_rows["date"].max().date())],
            "oos_split": str(split_date.date()),
            "horizons": HORIZONS,
            "step_days": STEP,
            "long_short_edge_15d_pct": overall["long_short_edge_15d_pct"],
            "cost_bps": COST_BPS,
            "exec_lag_days": EXEC_LAG,
            "note": "NET of round-trip cost (US ~10bps, India ~35bps) and a 1-bar "
                    "execution lag. Hit-rate = share of trades with positive net alpha. "
                    "Price-only, point-in-time, last 12mo out-of-sample. Not financial advice.",
        },
        "in_sample": overall["in_sample"],
        "out_of_sample": overall["out_of_sample"],
        "by_market": by_market,
    }


def run() -> dict:
    _consistency_check()
    frames = [backtest_symbol(s) for s in universe.symbols()]
    frames = [f for f in frames if not f.empty]
    all_rows = pd.concat(frames, ignore_index=True)
    all_rows["date"] = pd.to_datetime(all_rows["date"])

    # Direction-aware NET alpha per trade = gross alpha minus the round-trip cost,
    # flipped for shorts (a short profits when the name lags the index).
    cost = (all_rows["market"].map(COST_BPS).fillna(DEFAULT_COST_BPS)) / 1e4
    long_mask = all_rows["band"].isin(["STRONG_BUY", "BUY"]).to_numpy()
    short_mask = all_rows["band"].isin(["STRONG_SELL", "SELL"]).to_numpy()
    for h in HORIZONS:
        ex = all_rows[f"ex_{h}d"]
        all_rows[f"net_{h}d"] = np.where(
            long_mask, ex - cost, np.where(short_mask, -ex - cost, np.nan)
        )

    split = all_rows["date"].max() - pd.DateOffset(months=OOS_MONTHS)
    result = aggregate(all_rows, split)
    RESULTS_PATH.write_text(json.dumps(result, indent=2))
    return result


def _print(result: dict) -> None:
    m = result["meta"]
    print(f"\nBacktest: {m['samples']} samples · {m['symbols']} names · {m['date_range'][0]}→{m['date_range'][1]}")
    print(f"Avg NET alpha per 15d trade: {m['long_short_edge_15d_pct']}%   "
          f"(cost {m['cost_bps']} bps, {m['exec_lag_days']}-bar lag, OOS split {m['oos_split']})")
    for mkt, mv in result.get("by_market", {}).items():
        print(f"   · {mkt}: net {mv['long_short_edge_15d_pct']}%/trade ({mv['samples']} samples)")
    print("Hit-rate = share of trades with POSITIVE NET alpha. 15d: net alpha | gross alpha.\n")
    for split_name in ["in_sample", "out_of_sample"]:
        print(f"── {split_name.replace('_',' ').upper()} ──")
        print(f"{'band':12} {'n':>6} {'5d hit':>8} {'15d hit':>9} {'30d hit':>9} {'net15':>8} {'gross15':>8}")
        for band, st in result[split_name].items():
            if st.get("n", 0) == 0:
                continue
            h5 = st["5d"]["hit_rate"]; h15 = st["15d"]["hit_rate"]; h30 = st["30d"]["hit_rate"]
            net15 = st["15d"]["net_alpha_pct"]; gr15 = st["15d"]["gross_alpha_pct"]
            print(f"{band:12} {st['n']:>6} {str(h5):>8} {str(h15):>9} {str(h30):>9} {str(net15)+'%':>8} {str(gr15)+'%':>8}")
        print()


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    _print(run())
    print(f"Saved → {RESULTS_PATH}")
