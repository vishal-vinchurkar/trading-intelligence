"""The quant conviction score — the engine that hunts 'perfect BUY / perfect SELL'.

A deterministic 0–100 score computed from price action ALONE, so it can be run
point-in-time across 10 years of history with zero look-ahead and then validated
by the backtest. (Fundamentals are a *current-state overlay* added later by the
LLM arbitrator — they are deliberately NOT in this score, because free data has
no clean point-in-time fundamental history and we refuse to fake a backtest.)

The score is intentionally interpretable: every component returns its own 0–100
sub-score and a one-line reason, so the dashboard can explain *why* a name is a
"perfect BUY", not just assert it. Components are blended, not averaged blindly —
direction (trend/momentum/relative strength/flow) sets the core, and RSI acts as
an entry-timing modifier (don't chase overbought; reward buying oversold strength).

Score bands:
    >= 75  STRONG_BUY   ("perfect buy" candidate)
    60–75  BUY
    40–60  NEUTRAL
    25–40  SELL
    <  25  STRONG_SELL
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from indicators import technical as ta

# Component weights for the direction core (sum to 1.0). Trend and momentum carry
# the most weight — the two most robust, most-replicated equity-return factors.
WEIGHTS = {
    "trend": 0.35,
    "momentum": 0.30,
    "relative_strength": 0.25,
    "flow": 0.10,
}


def _squash(x: float, scale: float) -> float:
    """Map an unbounded signal to 0–100 via tanh, 50 = neutral. `scale` sets how
    many 'units' of x reach the saturation zone."""
    return 50.0 + 50.0 * math.tanh(x / scale)


def _ret(close: pd.Series, lookback: int) -> float | None:
    if len(close) <= lookback:
        return None
    return float(close.iloc[-1] / close.iloc[-1 - lookback] - 1.0)


def _trend(close: pd.Series) -> tuple[float, str]:
    """Where price sits in the SMA stack — the classic regime filter."""
    c = float(close.iloc[-1])
    s50 = float(ta.sma(close, 50).iloc[-1])
    s200_raw = ta.sma(close, 200).iloc[-1]
    s200 = None if pd.isna(s200_raw) else float(s200_raw)

    score = 50.0
    if c > s50:
        score += 15
    else:
        score -= 15
    if s200 is not None:
        if c > s200:
            score += 15
        else:
            score -= 15
        if s50 > s200:
            score += 20  # golden-cross regime
        else:
            score -= 20
    score = max(0.0, min(100.0, score))
    if s200 is None:
        reason = f"price {'above' if c > s50 else 'below'} 50DMA (200DMA not yet available)"
    else:
        stack = "above" if (c > s50 > s200) else ("below" if (c < s50 < s200) else "mixed")
        reason = f"price/50/200DMA stack {stack}"
    return score, reason


def _momentum(close: pd.Series) -> tuple[float, str]:
    """6-month price momentum (the 126-day return) — the workhorse equity factor —
    confirmed by MACD histogram sign."""
    r6 = _ret(close, 126)
    if r6 is None:
        return 50.0, "insufficient history for 6m momentum"
    base = _squash(r6, scale=0.25)  # ±25% 6m return ≈ saturation
    macd_line, signal_line, _ = ta.macd(close)
    hist = float(macd_line.iloc[-1] - signal_line.iloc[-1])
    base += 5 if hist > 0 else -5
    base = max(0.0, min(100.0, base))
    return base, f"6m return {r6*100:+.1f}%, MACD {'+' if hist > 0 else '−'}"


def _relative_strength(close: pd.Series, bench: pd.Series | None) -> tuple[float, str]:
    """3-month excess return vs the benchmark — is this name a leader or laggard?"""
    if bench is None:
        return 50.0, "no benchmark"
    rs_stock = _ret(close, 63)
    rs_bench = _ret(bench, 63)
    if rs_stock is None or rs_bench is None:
        return 50.0, "insufficient history for relative strength"
    excess = rs_stock - rs_bench
    return _squash(excess, scale=0.10), f"3m vs index {excess*100:+.1f}%"


def _flow(df: pd.DataFrame) -> tuple[float, str]:
    """Volume accumulation/distribution — does flow confirm the move?"""
    sig = ta._volume_signal(df["volume"], df["close"])
    return {"ACCUMULATION": 70.0, "DISTRIBUTION": 30.0, "NEUTRAL": 50.0}[sig], sig.lower()


def _rsi_timing(close: pd.Series) -> tuple[float, str]:
    """Entry-timing modifier (−10..+10): penalise chasing overbought, reward
    buying oversold. Applied on top of the direction core."""
    rsi_v = float(ta.rsi(close).iloc[-1])
    if rsi_v >= 70:
        return -10.0 * min(1.0, (rsi_v - 70) / 15), f"overbought (RSI {rsi_v:.0f})"
    if rsi_v <= 30:
        return +10.0 * min(1.0, (30 - rsi_v) / 15), f"oversold (RSI {rsi_v:.0f})"
    return 0.0, f"RSI {rsi_v:.0f} neutral"


def label_for(score: float) -> str:
    if score >= 75:
        return "STRONG_BUY"
    if score >= 60:
        return "BUY"
    if score > 40:
        return "NEUTRAL"
    if score > 25:
        return "SELL"
    return "STRONG_SELL"


def score(df: pd.DataFrame, bench: pd.Series | None = None) -> dict:
    """Compute the conviction score on the LAST row of `df`.

    Point-in-time by construction: to score as of date T, pass df.loc[:T] (and
    bench.loc[:T]). That is exactly what the backtest does — no look-ahead.

    Returns: {score, label, components:{name:{score,weight,reason}}, timing:{...}}.
    """
    if df is None or len(df) < 60:
        raise ValueError(f"Need ≥60 rows to score, got {0 if df is None else len(df)}")
    close = df["close"]

    comps = {
        "trend": _trend(close),
        "momentum": _momentum(close),
        "relative_strength": _relative_strength(close, bench),
        "flow": _flow(df),
    }
    core = sum(WEIGHTS[k] * v[0] for k, v in comps.items())
    tmod, treason = _rsi_timing(close)
    final = max(0.0, min(100.0, core + tmod))

    return {
        "score": round(final, 1),
        "label": label_for(final),
        "core": round(core, 1),
        "components": {
            k: {"score": round(v[0], 1), "weight": WEIGHTS[k], "reason": v[1]}
            for k, v in comps.items()
        },
        "timing": {"adjustment": round(tmod, 1), "reason": treason},
    }


if __name__ == "__main__":
    from data.backfill import load_cached
    from data import universe

    for sym in ["AAPL", "NVDA", "RELIANCE.NS", "ITC.NS"]:
        df = load_cached(sym)
        bench = load_cached(universe.benchmark_for(sym))
        if df is None:
            print(f"{sym}: no cache (run backfill)")
            continue
        bc = bench["close"] if bench is not None else None
        out = score(df, bc)
        print(f"{sym:14} {out['score']:5.1f}  {out['label']:11}  " +
              "  ".join(f"{k}={v['score']:.0f}" for k, v in out["components"].items()))
