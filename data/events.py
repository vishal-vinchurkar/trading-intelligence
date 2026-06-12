"""Event-risk context fetcher — Stream 3 of Phase B.

For a given symbol, find the nearest FUTURE earnings date and flag whether it
falls inside the next ~15 calendar days. This is a current-state overlay used to
downsize / veto a signal (don't take a fresh position into an earnings print) —
it is never folded into the backtested quant score.

Source is keyless yfinance: `get_earnings_dates()` (a tz-aware DataFrame indexed
by datetime) with `.calendar` as a fallback. yfinance is flaky, so every path
degrades gracefully to the "CLEAR / unknown" contract rather than throwing.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import yfinance as yf

_RETRIES = 3
_HORIZON_DAYS = 15


def _to_date(value) -> date | None:
    """Coerce a pandas Timestamp / datetime / date / str into a plain date."""
    if value is None:
        return None
    # pandas NaT and floats-as-nan
    try:
        import pandas as pd

        if value is pd.NaT:
            return None
        if isinstance(value, float) and pd.isna(value):
            return None
    except Exception:
        pass
    # pandas Timestamp / datetime both expose .date()
    if hasattr(value, "date") and callable(getattr(value, "date")):
        try:
            return value.date()
        except Exception:
            pass
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d"):
            try:
                return datetime.strptime(value[: len(fmt) + 2], fmt).date()
            except Exception:
                continue
    return None


def _future_dates_from_earnings_df(ticker: "yf.Ticker", today: date) -> list[date]:
    """Pull candidate dates from get_earnings_dates() with retries."""
    dates: list[date] = []
    for _ in range(_RETRIES):
        try:
            df = ticker.get_earnings_dates(limit=24)
        except Exception:
            df = None
        if df is None or getattr(df, "empty", True):
            continue
        try:
            for idx in df.index:
                d = _to_date(idx)
                if d is not None:
                    dates.append(d)
        except Exception:
            pass
        if dates:
            break
    return dates


def _future_dates_from_calendar(ticker: "yf.Ticker") -> list[date]:
    """Pull candidate dates from .calendar (dict or DataFrame, version-dependent)."""
    dates: list[date] = []
    try:
        cal = ticker.calendar
    except Exception:
        return dates
    if cal is None:
        return dates
    try:
        # Newer yfinance: dict with "Earnings Date" -> list[date]/date.
        if isinstance(cal, dict):
            val = cal.get("Earnings Date") or cal.get("Earnings High") or cal.get("Earnings Low")
            if isinstance(val, (list, tuple)):
                for v in val:
                    d = _to_date(v)
                    if d is not None:
                        dates.append(d)
            else:
                d = _to_date(val)
                if d is not None:
                    dates.append(d)
        else:
            # Older yfinance: DataFrame with an "Earnings Date" row.
            try:
                row = cal.loc["Earnings Date"]
                for v in row.tolist():
                    d = _to_date(v)
                    if d is not None:
                        dates.append(d)
            except Exception:
                pass
    except Exception:
        pass
    return dates


def event_context(symbol: str) -> dict:
    """Return the frozen event-context contract for the given symbol.

    On any failure / missing data returns the safe default:
    next_earnings_date=None, days_to_earnings=None, event_within_horizon=False,
    flag="CLEAR". All values are plain JSON-serialisable types.
    """
    today = datetime.now(timezone.utc).date()
    default = {
        "next_earnings_date": None,
        "days_to_earnings": None,
        "event_within_horizon": False,
        "flag": "CLEAR",
    }

    try:
        ticker = yf.Ticker(symbol)
        candidates = _future_dates_from_earnings_df(ticker, today)
        if not candidates:
            candidates = _future_dates_from_calendar(ticker)

        # Nearest FUTURE date (today counts as within horizon, so >= today).
        future = sorted(d for d in candidates if d >= today)
        if not future:
            return default

        next_date = future[0]
        days = (next_date - today).days
        within = 0 <= days <= _HORIZON_DAYS
        return {
            "next_earnings_date": next_date.isoformat(),
            "days_to_earnings": int(days),
            "event_within_horizon": bool(within),
            "flag": "EARNINGS_SOON" if within else "CLEAR",
        }
    except Exception:
        return default


if __name__ == "__main__":
    import json

    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    for sym in ("AAPL", "RELIANCE.NS"):
        print(f"=== event_context({sym!r}) ===")
        print(json.dumps(event_context(sym), indent=2))
        print()
