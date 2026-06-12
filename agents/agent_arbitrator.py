"""Agent 3 — Arbitrator.

The highest-stakes agent: it sees both the technical and fundamental JSON
outputs and makes the final call. No Anthropic API key is required.

Backends (set ARBITRATOR_PROVIDER):
- groq   (default) : a larger reasoning-grade Groq model — free tier, automatable.
- ollama           : a local model on the MacBook, for offline/zero-network runs.
- manual           : do NOT call an LLM. Instead build a handoff prompt that a
                     human can paste into Claude Code (existing plan, $0) to get
                     a top-tier verdict for high-stakes decisions, then write the
                     returned JSON back via `parse_manual_verdict()`.

This keeps the "best available reasoning at $0" intent of the brief without a
paid Anthropic API key.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from agents.llm import json_complete

_PROMPT = (Path(__file__).parent / "prompts" / "arbitrator_system.md").read_text()

def provider() -> str:
    return os.environ.get("ARBITRATOR_PROVIDER", "groq")


def model_id() -> str:
    # A bigger model than Agents 1 & 2 — verify ids at console.groq.com/docs/models.
    return os.environ.get("ARBITRATOR_MODEL", "llama-3.3-70b-versatile")


def _build_user_payload(symbol: str, market_label: str, technical: dict, fundamental: dict) -> str:
    return (
        f"Ticker: {symbol}\n"
        f"Market: {market_label}\n"
        f"Timestamp (UTC): {datetime.now(timezone.utc).isoformat()}\n\n"
        f"=== TECHNICAL ANALYST REPORT ===\n{json.dumps(technical, indent=2)}\n\n"
        f"=== FUNDAMENTAL ANALYST REPORT ===\n{json.dumps(fundamental, indent=2)}\n\n"
        "These two analysts did not see each other's work. Arbitrate and return "
        "your final verdict as JSON per the schema."
    )


def run(symbol: str, market_label: str, technical: dict, fundamental: dict) -> dict:
    """Produce the final arbitrated verdict. Raises if PROVIDER == 'manual'."""
    if provider() == "manual":
        raise RuntimeError(
            "ARBITRATOR_PROVIDER=manual: call build_manual_handoff() and run the "
            "arbitration in Claude Code, then parse_manual_verdict() the result."
        )
    user = _build_user_payload(symbol, market_label, technical, fundamental)
    out = json_complete(_PROMPT, user, provider=provider(), model=model_id(), temperature=0.2)
    out.setdefault("agent", "arbitrator")
    out.setdefault("ticker", symbol)
    return out


def build_manual_handoff(symbol: str, market_label: str, technical: dict, fundamental: dict) -> str:
    """Return a self-contained prompt to paste into Claude Code for a $0,
    top-tier arbitration on high-stakes tickers."""
    return f"{_PROMPT}\n\n---\n\n{_build_user_payload(symbol, market_label, technical, fundamental)}"


def parse_manual_verdict(raw: str, symbol: str) -> dict:
    """Validate a verdict produced manually (e.g. via Claude Code) before saving."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.lstrip().startswith("json"):
            text = text.lstrip()[4:]
    out = json.loads(text)
    out.setdefault("agent", "arbitrator")
    out.setdefault("ticker", symbol)
    return out
