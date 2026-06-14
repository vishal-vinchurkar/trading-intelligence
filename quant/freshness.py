"""Data-freshness guard — never silently serve a stale price.

The failure that broke trust: the cache missed a trading day, so the app showed a
day-old close (SNOW 240.39) while the market had moved (232.78), with no warning.
A tool that informs money decisions must LOUDLY flag stale data, not quietly serve
it. This computes how far behind the newest bar is versus the last completed
trading session and exposes an is_stale flag the scan + dashboard surface.

Method (deliberately lenient toward false-positives, never false-negatives):
  • Reference bar = SPY's newest cached date (SPY trades every session).
  • Expected = the last completed weekday session STRICTLY before today — so an
    as-yet-unprinted bar pre-close never trips it, but a genuinely missed day does.
  • US market holidays are not modelled; around a holiday this may warn one session
    early. That's the safe direction — warn, don't hide.

Run:
  PYTHONPATH=. python -m quant.freshness
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd

from data import universe
from data.backfill import load_cached


def last_completed_session(today: date | None = None) -> date:
    """Most recent weekday strictly before `today` (a session whose close is in)."""
    today = today or datetime.now().date()
    d = today - timedelta(days=1)
    while d.weekday() >= 5:  # Sat=5, Sun=6 → step back to Friday
        d -= timedelta(days=1)
    return d


def _business_days(a: date, b: date) -> int:
    """Count weekdays in (a, b]. Negative if a > b."""
    if a == b:
        return 0
    sign = 1 if b > a else -1
    lo, hi = sorted((a, b))
    days = 0
    cur = lo + timedelta(days=1)
    while cur <= hi:
        if cur.weekday() < 5:
            days += 1
        cur += timedelta(days=1)
    return sign * days


def check(today: date | None = None) -> dict:
    today = today or datetime.now().date()
    expected = last_completed_session(today)

    spy = load_cached("SPY")
    data_date = spy.index.max().date() if spy is not None and len(spy) else None

    # How many universe names lag the freshest bar we hold (catches partial failures).
    behind = 0
    if data_date is not None:
        for s in universe.symbols():
            df = load_cached(s)
            if df is not None and len(df) and df.index.max().date() < data_date:
                behind += 1

    if data_date is None:
        return {"is_stale": True, "data_date": None, "expected_date": expected.isoformat(),
                "business_days_stale": None, "symbols_behind": behind,
                "message": "No SPY price cache found — data is missing. Do not trade off this."}

    stale_by = _business_days(data_date, expected)
    is_stale = stale_by >= 1
    if is_stale:
        msg = (f"⚠ STALE DATA: newest bar is {data_date.isoformat()}, "
               f"{stale_by} trading day(s) behind the last session ({expected.isoformat()}). "
               f"Prices shown are out of date — refresh before acting.")
    else:
        msg = f"Data current as of {data_date.isoformat()} (last session {expected.isoformat()})."
    return {
        "is_stale": is_stale,
        "data_date": data_date.isoformat(),
        "expected_date": expected.isoformat(),
        "business_days_stale": stale_by,
        "symbols_behind": behind,
        "message": msg,
    }


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    r = check()
    print(("STALE" if r["is_stale"] else "FRESH") + ": " + r["message"])
    if r["symbols_behind"]:
        print(f"  {r['symbols_behind']} universe symbol(s) lag the freshest bar.")
