"""Slippage stress test — how much execution shortfall before the edge dies?

The reviewer's fair hit: "0.82% net/trade is plausible but fragile to costs/
slippage which I don't see modeled." Per-market COST_BPS already covers
commission + spread; this isolates the OTHER half — slippage, the gap between the
price that triggers a fill and the price you actually get. It re-runs the EXACT
trade backtest (quant.backtest_rules) on the US-long edge at increasing slippage
(0 → 50 bps, applied to BOTH legs on top of cost) and reports how win-rate,
expectancy and profit factor degrade — and the break-even slippage where the edge
goes to zero. A real-money strategy should survive a few bps; if 5 bps kills it,
it was never tradeable.

Run:
  PYTHONPATH=. python -m quant.slippage
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from data import universe
from quant.backtest import OOS_MONTHS
from quant.backtest_rules import _simulate_symbol, _stats

RESULTS_PATH = Path(__file__).parent / "slippage_results.json"
LEVELS_BPS = [0.0, 2.5, 5.0, 10.0, 25.0, 50.0]


def _us_long_oos(slip_bps: float) -> pd.DataFrame:
    """US-long trades at a given slippage, out-of-sample only (the honest window)."""
    rows = [t for s in universe.symbols("US")
            for t in _simulate_symbol(s, slip_bps=slip_bps) if t["direction"] == "long"]
    t = pd.DataFrame(rows)
    t["date"] = pd.to_datetime(t["date"])
    split = t["date"].max() - pd.DateOffset(months=OOS_MONTHS)
    return t[t["date"] > split]


def run() -> dict:
    rungs = []
    for bps in LEVELS_BPS:
        s = _stats(_us_long_oos(bps))
        rungs.append({
            "slip_bps": bps,
            "win_rate": s.get("win_rate"),
            "expectancy_pct": s.get("expectancy_pct"),
            "profit_factor": s.get("profit_factor"),
            "n": s.get("n"),
        })

    # Break-even slippage: linear interpolation between the rungs that bracket exp=0.
    breakeven = None
    for a, b in zip(rungs, rungs[1:]):
        ea, eb = a["expectancy_pct"], b["expectancy_pct"]
        if ea is not None and eb is not None and ea > 0 >= eb:
            frac = ea / (ea - eb)
            breakeven = round(a["slip_bps"] + frac * (b["slip_bps"] - a["slip_bps"]), 1)
            break
    if breakeven is None and rungs[-1]["expectancy_pct"] is not None and rungs[-1]["expectancy_pct"] > 0:
        breakeven = f">{LEVELS_BPS[-1]:.0f}"  # still positive at the top rung

    base, worst = rungs[0], rungs[-1]
    result = {
        "meta": {
            "what": "US-long out-of-sample edge vs slippage (bps applied to entry AND exit, on top of cost).",
            "levels_bps": LEVELS_BPS,
            "oos_months": OOS_MONTHS,
            "note": "Slippage is additive to per-market commission/spread (COST_BPS). "
                    "Break-even = slippage at which net expectancy hits zero. Not financial advice.",
        },
        "rungs": rungs,
        "breakeven_bps": breakeven,
        "base_expectancy_pct": base["expectancy_pct"],
        "expectancy_at_10bps_pct": next((r["expectancy_pct"] for r in rungs if r["slip_bps"] == 10.0), None),
        "robust": isinstance(breakeven, str) or (isinstance(breakeven, (int, float)) and breakeven >= 10.0),
    }
    RESULTS_PATH.write_text(json.dumps(result, indent=2))
    return result


def _print(r: dict) -> None:
    print(f"\nSlippage stress — {r['meta']['what']}\n")
    print(f"{'slip(bps)':>10} {'win%':>7} {'exp%':>9} {'PF':>6} {'n':>6}")
    for rung in r["rungs"]:
        print(f"{rung['slip_bps']:>10} {str(rung['win_rate']):>7} {str(rung['expectancy_pct']):>9} "
              f"{str(rung['profit_factor']):>6} {str(rung['n']):>6}")
    be = r["breakeven_bps"]
    print(f"\nBreak-even slippage: {be} bps   ({'ROBUST' if r['robust'] else 'FRAGILE'} — "
          f"{'survives ≥10bps' if r['robust'] else 'edge dies under 10bps'})")


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    _print(run())
    print(f"\nSaved → {RESULTS_PATH}")
