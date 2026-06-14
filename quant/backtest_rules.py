"""Rule-based backtest — validate the trade we ACTUALLY show, not a proxy.

The hold-to-horizon backtest (backtest.py) answers "does a high score precede
gains." But the dashboard tells you to enter, stop at 2xATR, and target the
nearest resistance. Those are a different strategy with a different outcome
distribution. This module closes that gap: at every signal it builds the SAME
trade construct the app shows (quant.trade.build), then walks the tape forward
bar-by-bar and exits on whichever comes first — stop, target, or a time-stop —
netting realistic costs. The result is the honest per-trade expectancy of the
system exactly as specified.

Point-in-time + honest by construction:
  • entry = NEXT session's open (you can't trade the close that fired the signal)
  • stop/target computed from data available AT the signal (ATR + swing S/R)
  • if a bar's range spans both stop and target, assume STOP first (worst case)
  • costs netted per market; last 12 months held out-of-sample

Run:
  PYTHONPATH=. python -m quant.backtest_rules
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from data import universe
from data.backfill import load_cached
from indicators import technical as ta
from quant import trade as qtrade
from quant.backtest import COST_BPS, DEFAULT_COST_BPS, OOS_MONTHS, score_series
from quant.score import label_for

STEP = 5            # trading days between candidate signals (limits overlap)
MAX_HOLD = 20       # time-stop: exit at the close after this many sessions
RESULTS_PATH = Path(__file__).parent / "backtest_rules_results.json"
TRADEABLE = ("STRONG_BUY", "BUY", "STRONG_SELL", "SELL")


def _simulate_symbol(sym: str, slip_bps: float = 0.0) -> list[dict]:
    df = load_cached(sym)
    if df is None or len(df) < 260:
        return []
    market = universe.market_of(sym)
    cost = COST_BPS.get(market, DEFAULT_COST_BPS) / 1e4
    slip = slip_bps / 1e4  # execution shortfall applied to BOTH legs, on top of cost
    bench = load_cached(universe.benchmark_for(sym))
    bc = bench["close"] if bench is not None else None
    ss = score_series(df, bc)

    atr = ta.atr(df)
    o, h, l, c = (df[col].to_numpy() for col in ("open", "high", "low", "close"))
    trades = []
    start, end = 200, len(df) - MAX_HOLD - 2
    for i in range(start, end, STEP):
        sc = ss["score"].iloc[i]
        if pd.isna(sc):
            continue
        band = label_for(float(sc))
        direction = qtrade.direction_for(band)
        if band not in TRADEABLE or direction == "none":
            continue
        a = float(atr.iloc[i])
        if not np.isfinite(a) or a <= 0:
            continue
        # Same construct the dashboard shows — but anchored to the next open.
        entry = float(o[i + 1])
        sup, res = ta.support_resistance(df.iloc[: i + 1])
        tr = qtrade.build(entry, a, sup, res, direction)
        if tr is None:
            continue

        stop, target = tr["stop"], tr["target"]
        exit_px, reason, exit_bar = None, "time", min(i + MAX_HOLD, len(df) - 1)
        for t in range(i + 1, min(i + 1 + MAX_HOLD, len(df))):
            if direction == "long":
                if l[t] <= stop:
                    exit_px, reason, exit_bar = stop, "stop", t; break
                if h[t] >= target:
                    exit_px, reason, exit_bar = target, "target", t; break
            else:  # short
                if h[t] >= stop:
                    exit_px, reason, exit_bar = stop, "stop", t; break
                if l[t] <= target:
                    exit_px, reason, exit_bar = target, "target", t; break
        if exit_px is None:
            exit_px = float(c[exit_bar])

        # Slippage: you fill WORSE than the trigger level on both legs — pay up on
        # entry, give up on exit. Levels still trigger off the raw tape; only the
        # realised fill price degrades. Applied on top of the per-market cost.
        if direction == "long":
            entry_fill, exit_fill = entry * (1 + slip), exit_px * (1 - slip)
            gross = exit_fill / entry_fill - 1.0
        else:
            entry_fill, exit_fill = entry * (1 - slip), exit_px * (1 + slip)
            gross = entry_fill / exit_fill - 1.0
        net = gross - cost
        trades.append({
            "symbol": sym, "market": market, "date": ss.index[i], "band": band,
            "direction": direction, "rr": tr["risk_reward"], "actionable": tr["actionable"],
            "net": float(net), "gross": float(gross), "reason": reason,
            "held": exit_bar - (i + 1),
            "entry_date": df.index[i + 1], "exit_date": df.index[exit_bar],
        })
    return trades


def _stats(t: pd.DataFrame) -> dict:
    if not len(t):
        return {"n": 0}
    net = t["net"]
    wins, losses = net[net > 0], net[net <= 0]
    pf = float(wins.sum() / -losses.sum()) if len(losses) and losses.sum() != 0 else None
    # NOTE: no "max drawdown" here — these trades OVERLAP across names, so a
    # cumulative sum of per-trade returns is not a valid equity curve. True
    # portfolio drawdown comes from the position-sized equity sim (quant.portfolio).
    return {
        "n": int(len(t)),
        "win_rate": round(float((net > 0).mean()) * 100, 1),
        "expectancy_pct": round(float(net.mean()) * 100, 3),
        "avg_win_pct": round(float(wins.mean()) * 100, 2) if len(wins) else None,
        "avg_loss_pct": round(float(losses.mean()) * 100, 2) if len(losses) else None,
        "profit_factor": None if pf is None else round(pf, 2),
        "worst_trade_pct": round(float(net.min()) * 100, 1),
        "avg_hold_days": round(float(t["held"].mean()), 1),
        "exit_mix": {k: int(v) for k, v in t["reason"].value_counts().items()},
    }


def _slice(t: pd.DataFrame, split: pd.Timestamp) -> dict:
    out = {"all": _stats(t), "in_sample": _stats(t[t["date"] <= split]),
           "out_of_sample": _stats(t[t["date"] > split])}
    # Actionable-only (R:R ≥ 1.5) — does the gate the dashboard enforces add value?
    out["actionable_only"] = _stats(t[t["actionable"]])
    return out


def run() -> dict:
    all_t = []
    for s in universe.symbols():
        all_t.extend(_simulate_symbol(s))
    t = pd.DataFrame(all_t)
    t["date"] = pd.to_datetime(t["date"])
    split = t["date"].max() - pd.DateOffset(months=OOS_MONTHS)

    longs = t[t["direction"] == "long"]
    result = {
        "meta": {
            "trades": int(len(t)),
            "symbols": int(t["symbol"].nunique()),
            "date_range": [str(t["date"].min().date()), str(t["date"].max().date())],
            "oos_split": str(split.date()),
            "rule": f"entry=next open, stop=2xATR, target=nearest resistance (fallback 4xATR), "
                    f"time-stop={MAX_HOLD}d; costs US {COST_BPS['US']}bps / India {COST_BPS['India']}bps",
            "note": "Simulates the exact trade the dashboard shows. Net of costs, "
                    "point-in-time, stop-before-target on ambiguous bars. Not financial advice.",
        },
        "long_all": _slice(longs, split),
        "by_market_long": {m: _slice(longs[longs["market"] == m], split)
                           for m in sorted(longs["market"].dropna().unique())},
        "by_band": {b: _slice(t[t["band"] == b], split) for b in TRADEABLE},
    }
    RESULTS_PATH.write_text(json.dumps(result, indent=2))
    return result


def _row(name: str, s: dict) -> str:
    if s.get("n", 0) == 0:
        return f"{name:22} (no trades)"
    return (f"{name:22} n={s['n']:>5}  win {s['win_rate']:>5}%  exp {str(s['expectancy_pct'])+'%':>8}  "
            f"PF {str(s['profit_factor']):>5}  worst {str(s['worst_trade_pct'])+'%':>7}  hold {s['avg_hold_days']}d")


def _print(r: dict) -> None:
    m = r["meta"]
    print(f"\nRule-based backtest: {m['trades']} trades · {m['symbols']} names · {m['date_range'][0]}→{m['date_range'][1]}")
    print(f"Rule: {m['rule']}\n")
    print("LONGS — all / in-sample / out-of-sample / actionable-only (R:R≥1.5):")
    for k in ["all", "in_sample", "out_of_sample", "actionable_only"]:
        print("  " + _row(k, r["long_all"][k]))
    print("\nLONGS by market (out-of-sample):")
    for mkt, sl in r["by_market_long"].items():
        print("  " + _row(mkt, sl["out_of_sample"]))
    print("\nBy band (all):")
    for b, sl in r["by_band"].items():
        print("  " + _row(b, sl["all"]))


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    _print(run())
    print(f"\nSaved → {RESULTS_PATH}")
