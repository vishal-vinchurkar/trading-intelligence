"""Liquidity / smart-money detectors — deterministic, point-in-time, backtestable.

The thesis (Smart Money Concepts / Wyckoff / VSA): institutions accumulate by
running retail stops — price sweeps below an obvious low (where stops sit), fills
big orders, then reverses. These detectors infer that footprint from FREE daily
OHLCV. They are deliberately point-in-time (every value at bar t uses only data
through t) so they can be backtested honestly and — only if they show edge —
folded into the score (unlike the macro/fundamental/congress OVERLAYS, which
aren't backtestable). What daily bars can't see (true order flow, where stops
actually rest) is acknowledged: these are inferences, sharpenable later with
intraday/live data.

Detectors (each returns a boolean Series aligned to df.index):
  • liquidity_sweep_bull — bar pierces a recent swing low then closes back above it
    (sell-side liquidity run + reclaim → likely accumulation). Bearish mirror too.
  • vsa_demand / vsa_supply — high-volume bar closing off its lows/highs (absorption
    / supply): the Volume-Spread-Analysis institutional footprint.
  • obv_bull_div / obv_bear_div — price makes a new extreme but OBV does not
    (hidden accumulation/distribution).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _prior_extreme(s: pd.Series, window: int, kind: str) -> pd.Series:
    """Rolling min/max over the `window` bars ENDING AT t-1 (excludes bar t) — the
    liquidity level resting just before the current bar. No lookahead."""
    roll = s.rolling(window).min() if kind == "low" else s.rolling(window).max()
    return roll.shift(1)


def liquidity_sweep_bull(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Bar's low pierces the prior `window`-bar low, but it closes back above it."""
    prior_low = _prior_extreme(df["low"], window, "low")
    return (df["low"] < prior_low) & (df["close"] > prior_low)


def liquidity_sweep_bear(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Bar's high pierces the prior `window`-bar high, but it closes back below it."""
    prior_high = _prior_extreme(df["high"], window, "high")
    return (df["high"] > prior_high) & (df["close"] < prior_high)


def _close_position(df: pd.DataFrame) -> pd.Series:
    """Where the close sits in the bar's range: 1.0 = on the high, 0.0 = on the low."""
    rng = (df["high"] - df["low"]).replace(0, np.nan)
    return ((df["close"] - df["low"]) / rng).clip(0, 1)


def vsa_demand(df: pd.DataFrame, vol_mult: float = 1.8, lookback: int = 20) -> pd.Series:
    """High-volume bar closing in the upper third of its range (absorption / demand)."""
    avg_vol = df["volume"].rolling(lookback).mean().shift(1)
    high_vol = df["volume"] > vol_mult * avg_vol
    return high_vol & (_close_position(df) >= 0.66)


def vsa_supply(df: pd.DataFrame, vol_mult: float = 1.8, lookback: int = 20) -> pd.Series:
    """High-volume bar closing in the lower third of its range (distribution / supply)."""
    avg_vol = df["volume"].rolling(lookback).mean().shift(1)
    high_vol = df["volume"] > vol_mult * avg_vol
    return high_vol & (_close_position(df) <= 0.34)


def obv(df: pd.DataFrame) -> pd.Series:
    """On-Balance Volume: cumulative volume signed by the day's close direction."""
    sign = np.sign(df["close"].diff().fillna(0.0))
    return (sign * df["volume"]).cumsum()


def obv_bull_div(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Price makes a new `window`-low but OBV does NOT — hidden accumulation."""
    o = obv(df)
    price_new_low = df["close"] < _prior_extreme(df["close"], window, "low")
    obv_not_new_low = o > _prior_extreme(o, window, "low")
    return price_new_low & obv_not_new_low


def obv_bear_div(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Price makes a new `window`-high but OBV does NOT — hidden distribution."""
    o = obv(df)
    price_new_high = df["close"] > _prior_extreme(df["close"], window, "high")
    obv_not_new_high = o < _prior_extreme(o, window, "high")
    return price_new_high & obv_not_new_high


# Registry the backtest iterates over — name → (function, "bull"/"bear" direction).
BULL_DETECTORS = {
    "liquidity_sweep_bull": liquidity_sweep_bull,
    "vsa_demand": vsa_demand,
    "obv_bull_div": obv_bull_div,
}
BEAR_DETECTORS = {
    "liquidity_sweep_bear": liquidity_sweep_bear,
    "vsa_supply": vsa_supply,
    "obv_bear_div": obv_bear_div,
}
