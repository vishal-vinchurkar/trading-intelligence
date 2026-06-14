"""Autonomous decision engine — turn signals into a risk-managed book.

The scan emits signals; the rule backtest proves per-trade expectancy; the equal-
weight portfolio (quant.portfolio) shows a naive account curve. None of that is an
*agent*. This module is the decision brain: given the same US-long entry signals,
it sizes and risk-manages a portfolio autonomously, then backtests the result so we
can see whether the management actually improves risk-adjusted return over naive
equal-weight (and over SPY). It is the controller that will drive live Alpaca
execution once keys land — the backtest here and the live order layer share the
same sizing/risk rules.

Decision rules (all stated, none hidden):
  • Inverse-volatility sizing — lower-vol names get more weight (risk-balanced),
    normalised across open positions.
  • Per-name cap (MAX_WEIGHT) and gross cap (no leverage) — leftover sits in cash.
  • Volatility targeting — scale gross exposure by TARGET_VOL / trailing realised
    portfolio vol, so the book leans out when it gets choppy. Never levers up past 1x.
  • Drawdown circuit-breaker — if the book draws down past DD_HALT from its peak,
    go flat (cash) and stop entering until it recovers to within DD_RESUME. This is
    the "don't let the autonomous agent ride a crash to zero" guardrail.

Costs netted on weight changes. US long-only (the only validated edge). The forward
Alpaca paper ledger remains the unbiased test — this is still a backtest on today's
universe (survivorship-biased upper bound).

Run:
  PYTHONPATH=. python -m quant.agent_book
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from data import universe
from data.backfill import load_cached
from quant.backtest import COST_BPS
from quant.backtest_rules import _simulate_symbol
from quant.portfolio import _curve_stats

RESULTS_PATH = Path(__file__).parent / "agent_book_results.json"

MAX_WEIGHT = 0.20      # per-name cap
TARGET_VOL = 0.15      # annualised portfolio vol target
VOL_LOOKBACK = 21      # trading days for realised-vol estimates
DD_HALT = -0.20        # go flat if drawdown breaches this
DD_RESUME = -0.10      # resume entering once recovered to within this of peak
COST = COST_BPS["US"] / 1e4


def _name_vol(symbol: str) -> pd.Series:
    df = load_cached(symbol)
    if df is None:
        return pd.Series(dtype=float)
    r = df["close"].pct_change()
    return r.rolling(VOL_LOOKBACK).std() * np.sqrt(252)


def _inverse_vol_weights(vol_by_symbol: dict[str, float]) -> dict[str, float]:
    """Risk-balanced weights: ∝ 1/vol, per-name capped, gross capped at 1x (no
    leverage). The single sizing rule shared by the backtest AND the live broker
    layer — so the paper account trades exactly what the backtest measured."""
    raw = {}
    for sym, v in vol_by_symbol.items():
        if v is None or (isinstance(v, float) and (pd.isna(v) or v <= 0)):
            v = TARGET_VOL  # fallback when vol is missing
        raw[sym] = 1.0 / v
    tot = sum(raw.values())
    if tot <= 0:
        return {}
    w = {s: min(raw[s] / tot, MAX_WEIGHT) for s in raw}   # normalise + per-name cap
    gross = sum(w.values())
    if gross > 1.0:                                         # gross cap (no leverage)
        w = {s: x / gross for s, x in w.items()}
    return w


def latest_vol(symbol: str) -> float:
    s = _name_vol(symbol).dropna()
    return float(s.iloc[-1]) if len(s) else TARGET_VOL


def live_target_weights(symbols: list[str]) -> dict[str, float]:
    """Today's target weights for a set of candidate names — the agent's live
    sizing decision. (Vol-target scalar and DD breaker are portfolio-state
    features that engage once the live book has return history; at initialisation
    they're inert, so this is inverse-vol + caps.)"""
    return _inverse_vol_weights({s: latest_vol(s) for s in symbols})


def run() -> dict:
    trades = [t for s in universe.symbols("US") for t in _simulate_symbol(s) if t["direction"] == "long"]
    tdf = pd.DataFrame(trades)
    tdf["entry_date"] = pd.to_datetime(tdf["entry_date"])
    tdf["exit_date"] = pd.to_datetime(tdf["exit_date"])

    syms = tdf["symbol"].unique()
    rets = {s: load_cached(s)["close"].pct_change() for s in syms}
    vols = {s: _name_vol(s) for s in syms}

    spy = load_cached("SPY")["close"]
    cal = spy.index[(spy.index >= tdf["entry_date"].min()) & (spy.index <= tdf["exit_date"].max())]

    strat = pd.Series(0.0, index=cal)
    prev_w: dict[str, float] = {}
    equity, peak, halted = 1.0, 1.0, False
    recent: list[float] = []  # trailing strat returns for vol targeting

    for day in cal:
        # Drawdown circuit-breaker state machine.
        dd = equity / peak - 1.0
        if not halted and dd <= DD_HALT:
            halted = True
        elif halted and dd >= DD_RESUME:
            halted = False

        open_t = tdf[(tdf["entry_date"] <= day) & (tdf["exit_date"] > day)]
        target_w: dict[str, float] = {}
        if not halted and not open_t.empty:
            # Inverse-vol weights — the SAME helper the live broker layer uses.
            w = _inverse_vol_weights({sym: vols[sym].get(day, np.nan)
                                      for sym in open_t["symbol"].unique()})
            # Volatility targeting: lean exposure to hit TARGET_VOL.
            if len(recent) >= VOL_LOOKBACK:
                pv = float(np.std(recent[-VOL_LOOKBACK:]) * np.sqrt(252))
                scalar = min(1.0, TARGET_VOL / pv) if pv > 0 else 1.0
                w = {s: x * scalar for s, x in w.items()}
            target_w = w

        # Day P&L from current weights; charge cost on the turnover vs yesterday.
        day_ret = 0.0
        for sym, wt in target_w.items():
            r = rets[sym].get(day, 0.0)
            day_ret += wt * (0.0 if pd.isna(r) else r)
        turnover = sum(abs(target_w.get(s, 0.0) - prev_w.get(s, 0.0))
                       for s in set(target_w) | set(prev_w))
        day_ret -= turnover * COST

        strat.loc[day] = day_ret
        recent.append(day_ret)
        equity *= (1 + day_ret)
        peak = max(peak, equity)
        prev_w = target_w

    strat_equity = (1 + strat).cumprod()
    eq_equity = _equal_weight_curve(tdf, rets, cal)
    spy_equity = (spy.reindex(cal).ffill() / spy.reindex(cal).ffill().iloc[0])

    days_in_mkt = float((strat != 0).mean())
    result = {
        "meta": {
            "strategy": "Autonomous risk-managed book — inverse-vol sizing, vol-targeting, DD breaker.",
            "rules": {"max_weight": MAX_WEIGHT, "target_vol": TARGET_VOL,
                      "dd_halt": DD_HALT, "dd_resume": DD_RESUME},
            "date_range": [str(cal[0].date()), str(cal[-1].date())],
            "pct_days_invested": round(days_in_mkt * 100, 1),
            "note": "US long-only. Same entry signals as the rule backtest, but sized + risk-managed. "
                    "Shares its rules with the live Alpaca layer. Survivorship-biased upper bound; "
                    "forward ledger is the unbiased test. Not financial advice.",
        },
        "agent": _curve_stats(strat_equity, "Autonomous book"),
        "equal_weight": _curve_stats(eq_equity, "Equal-weight book"),
        "benchmark": _curve_stats(spy_equity, "SPY buy & hold"),
    }
    RESULTS_PATH.write_text(json.dumps(result, indent=2))
    return result


def _equal_weight_curve(tdf: pd.DataFrame, rets: dict, cal: pd.DatetimeIndex) -> pd.Series:
    """Naive benchmark: equal-weight open positions, charge cost on entry day."""
    s = pd.Series(0.0, index=cal)
    for day in cal:
        open_t = tdf[(tdf["entry_date"] <= day) & (tdf["exit_date"] > day)]
        if open_t.empty:
            continue
        drs = []
        for _, tr in open_t.iterrows():
            r = rets[tr["symbol"]].get(day, 0.0)
            r = 0.0 if pd.isna(r) else r
            if tr["entry_date"] == day:
                r -= COST
            drs.append(r)
        s.loc[day] = float(np.mean(drs))
    return (1 + s).cumprod()


def _print(r: dict) -> None:
    m = r["meta"]
    print(f"\n{m['strategy']}")
    print(f"{m['date_range'][0]}→{m['date_range'][1]} · invested {m['pct_days_invested']}% of days")
    print(f"Rules: {m['rules']}\n")
    print(f"{'':20} {'total':>9} {'CAGR':>8} {'vol':>7} {'Sharpe':>7} {'maxDD':>8}")
    for k in ["agent", "equal_weight", "benchmark"]:
        s = r[k]
        print(f"{s['label']:20} {str(s['total_return_pct'])+'%':>9} {str(s['cagr_pct'])+'%':>8} "
              f"{str(s['vol_pct'])+'%':>7} {str(s['sharpe']):>7} {str(s['max_drawdown_pct'])+'%':>8}")


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    _print(run())
    print(f"\nSaved → {RESULTS_PATH}")
