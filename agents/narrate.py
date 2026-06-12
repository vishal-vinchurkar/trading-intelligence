"""Hybrid narration — plain-English thesis over the quant verdict + Phase B overlays.

The deterministic quant score + backtest MAKE the decision; this layer only
EXPLAINS it and flags context the score can't see (rich valuation, looming
earnings, macro regime). It is explicitly subordinate: it must not change the
verdict — at most it raises a `caution`. That keeps the auditable, backtested
spine in charge while giving a human-readable thesis (the thing a PM reads first).

Free: Groq Llama via the existing agents.llm.json_complete. Returns a dict, so a
provider hiccup degrades to None at the call site rather than breaking the scan.
"""

from __future__ import annotations

import os

from agents.llm import json_complete

_SYSTEM = (
    "You are a buy-side analyst writing a one-paragraph thesis for a quant signal. "
    "A deterministic, backtested model has ALREADY decided the verdict and the trade "
    "levels — you do NOT change them. Your job: (1) explain in 2-3 plain sentences WHY "
    "the setup looks the way it does, citing the given numbers; (2) surface any caution "
    "the price model can't see (expensive valuation, earnings within the horizon, macro "
    "headwind). Be specific and sober — no hype, no hedging filler. "
    'Output ONLY JSON: {"thesis": "<2-3 sentences>", "caution": "<one line or null>"}.'
)


def model_id() -> str:
    return os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")


def narrate(signal: dict) -> dict | None:
    """Return {thesis, caution} for a scanned signal, or None on any failure."""
    q = signal.get("quality") or {}
    ev = signal.get("events") or {}
    payload = (
        f"Ticker {signal['symbol']} ({signal['market']}), last {signal['last_close']}.\n"
        f"Quant verdict: {signal['label']} (score {signal['score']}/100, "
        f"tradeable={signal['calibration'].get('tradeable')}).\n"
        f"Components: " + "; ".join(
            f"{k} {c['score']:.0f} ({c['reason']})" for k, c in signal["components"].items()
        ) + ".\n"
        f"Trade: {signal.get('trade')}.\n"
        f"Fundamental quality: {q.get('score')}/100 {q.get('assessment')} "
        f"({'; '.join(q.get('reasons', []))}).\n"
        f"Event risk: {ev.get('flag')} (next earnings {ev.get('next_earnings_date')}, "
        f"{ev.get('days_to_earnings')}d).\n"
        "Write the thesis JSON. Do not restate the verdict as your own decision; explain it."
    )
    try:
        out = json_complete(_SYSTEM, payload, provider="groq", model=model_id(), temperature=0.3)
        return {"thesis": out.get("thesis"), "caution": out.get("caution") or None}
    except Exception:  # noqa: BLE001 — narration is optional polish; never break the scan
        return None


if __name__ == "__main__":
    import json
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    scan = json.loads(open("quant/latest_scan.json").read())
    s = next(x for x in scan["signals"] if x["calibration"].get("tradeable"))
    print(f"{s['symbol']} {s['label']}:")
    print(json.dumps(narrate(s), indent=2))
