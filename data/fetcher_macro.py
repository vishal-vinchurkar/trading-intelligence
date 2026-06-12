"""Macro context fetcher — Stream 1 of Phase B.

Current-state macro overlay: policy/short-rate regime, the long end, the curve
slope, and (for India) the currency. This is NOT point-in-time backtestable on
free data — it contextualises a signal, it is never folded into the backtested
quant score.

Data source is keyless yfinance only (no FRED_API_KEY in this environment):
    ^IRX  = 13-week T-bill yield, already in %        (short-rate / policy proxy)
    ^FVX  = 5-year Treasury yield  * 10
    ^TNX  = 10-year Treasury yield * 10
    ^TYX  = 30-year Treasury yield * 10
    INR=X = USDINR spot                                (India FX)

regime is DERIVED from the ~6-month trend of the short-rate series, never hardcoded.
Every network call degrades gracefully: on failure we return the contract with
None fields and a `source` string that records what went wrong.
"""

from __future__ import annotations

from datetime import date

import yfinance as yf

_RETRIES = 3


def _history(ticker: str, period: str = "6mo"):
    """Fetch a price history DataFrame for a yfinance ticker, with retries.

    Returns the DataFrame (possibly empty) or None on hard failure.
    """
    last_exc = None
    for _ in range(_RETRIES):
        try:
            df = yf.Ticker(ticker).history(period=period, auto_adjust=False)
            if df is not None and not df.empty:
                return df
        except Exception as exc:  # network / parse / rate-limit — all non-fatal
            last_exc = exc
    if last_exc is not None:
        return None
    return None  # empty every time


def _latest_close(df) -> float | None:
    if df is None or df.empty or "Close" not in df.columns:
        return None
    try:
        return float(df["Close"].dropna().iloc[-1])
    except (IndexError, ValueError, TypeError):
        return None


def _yield_pct(raw: float | None) -> float | None:
    """Normalise a CBOE yield-index close to a percentage.

    History note: ^TNX/^FVX/^TYX were historically quoted as yield*10 (e.g. 43.2
    meant 4.32%). Current yfinance (1.2.x) returns them already in percent
    (~4.46). Detect by magnitude: a Treasury yield > 25 is implausible, so it's
    the legacy *10 convention and we divide; otherwise it's already in %.
    """
    if raw is None:
        return None
    return round(raw / 10.0, 4) if raw > 25.0 else round(raw, 4)


def _close_n_back(df, n: int) -> float | None:
    """Close roughly n trading rows before the latest row."""
    if df is None or df.empty or "Close" not in df.columns:
        return None
    closes = df["Close"].dropna()
    if len(closes) <= n:
        return None
    try:
        return float(closes.iloc[-(n + 1)])
    except (IndexError, ValueError, TypeError):
        return None


def _empty_contract(source: str) -> dict:
    return {
        "regime": "NEUTRAL",
        "policy_rate": None,
        "ten_year": None,
        "two_year": None,
        "curve_slope_bps": None,
        "fx": None,
        "as_of": date.today().isoformat(),
        "source": source,
    }


def _us_macro() -> dict:
    out = _empty_contract("yfinance")
    notes = []

    # Short-rate / policy proxy + 6-month regime derivation, both from ^IRX.
    irx = _history("^IRX", period="6mo")
    policy_rate = _latest_close(irx)  # ^IRX already in %
    if policy_rate is None:
        notes.append("^IRX unavailable")
    out["policy_rate"] = policy_rate

    regime = "NEUTRAL"
    if irx is not None and policy_rate is not None:
        # ~6 months ago: a 6mo daily history is ~125 rows; step back ~125.
        six_mo_ago = _close_n_back(irx, 125)
        if six_mo_ago is None:
            # fall back to the earliest available close in the window
            six_mo_ago = _close_n_back(irx, len(irx["Close"].dropna()) - 1)
        if six_mo_ago is not None:
            delta = policy_rate - six_mo_ago
            if delta > 0.25:
                regime = "TIGHTENING"
            elif delta < -0.25:
                regime = "EASING"
            else:
                regime = "NEUTRAL"
        else:
            notes.append("no 6m short-rate history for regime")
    out["regime"] = regime

    # Long end: ^TNX is yield*10.
    tnx = _history("^TNX", period="1mo")
    tnx_close = _latest_close(tnx)
    out["ten_year"] = _yield_pct(tnx_close)
    if tnx_close is None:
        notes.append("^TNX unavailable")

    # No clean 2y index on yfinance → leave two_year / curve_slope_bps as None.
    out["two_year"] = None
    out["curve_slope_bps"] = None
    notes.append("two_year=None (no keyless 2y yfinance index)")

    out["fx"] = None  # not meaningful for the US overlay
    out["source"] = "yfinance" + ("; " + "; ".join(notes) if notes else "")
    return out


def _india_macro() -> dict:
    out = _empty_contract("yfinance")
    notes = []

    # No reliable keyless NSE 10y G-sec or RBI policy-rate ticker on yfinance.
    out["ten_year"] = None
    out["two_year"] = None
    out["curve_slope_bps"] = None
    out["policy_rate"] = None
    notes.append("IN rates=None (no keyless yfinance G-sec/policy source)")

    # FX is the reliable, always-provided India signal: USDINR via INR=X.
    fx = None
    inr = _history("INR=X", period="6mo")
    if inr is None or inr.empty:
        inr = _history("USDINR=X", period="6mo")
    level = _latest_close(inr)
    if level is not None:
        # ~63 trading days ago (~3 months); the spec window for trend.
        ref = _close_n_back(inr, 63)
        if ref is None:
            ref = _close_n_back(inr, len(inr["Close"].dropna()) - 1)
        trend = "FLAT"
        if ref is not None and ref != 0:
            pct = (level - ref) / ref * 100.0
            # USDINR up => INR weaker.
            if pct > 1.0:
                trend = "WEAKER"
            elif pct < -1.0:
                trend = "STRONGER"
            else:
                trend = "FLAT"
        else:
            notes.append("no FX history window for trend")
        fx = {"pair": "USDINR", "level": round(level, 4), "trend": trend}
    else:
        notes.append("USDINR unavailable")
    out["fx"] = fx

    # No rate series for India → regime stays NEUTRAL (documented in source).
    out["regime"] = "NEUTRAL"
    notes.append("regime=NEUTRAL (no IN rate series to derive trend)")
    out["source"] = "yfinance; " + "; ".join(notes)
    return out


def macro_context(market: str) -> dict:
    """Return the frozen macro-context contract for the given market.

    market: "US" or "IN"/"INDIA" (case-insensitive). Any unknown market is
    treated as US. All values are plain JSON-serialisable types.
    """
    try:
        m = (market or "").strip().upper()
        if m in ("IN", "INDIA", "NSE", "BSE"):
            return _india_macro()
        return _us_macro()
    except Exception as exc:  # last-resort guard — never throw to the caller
        out = _empty_contract(f"yfinance; fatal: {exc}")
        return out


if __name__ == "__main__":
    import json

    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    print("=== macro_context('US') ===")
    print(json.dumps(macro_context("US"), indent=2))
    print("\n=== macro_context('IN') ===")
    print(json.dumps(macro_context("IN"), indent=2))
