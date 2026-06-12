"""Turn a conviction signal into a placeable trade: entry, stop, target, R:R.

The stop and target are anchored to STRUCTURE — recent support/resistance, with
ATR as the fallback unit — and then the reward:risk is *computed* from those
levels, not asserted. If the resulting R:R is below the threshold, the trade is
flagged not-actionable (a real desk passes on a 1:0.8 setup no matter how pretty
the thesis). This is what makes "BUY" mean "buy here, risk to there, target there"
instead of a vibe.
"""

from __future__ import annotations

MIN_RR = 1.5          # below this, the setup isn't worth taking
ATR_STOP_MULT = 2.0   # fallback stop distance when structure is unhelpful


def build(
    last_close: float,
    atr: float,
    support: list[float],
    resistance: list[float],
    direction: str,   # "long" | "short" | "none"
) -> dict | None:
    """Return a trade construct, or None for a no-trade (NEUTRAL) signal."""
    if direction == "none" or atr <= 0:
        return None
    entry = float(last_close)
    # Targets must clear at least 1·ATR of noise to count as real structure.
    above = sorted([r for r in resistance if r > entry + atr])
    below = sorted([s for s in support if s < entry - atr], reverse=True)

    if direction == "long":
        # Volatility stop (standard 2·ATR) — a defensible, name-adaptive risk unit.
        stop = entry - ATR_STOP_MULT * atr
        # Target the nearest meaningful resistance, else a 4·ATR measured extension.
        target = above[0] if above else (entry + 4 * atr)
        risk = entry - stop
        reward = target - entry
    else:  # short
        stop = entry + ATR_STOP_MULT * atr
        target = below[0] if below else (entry - 4 * atr)
        risk = stop - entry
        reward = entry - target

    if risk <= 0:
        return None
    rr = reward / risk
    return {
        "direction": direction,
        "entry": round(entry, 2),
        "stop": round(stop, 2),
        "target": round(target, 2),
        "risk_per_share": round(risk, 2),
        "reward_per_share": round(reward, 2),
        "risk_reward": round(rr, 2),
        "actionable": bool(rr >= MIN_RR),
        "note": (
            f"R:R {rr:.1f} ≥ {MIN_RR} — actionable"
            if rr >= MIN_RR
            else f"R:R {rr:.1f} below {MIN_RR} — structure doesn't justify the trade; watch only"
        ),
    }


def direction_for(label: str) -> str:
    if label in ("STRONG_BUY", "BUY"):
        return "long"
    if label in ("STRONG_SELL", "SELL"):
        return "short"
    return "none"
