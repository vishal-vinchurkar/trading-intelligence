"""Does liquidity/smart-money have edge? — the honest test before touching the score.

Owner's rule: research first. This walks every US name point-in-time, fires each
liquidity detector (indicators/liquidity.py), and measures the forward return after
the signal — entry at the NEXT open (you can't trade the signal bar's close), held
H days, net of cost, versus SPY over the same window. A baseline of random-timed
entries is included so "edge" means *beats just being in the market*, not just
">0". Bull detectors should beat baseline to the upside; bear detectors should
precede underperformance (a short edge). Nothing here is folded into the conviction
score — that's a separate decision, only if the edge is real.

Run:
  PYTHONPATH=. python -m quant.liquidity_backtest
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from data import universe
from data.backfill import load_cached
from indicators import liquidity as liq
from quant.backtest import COST_BPS

RESULTS_PATH = Path(__file__).parent / "liquidity_results.json"
HORIZON = 10          # trading days held after the signal
MIN_SPACING = 5       # min bars between counted signals (limit overlap/autocorr)
COST = COST_BPS["US"] / 1e4


def _fwd_returns(df: pd.DataFrame, spy: pd.DataFrame, mask: pd.Series) -> list[dict]:
    o, c = df["open"].to_numpy(), df["close"].to_numpy()
    idx = np.flatnonzero(mask.to_numpy())
    out, last = [], -10**9
    for i in idx:
        if i < 20 or i + 1 + HORIZON >= len(df) or i - last < MIN_SPACING:
            continue
        last = i
        entry, exit_px = float(o[i + 1]), float(c[i + 1 + HORIZON])
        if entry <= 0:
            continue
        net = (exit_px / entry - 1.0) - COST
        b = _spy_ret(spy, df.index[i + 1])
        out.append({"net": net, "alpha": (net - b) if b is not None else None})
    return out


def _spy_ret(spy: pd.DataFrame, entry_date: pd.Timestamp) -> float | None:
    pos = spy.index.searchsorted(entry_date)
    if pos + HORIZON >= len(spy):
        return None
    return float(spy["close"].iloc[pos + HORIZON] / spy["open"].iloc[pos] - 1.0)


def _baseline(df: pd.DataFrame, spy: pd.DataFrame) -> list[dict]:
    """Random-timed entries (every MIN_SPACING bars) — the 'just be in the market' bar."""
    mask = pd.Series(False, index=df.index)
    mask.iloc[20:len(df) - HORIZON - 1:MIN_SPACING] = True
    return _fwd_returns(df, spy, mask)


def _stats(rows: list[dict]) -> dict:
    if not rows:
        return {"n": 0}
    net = np.array([r["net"] for r in rows])
    alpha = np.array([r["alpha"] for r in rows if r["alpha"] is not None])
    return {
        "n": int(len(net)),
        "win_pct": round(float((net > 0).mean()) * 100, 1),
        "mean_net_pct": round(float(net.mean()) * 100, 3),
        "mean_alpha_vs_spy_pct": round(float(alpha.mean()) * 100, 3) if alpha.size else None,
        "beat_spy_pct": round(float((alpha > 0).mean()) * 100, 1) if alpha.size else None,
    }


def run() -> dict:
    syms = universe.symbols("US")
    spy = load_cached("SPY")
    detectors = {**liq.BULL_DETECTORS, **liq.BEAR_DETECTORS}
    collected: dict[str, list] = {k: [] for k in detectors}
    baseline: list[dict] = []

    for s in syms:
        df = load_cached(s)
        if df is None or len(df) < 260:
            continue
        baseline += _baseline(df, spy)
        for name, fn in detectors.items():
            collected[name] += _fwd_returns(df, spy, fn(df).fillna(False))

    base = _stats(baseline)
    results = {name: _stats(rows) for name, rows in collected.items()}

    # Edge = beats baseline mean return (bull) / undershoots it (bear).
    for name, st in results.items():
        if st.get("n", 0) and base.get("n"):
            edge = st["mean_net_pct"] - base["mean_net_pct"]
            is_bear = name in liq.BEAR_DETECTORS
            st["vs_baseline_pct"] = round(edge, 3)
            st["has_edge"] = (edge < -0.10) if is_bear else (edge > 0.10)

    out = {
        "meta": {
            "what": "Forward return after each liquidity detector vs a random-entry baseline.",
            "horizon_days": HORIZON, "min_spacing": MIN_SPACING,
            "universe": "US", "names": int(sum(1 for s in syms if load_cached(s) is not None)),
            "note": "Entry = next open after signal, net of US cost, vs SPY same window. "
                    "Point-in-time. NOT yet in the conviction score — research only. Not advice.",
        },
        "baseline_random_entry": base,
        "detectors": results,
    }
    RESULTS_PATH.write_text(json.dumps(out, indent=2))
    return out


def _row(name: str, s: dict) -> str:
    if not s.get("n"):
        return f"{name:22} (no signals)"
    edge = s.get("vs_baseline_pct")
    flag = "  <-- EDGE" if s.get("has_edge") else ""
    return (f"{name:22} n={s['n']:>5}  win {s['win_pct']:>5}%  net {str(s['mean_net_pct'])+'%':>8}  "
            f"alpha {str(s['mean_alpha_vs_spy_pct'])+'%':>8}  vsBase {str(edge)+'%':>8}{flag}")


def _print(r: dict) -> None:
    print(f"\nLiquidity / smart-money edge test — {r['meta']['names']} US names, {r['meta']['horizon_days']}d hold\n")
    print("  " + _row("BASELINE (random)", r["baseline_random_entry"]))
    print("\nBULL detectors (want net > baseline):")
    for n in liq.BULL_DETECTORS:
        print("  " + _row(n, r["detectors"][n]))
    print("\nBEAR detectors (want net < baseline — a short edge):")
    for n in liq.BEAR_DETECTORS:
        print("  " + _row(n, r["detectors"][n]))


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    _print(run())
    print(f"\nSaved -> {RESULTS_PATH}")
