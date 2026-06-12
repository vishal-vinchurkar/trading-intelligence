"""The scan universe — the engine's search space, NOT a user-facing list.

The quant engine scores every name here and surfaces only the highest-conviction
setups ("perfect BUY / perfect SELL") front-and-centre. The user never browses
this list; they pin their own favourites separately (tickers.is_favourite).

Keep it liquid and sector-spread so the backtest hit-rate is meaningful and not
an artifact of one crowded trade. Edit freely — add/remove names here and the
backfill + scan pick them up. Price history for every name comes from yfinance
(free, keyless, US + India), so growing this list costs nothing but compute.
"""

from __future__ import annotations

# Each name: (symbol, market, sector). Sector is coarse — used for the
# portfolio "book" view (concentration / net bias by sector), not for alpha.
US_UNIVERSE = [
    ("AAPL", "US", "Technology"),
    ("MSFT", "US", "Technology"),
    ("NVDA", "US", "Technology"),
    ("AMD", "US", "Technology"),
    ("CSCO", "US", "Technology"),
    ("GOOGL", "US", "Communication"),
    ("META", "US", "Communication"),
    ("NFLX", "US", "Communication"),
    ("DIS", "US", "Communication"),
    ("AMZN", "US", "Consumer Discretionary"),
    ("TSLA", "US", "Consumer Discretionary"),
    ("HD", "US", "Consumer Discretionary"),
    ("WMT", "US", "Consumer Staples"),
    ("PG", "US", "Consumer Staples"),
    ("KO", "US", "Consumer Staples"),
    ("JPM", "US", "Financials"),
    ("BAC", "US", "Financials"),
    ("V", "US", "Financials"),
    ("UNH", "US", "Healthcare"),
    ("JNJ", "US", "Healthcare"),
    ("XOM", "US", "Energy"),
]

INDIA_UNIVERSE = [
    ("RELIANCE.NS", "India", "Energy"),
    ("TCS.NS", "India", "Technology"),
    ("INFY.NS", "India", "Technology"),
    ("HDFCBANK.NS", "India", "Financials"),
    ("ICICIBANK.NS", "India", "Financials"),
    ("SBIN.NS", "India", "Financials"),
    ("KOTAKBANK.NS", "India", "Financials"),
    ("AXISBANK.NS", "India", "Financials"),
    ("BHARTIARTL.NS", "India", "Communication"),
    ("HINDUNILVR.NS", "India", "Consumer Staples"),
    ("ITC.NS", "India", "Consumer Staples"),
    ("LT.NS", "India", "Industrials"),
]

UNIVERSE = US_UNIVERSE + INDIA_UNIVERSE

# Benchmarks per market — for relative strength, beta, and "vs index" framing.
BENCHMARKS = {
    "US": "SPY",       # S&P 500 ETF (yfinance-friendly, long history)
    "India": "^NSEI",  # NIFTY 50
}


def symbols(market: str | None = None) -> list[str]:
    """All symbols, optionally filtered to one market."""
    return [s for s, m, _ in UNIVERSE if market is None or m == market]


def market_of(symbol: str) -> str | None:
    for s, m, _ in UNIVERSE:
        if s == symbol:
            return m
    return None


def sector_of(symbol: str) -> str | None:
    for s, _, sec in UNIVERSE:
        if s == symbol:
            return sec
    return None


def benchmark_for(symbol_or_market: str) -> str:
    """Benchmark symbol for a market label or a ticker."""
    if symbol_or_market in BENCHMARKS:
        return BENCHMARKS[symbol_or_market]
    m = market_of(symbol_or_market)
    return BENCHMARKS.get(m or "US", "SPY")
