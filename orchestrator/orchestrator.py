"""Orchestrator — the main entry point.

For one ticker:
  1. Identify market (US vs India) and fetch OHLCV + fundamentals.
  2. Compute technical indicators.
  3. Run Agent 1 (technical) and Agent 2 (fundamental) IN PARALLEL, isolated.
  4. Feed both into Agent 3 (arbitrator) for the final verdict.
  5. Optionally persist everything to Supabase.

Agent isolation is structural: Agent 1 never receives fundamentals, Agent 2
never receives price data, and only Agent 3 sees both outputs.

Run:
  python -m orchestrator.orchestrator AAPL
  python -m orchestrator.orchestrator RELIANCE.NS --no-save
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

from agents import agent_arbitrator, agent_fundamental, agent_technical
from data import fetcher_india, fetcher_us
from indicators import technical as ta
from orchestrator import market_utils


def _fetch(symbol: str, market: market_utils.Market) -> dict:
    """Route to the right data source by market."""
    if market.name == "India":
        return fetcher_india.fetch_all(symbol)
    return fetcher_us.fetch_all(symbol)


async def analyze(symbol: str, save: bool = True) -> dict:
    market = market_utils.identify_market(symbol)
    market_label = f"{market.name}/{market.default_exchange}"
    status = market_utils.market_status(symbol)
    if not status["is_open"]:
        print(f"[info] {symbol}: market closed ({status['local_time']}). Running on last close.")

    # 1-2. Fetch + indicators (blocking I/O, off the event loop).
    bundle = await asyncio.to_thread(_fetch, symbol, market)
    indicators = ta.compute_all(bundle["ohlcv"])

    # 3. Agents 1 & 2 in parallel, each blind to the other's domain.
    technical_task = asyncio.to_thread(
        agent_technical.run, symbol, market_label, indicators
    )
    fundamental_task = asyncio.to_thread(
        agent_fundamental.run, symbol, market_label, bundle["fundamentals"]
    )
    technical_out, fundamental_out = await asyncio.gather(technical_task, fundamental_task)

    # 4. Arbitration.
    arb_out = await asyncio.to_thread(
        agent_arbitrator.run, symbol, market_label, technical_out, fundamental_out
    )

    result = {
        "symbol": symbol,
        "market": market_label,
        "technical": technical_out,
        "fundamental": fundamental_out,
        "arbitrator": arb_out,
    }

    # 5. Persist (optional).
    if save and os.environ.get("SUPABASE_URL"):
        from orchestrator import supabase_client as db

        client = db.get_client()
        ticker_id = db.upsert_ticker(
            client, symbol, market.name, market.default_exchange,
            name=bundle["fundamentals"].get("name"),
        )
        db.save_agent_output(client, ticker_id, "technical", technical_out, agent_technical.model_id())
        db.save_agent_output(client, ticker_id, "fundamental", fundamental_out, agent_fundamental.model_id())
        db.save_agent_output(client, ticker_id, "arbitrator", arb_out, agent_arbitrator.model_id())
        db.save_prediction(client, ticker_id, arb_out, technical_out, fundamental_out)
        print(f"[saved] {symbol} → Supabase (ticker_id={ticker_id})")

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the trading intelligence pipeline for a ticker.")
    parser.add_argument("symbol", help="e.g. AAPL, NVDA, RELIANCE.NS, INFY.NS")
    parser.add_argument("--no-save", action="store_true", help="skip Supabase persistence")
    args = parser.parse_args()

    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    result = asyncio.run(analyze(args.symbol, save=not args.no_save))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    sys.exit(main())
