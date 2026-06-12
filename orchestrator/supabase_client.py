"""Supabase persistence helpers.

Thin wrappers around supabase-py for the tables in schema.sql. Uses the service
role key (server-side only — never ship it to the browser).
"""

from __future__ import annotations

import os

from supabase import Client, create_client


def get_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not (url and key):
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set (.env).")
    return create_client(url, key)


def upsert_ticker(client: Client, symbol: str, market: str, exchange: str, name: str | None = None) -> str:
    """Insert the ticker if new; return its UUID."""
    existing = client.table("tickers").select("id").eq("symbol", symbol).execute()
    if existing.data:
        return existing.data[0]["id"]
    row = (
        client.table("tickers")
        .insert({"symbol": symbol, "market": market, "exchange": exchange, "name": name})
        .execute()
    )
    return row.data[0]["id"]


def save_agent_output(client: Client, ticker_id: str, agent: str, output: dict, model_used: str) -> None:
    client.table("agent_outputs").insert(
        {"ticker_id": ticker_id, "agent": agent, "output": output, "model_used": model_used}
    ).execute()


def save_prediction(client: Client, ticker_id: str, arb: dict, technical: dict, fundamental: dict) -> str:
    pred = arb.get("prediction", {})
    row = (
        client.table("predictions")
        .insert(
            {
                "ticker_id": ticker_id,
                "verdict": arb.get("verdict"),
                "confidence": arb.get("confidence"),
                "signal_alignment": arb.get("signal_alignment"),
                "reasoning": arb.get("reasoning"),
                "prediction_5d": pred.get("5_day"),
                "prediction_15d": pred.get("15_day"),
                "prediction_30d": pred.get("30_day"),
                "invalidation": arb.get("invalidation"),
                "risk_reward": arb.get("risk_reward"),
                "technical_signal": technical.get("signal"),
                "fundamental_signal": fundamental.get("signal"),
            }
        )
        .execute()
    )
    return row.data[0]["id"]
