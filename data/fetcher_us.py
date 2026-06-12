"""US equities data fetcher — Alpha Vantage.

Pulls daily OHLCV and company fundamentals for US-listed tickers.

Free-tier reality (the binding constraint in this whole project):
    - 25 API calls per DAY on the free key
    - ~5 calls/minute
Each full fetch for one ticker = 2 calls (TIME_SERIES_DAILY + OVERVIEW),
so the free key covers ~12 tickers/day cold. Cache aggressively upstream
(Supabase) — this module only fetches; it does not cache.

Functions return normalised structures so the rest of the pipeline never
has to know the data came from Alpha Vantage specifically.
"""

from __future__ import annotations

import os
import time

import pandas as pd
import requests

_BASE_URL = "https://www.alphavantage.co/query"
_TIMEOUT = 30


class AlphaVantageError(RuntimeError):
    """Raised when Alpha Vantage returns an error, rate-limit, or empty payload."""


def _api_key() -> str:
    key = os.environ.get("ALPHA_VANTAGE_API_KEY")
    if not key:
        raise AlphaVantageError(
            "ALPHA_VANTAGE_API_KEY not set. Add it to your .env (see .env.example)."
        )
    return key


def _get(params: dict) -> dict:
    """Single GET with shared error handling for AV's many failure shapes."""
    params = {**params, "apikey": _api_key()}
    resp = requests.get(_BASE_URL, params=params, timeout=_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()

    # Alpha Vantage signals problems inside a 200 response, not via status code.
    if "Error Message" in data:
        raise AlphaVantageError(f"Alpha Vantage error: {data['Error Message']}")
    if "Note" in data:  # rate limit hit
        raise AlphaVantageError(f"Rate limit: {data['Note']}")
    if "Information" in data:  # free-tier exhausted / invalid call
        raise AlphaVantageError(f"Alpha Vantage info: {data['Information']}")
    if not data:
        raise AlphaVantageError("Empty response from Alpha Vantage.")
    return data


def fetch_ohlcv(symbol: str, outputsize: str = "compact") -> pd.DataFrame:
    """Daily OHLCV as a normalised DataFrame (oldest→newest, lowercase cols).

    outputsize: 'compact' = last 100 rows (1 call), 'full' = 20+ yrs.
    'compact' is plenty for the 90-day window the technical agent needs.
    """
    data = _get(
        {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": outputsize,
        }
    )
    series = data.get("Time Series (Daily)")
    if not series:
        raise AlphaVantageError(f"No daily series returned for {symbol!r}.")

    df = pd.DataFrame.from_dict(series, orient="index").rename(
        columns={
            "1. open": "open",
            "2. high": "high",
            "3. low": "low",
            "4. close": "close",
            "5. volume": "volume",
        }
    )
    df = df.astype(float)
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()  # oldest → newest
    df["volume"] = df["volume"].astype("int64")
    return df


def fetch_quote(symbol: str) -> dict:
    """Latest real-time-ish quote (GLOBAL_QUOTE)."""
    data = _get({"function": "GLOBAL_QUOTE", "symbol": symbol})
    q = data.get("Global Quote") or {}
    if not q:
        raise AlphaVantageError(f"No quote returned for {symbol!r}.")
    return {
        "symbol": q.get("01. symbol"),
        "price": float(q.get("05. price", "nan")),
        "change_percent": q.get("10. change percent"),
        "volume": int(q.get("06. volume", 0)),
        "latest_trading_day": q.get("07. latest trading day"),
    }


def fetch_fundamentals(symbol: str) -> dict:
    """Company overview → the ratios Agent 2 (Fundamental) needs."""
    data = _get({"function": "OVERVIEW", "symbol": symbol})

    def _num(key):
        val = data.get(key)
        if val in (None, "None", "-", ""):
            return None
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    return {
        "symbol": data.get("Symbol", symbol),
        "name": data.get("Name"),
        "sector": data.get("Sector"),
        "industry": data.get("Industry"),
        "valuation": {
            "pe_ratio": _num("PERatio"),
            "pb_ratio": _num("PriceToBookRatio"),
            "ev_to_ebitda": _num("EVToEBITDA"),
            "peg_ratio": _num("PEGRatio"),
        },
        "profitability": {
            "roe": _num("ReturnOnEquityTTM"),
            "profit_margin": _num("ProfitMargin"),
            "operating_margin": _num("OperatingMarginTTM"),
        },
        "growth": {
            "revenue_yoy": _num("QuarterlyRevenueGrowthYOY"),
            "earnings_yoy": _num("QuarterlyEarningsGrowthYOY"),
        },
        "leverage": {
            "debt_to_equity": _num("DebtToEquityRatio"),
        },
        "dividend_yield": _num("DividendYield"),
        "market_cap": _num("MarketCapitalization"),
    }


def fetch_all(symbol: str, polite_delay: float = 13.0) -> dict:
    """OHLCV + fundamentals for one ticker.

    polite_delay seconds between the two calls keeps us under the
    ~5 calls/min free-tier ceiling. Costs 2 of the daily 25 calls.
    """
    ohlcv = fetch_ohlcv(symbol)
    time.sleep(polite_delay)
    fundamentals = fetch_fundamentals(symbol)
    return {"symbol": symbol, "market": "US", "ohlcv": ohlcv, "fundamentals": fundamentals}


if __name__ == "__main__":
    # Quick manual check: requires ALPHA_VANTAGE_API_KEY in env.
    from dotenv import load_dotenv

    load_dotenv()
    df = fetch_ohlcv("AAPL")
    print(f"AAPL OHLCV rows: {len(df)}  range: {df.index.min().date()} → {df.index.max().date()}")
    print(df.tail(3))
