"""Agent 1 — Technical Analyst.

Receives computed indicators (NOT raw fundamentals) and returns a JSON verdict.
Runs on a fast Groq Llama 4 model by default; falls back to Ollama if configured.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from agents.llm import json_complete

_PROMPT = (Path(__file__).parent / "prompts" / "technical_system.md").read_text()

def provider() -> str:
    return os.environ.get("AGENT_PROVIDER", "groq")


def model_id() -> str:
    return os.environ.get("GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")


def run(symbol: str, market_label: str, indicators: dict) -> dict:
    """Produce the technical verdict for one ticker.

    `market_label` e.g. 'India/NSE'. `indicators` is the dict from
    indicators.technical.compute_all().
    """
    user = (
        f"Ticker: {symbol}\n"
        f"Market: {market_label}\n"
        f"Timestamp (UTC): {datetime.now(timezone.utc).isoformat()}\n\n"
        f"Computed indicators (last 90 days of price action):\n"
        f"{json.dumps(indicators, indent=2)}\n\n"
        "Produce your technical verdict as JSON per the schema."
    )
    out = json_complete(_PROMPT, user, provider=provider(), model=model_id())
    out.setdefault("agent", "technical")
    out.setdefault("ticker", symbol)
    return out
