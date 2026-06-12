"""Agent 2 — Fundamental Researcher.

Receives fundamentals + macro/news context (NOT price charts) and returns a
JSON verdict. Runs on a fast Groq Llama 4 model by default.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from agents.llm import json_complete

_PROMPT = (Path(__file__).parent / "prompts" / "fundamental_system.md").read_text()

def provider() -> str:
    return os.environ.get("AGENT_PROVIDER", "groq")


def model_id() -> str:
    return os.environ.get("GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")


def run(
    symbol: str,
    market_label: str,
    fundamentals: dict,
    macro: dict | None = None,
    news: list | None = None,
) -> dict:
    """Produce the fundamental verdict for one ticker."""
    user = (
        f"Ticker: {symbol}\n"
        f"Market: {market_label}\n"
        f"Timestamp (UTC): {datetime.now(timezone.utc).isoformat()}\n\n"
        f"Fundamentals:\n{json.dumps(fundamentals, indent=2)}\n\n"
        f"Macro context:\n{json.dumps(macro or {}, indent=2)}\n\n"
        f"Recent news headlines (last 7 days):\n{json.dumps(news or [], indent=2)}\n\n"
        "Produce your fundamental verdict as JSON per the schema."
    )
    out = json_complete(_PROMPT, user, provider=provider(), model=model_id())
    out.setdefault("agent", "fundamental")
    out.setdefault("ticker", symbol)
    return out
