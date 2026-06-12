"""India equities data fetcher — yfinance (Yahoo Finance).

Covers NSE (`.NS`) and BSE (`.BO`) tickers. yfinance is free and needs no API
key, which makes it the workhorse for India coverage. It is an unofficial
scraper, so treat failures as expected and cache results upstream.

Returns the same normalised shapes as `fetcher_us.py` so the orchestrator can
treat US and India identically downstream.
"""

from __future__ import annotations

import pandas as pd
import yfinance as yf


class YFinanceError(RuntimeError):
    """Raised when yfinance returns no usable data for a symbol."""


def fetch_ohlcv(symbol: str, period: str = "6mo") -> pd.DataFrame:
    """Daily OHLCV as a normalised DataFrame (oldest→newest, lowercase cols).

    `period` of '6mo' comfortably covers the 90-day window the technical agent
    needs plus enough history for the 200-day SMA to start filling in.
    """
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval="1d", auto_adjust=False)
    if df is None or df.empty:
        raise YFinanceError(f"No OHLCV data returned for {symbol!r}.")

    df = df.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
    )[["open", "high", "low", "close", "volume"]]
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df = df.sort_index()
    df["volume"] = df["volume"].astype("int64")
    return df


def fetch_quote(symbol: str) -> dict:
    """Latest quote-ish snapshot from fast_info."""
    ticker = yf.Ticker(symbol)
    fi = ticker.fast_info
    try:
        last = float(fi["last_price"])
    except (KeyError, TypeError, ValueError):
        raise YFinanceError(f"No quote available for {symbol!r}.")
    return {
        "symbol": symbol,
        "price": last,
        "previous_close": float(fi.get("previous_close", "nan")),
        "currency": fi.get("currency"),
    }


def fetch_fundamentals(symbol: str) -> dict:
    """Map yfinance `.info` into the ratios Agent 2 (Fundamental) needs.

    `.info` is the flakiest part of yfinance — fields are frequently missing,
    so every value is defensively pulled and may be None.
    """
    ticker = yf.Ticker(symbol)
    info = ticker.info or {}

    def _num(key):
        val = info.get(key)
        if val in (None, "None", ""):
            return None
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    return {
        "symbol": symbol,
        "name": info.get("longName") or info.get("shortName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "valuation": {
            "pe_ratio": _num("trailingPE"),
            "pb_ratio": _num("priceToBook"),
            "ev_to_ebitda": _num("enterpriseToEbitda"),
            "peg_ratio": _num("trailingPegRatio"),
        },
        "profitability": {
            "roe": _num("returnOnEquity"),
            "profit_margin": _num("profitMargins"),
            "operating_margin": _num("operatingMargins"),
        },
        "growth": {
            "revenue_yoy": _num("revenueGrowth"),
            "earnings_yoy": _num("earningsGrowth"),
        },
        "leverage": {
            "debt_to_equity": _num("debtToEquity"),
        },
        "dividend_yield": _num("dividendYield"),
        "market_cap": _num("marketCap"),
    }


def fetch_all(symbol: str) -> dict:
    """OHLCV + fundamentals for one India ticker. No rate limit / no key."""
    ohlcv = fetch_ohlcv(symbol)
    fundamentals = fetch_fundamentals(symbol)
    return {"symbol": symbol, "market": "India", "ohlcv": ohlcv, "fundamentals": fundamentals}


if __name__ == "__main__":
    df = fetch_ohlcv("RELIANCE.NS")
    print(f"RELIANCE.NS rows: {len(df)}  range: {df.index.min().date()} → {df.index.max().date()}")
    print(df.tail(3))
