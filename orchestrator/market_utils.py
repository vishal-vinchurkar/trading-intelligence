"""Market identification, hours, and timezone helpers.

All stored timestamps should be UTC; convert to local market time for display
and for the market-hours checks here. Indian tickers carry a `.NS` (NSE) or
`.BO` (BSE) suffix on Yahoo Finance; everything else is treated as US.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from zoneinfo import ZoneInfo

US_TZ = ZoneInfo("America/New_York")
INDIA_TZ = ZoneInfo("Asia/Kolkata")
UTC = ZoneInfo("UTC")


@dataclass(frozen=True)
class Market:
    name: str            # 'US' | 'India'
    tz: ZoneInfo
    open_t: time
    close_t: time
    default_exchange: str


US_MARKET = Market("US", US_TZ, time(9, 30), time(16, 0), "NASDAQ")
INDIA_MARKET = Market("India", INDIA_TZ, time(9, 15), time(15, 30), "NSE")


def identify_market(symbol: str) -> Market:
    """Classify a ticker by suffix. '.NS'/'.BO' → India, else US."""
    s = symbol.upper().strip()
    if s.endswith(".NS") or s.endswith(".BO"):
        return INDIA_MARKET
    return US_MARKET


def is_market_open(symbol: str, at: datetime | None = None) -> bool:
    """True if the symbol's market is open at `at` (default: now, UTC).

    Weekend-aware; does not account for exchange holidays.
    """
    market = identify_market(symbol)
    now = (at or datetime.now(UTC)).astimezone(market.tz)
    if now.weekday() >= 5:  # Sat/Sun
        return False
    return market.open_t <= now.time() <= market.close_t


def market_status(symbol: str, at: datetime | None = None) -> dict:
    """Structured status for logging / 'market closed' records."""
    market = identify_market(symbol)
    now = (at or datetime.now(UTC)).astimezone(market.tz)
    return {
        "symbol": symbol,
        "market": market.name,
        "exchange": market.default_exchange,
        "local_time": now.isoformat(),
        "is_open": is_market_open(symbol, at),
    }
