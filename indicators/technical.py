"""Technical indicators computed from OHLCV data.

All functions take a pandas DataFrame with columns:
    open, high, low, close, volume   (lowercase, datetime index, oldest→newest)

`compute_all` returns a single dict ready to hand to Agent 1 (Technical Analyst).
Indicators are implemented by hand on pandas/numpy — no third-party TA library —
so behaviour is transparent and the install stays light.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ── Individual indicators ─────────────────────────────────────────────

def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's RSI."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    # Wilder smoothing == EMA with alpha = 1/period
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """Returns (macd_line, signal_line, histogram)."""
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line, macd_line - signal_line


def sma(close: pd.Series, period: int) -> pd.Series:
    return close.rolling(window=period).mean()


def bollinger(close: pd.Series, period: int = 20, num_std: float = 2.0):
    """Returns (middle, upper, lower)."""
    middle = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()
    return middle, middle + num_std * std, middle - num_std * std


def support_resistance(df: pd.DataFrame, lookback: int = 120, k: int = 3, n_levels: int = 2):
    """Near-price support/resistance from swing pivots.

    A swing high is a bar whose high is the max of its ±k neighbours (a local top);
    a swing low is the mirror. We return the NEAREST pivots above (resistance) and
    below (support) the latest close — the levels a trade would actually use —
    rather than the 90-day extremes (which for a trending name sit absurdly far
    from price and read as broken). Falls back to rolling min/max if no pivots."""
    window = df.tail(lookback)
    highs, lows = window["high"].to_numpy(), window["low"].to_numpy()
    close = float(window["close"].iloc[-1])

    swing_highs, swing_lows = [], []
    for i in range(k, len(window) - k):
        if highs[i] == highs[i - k : i + k + 1].max():
            swing_highs.append(round(float(highs[i]), 2))
        if lows[i] == lows[i - k : i + k + 1].min():
            swing_lows.append(round(float(lows[i]), 2))

    resistance = sorted({h for h in swing_highs if h > close})[:n_levels]
    support = sorted({l for l in swing_lows if l < close}, reverse=True)[:n_levels]

    # Fallbacks so we always return usable levels.
    if not resistance:
        resistance = [round(float(window["high"].tail(20).max()), 2)]
    if not support:
        support = [round(float(window["low"].tail(20).min()), 2)]
    return support, resistance


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range (Wilder). The stop/target unit of measure — a stop set
    at N×ATR adapts to each name's actual range instead of an arbitrary %."""
    high, low, prev_close = df["high"], df["low"], df["close"].shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()


def realized_vol(close: pd.Series, lookback: int = 20):
    """Daily and annualised realised volatility from log returns.

    This is what makes a predicted move *mean* something: a 2% call is noise on
    a 1%-vol name and a real thesis on a 5%-vol name. Expected moves are sized
    off this, not guessed.
    """
    rets = np.log(close / close.shift(1)).dropna()
    daily = float(rets.tail(lookback).std())
    return daily, float(daily * np.sqrt(252))


def expected_move(last_close: float, daily_vol: float, horizon_days: int) -> dict:
    """1-sigma expected move over a horizon: price × σ_daily × √days.

    Returns both the % band and the absolute price band. A trade's predicted
    magnitude should live inside this band — if the model claims a 10% move on a
    name whose 1σ/30d is 4%, that's a flag, not a forecast.
    """
    sigma_pct = float(daily_vol * np.sqrt(horizon_days))
    return {
        "sigma_pct": round(sigma_pct * 100, 2),
        "low": round(last_close * (1 - sigma_pct), 2),
        "high": round(last_close * (1 + sigma_pct), 2),
    }


# ── Signal interpretation helpers ─────────────────────────────────────

def _rsi_signal(value: float) -> str:
    if value >= 70:
        return "OVERBOUGHT"
    if value <= 30:
        return "OVERSOLD"
    return "NEUTRAL"


def _macd_signal(macd_v: float, signal_v: float) -> str:
    if macd_v > signal_v:
        return "BULLISH"
    if macd_v < signal_v:
        return "BEARISH"
    return "NEUTRAL"


def _ma_trend(close: float, s20: float, s50: float, s200: float) -> str:
    if np.isnan(s200):  # not enough history for 200 SMA
        if close > s20 > s50:
            return "BULLISH"
        if close < s20 < s50:
            return "BEARISH"
        return "NEUTRAL"
    if close > s50 > s200:
        return "BULLISH"
    if close < s50 < s200:
        return "BEARISH"
    return "NEUTRAL"


def _bollinger_signal(close: float, upper: float, lower: float) -> str:
    if close >= upper:
        return "UPPER_BREAKOUT"
    if close <= lower:
        return "LOWER_BREAKOUT"
    return "WITHIN_BANDS"


def _volume_signal(volume: pd.Series, close: pd.Series, lookback: int = 20) -> str:
    """Crude accumulation/distribution read: recent volume vs avg, on up vs down days."""
    recent_vol = volume.tail(5).mean()
    avg_vol = volume.tail(lookback).mean()
    price_change = close.iloc[-1] - close.iloc[-5] if len(close) >= 5 else 0
    if recent_vol > avg_vol and price_change > 0:
        return "ACCUMULATION"
    if recent_vol > avg_vol and price_change < 0:
        return "DISTRIBUTION"
    return "NEUTRAL"


# ── Public entry point ────────────────────────────────────────────────

def compute_all(df: pd.DataFrame) -> dict:
    """Compute the full indicator panel for Agent 1.

    Expects a normalised OHLCV DataFrame (lowercase cols, oldest→newest).
    Returns a JSON-serialisable dict; values are plain Python floats/str.
    """
    if df is None or len(df) < 30:
        raise ValueError(
            f"Need at least 30 rows of OHLCV to compute indicators, got {0 if df is None else len(df)}"
        )

    close = df["close"]
    last_close = float(close.iloc[-1])

    rsi_series = rsi(close)
    rsi_v = float(rsi_series.iloc[-1])

    macd_line, signal_line, hist = macd(close)
    macd_v = float(macd_line.iloc[-1])
    macd_sig_v = float(signal_line.iloc[-1])

    s20 = float(sma(close, 20).iloc[-1])
    s50 = float(sma(close, 50).iloc[-1])
    s200_raw = sma(close, 200).iloc[-1]
    s200 = np.nan if pd.isna(s200_raw) else float(s200_raw)

    mid, upper, lower = bollinger(close)
    upper_v, lower_v = float(upper.iloc[-1]), float(lower.iloc[-1])

    support, resistance = support_resistance(df)

    atr_v = float(atr(df).iloc[-1])
    daily_vol, annual_vol = realized_vol(close)

    return {
        "last_close": round(last_close, 2),
        "volatility": {
            "atr_14": round(atr_v, 2),
            "atr_pct": round(atr_v / last_close * 100, 2),
            "daily_vol_pct": round(daily_vol * 100, 2),
            "annual_vol_pct": round(annual_vol * 100, 1),
        },
        "expected_move": {
            "5d": expected_move(last_close, daily_vol, 5),
            "15d": expected_move(last_close, daily_vol, 15),
            "30d": expected_move(last_close, daily_vol, 30),
        },
        "rsi": {"value": round(rsi_v, 1), "signal": _rsi_signal(rsi_v)},
        "macd": {
            "value": round(macd_v, 3),
            "signal_line": round(macd_sig_v, 3),
            "histogram": round(macd_v - macd_sig_v, 3),
            "signal": _macd_signal(macd_v, macd_sig_v),
        },
        "moving_averages": {
            "sma_20": round(s20, 2),
            "sma_50": round(s50, 2),
            "sma_200": None if np.isnan(s200) else round(s200, 2),
            "trend": _ma_trend(last_close, s20, s50, s200),
        },
        "bollinger": {
            "upper": round(upper_v, 2),
            "lower": round(lower_v, 2),
            "signal": _bollinger_signal(last_close, upper_v, lower_v),
        },
        "volume": {"signal": _volume_signal(df["volume"], close)},
        "key_levels": {"support": support, "resistance": resistance},
    }


if __name__ == "__main__":
    # Smoke test with synthetic data
    idx = pd.date_range("2025-01-01", periods=200, freq="D")
    base = np.cumsum(np.random.randn(200)) + 100
    demo = pd.DataFrame(
        {
            "open": base + np.random.randn(200) * 0.5,
            "high": base + np.abs(np.random.randn(200)),
            "low": base - np.abs(np.random.randn(200)),
            "close": base,
            "volume": np.random.randint(1_000_000, 5_000_000, 200),
        },
        index=idx,
    )
    import json

    print(json.dumps(compute_all(demo), indent=2))
