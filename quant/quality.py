"""Stream 2 — fundamental quality (current-state overlay).

Turns the fundamental fields the fetchers already return (valuation multiples,
margins, growth, leverage) into an interpretable 0–100 quality score with
per-component reasons.

HONESTY RULE (non-negotiable, see docs/PHASE-B-PLAN.md): this is a
CURRENT-STATE overlay. None of these fields are point-in-time backtestable on
free data, so quality must NEVER be folded into the backtested, price-only quant
score. This module deliberately does not import `quant.score`. The arbitrator
(Stream 4) may use quality to downgrade/veto/size — never to move the base
score.

Robustness: most fundamentals are frequently None (especially India via
yfinance `.info`). Every sub-score degrades gracefully to a neutral 50.0 when
its inputs are missing, and cites the actual numbers when present.

Unit handling (both data sources are normalised through here):
  - margins / ROE / growth: yfinance reports fractions (0.25), Alpha Vantage
    sometimes percents (25.0). Heuristic: abs(value) <= 1 → treat as fraction.
  - debt_to_equity: yfinance reports a percent (150.0 == 1.5x), Alpha Vantage a
    ratio (1.5). Heuristic: value > 5 → treat as percent, divide by 100.
"""

from __future__ import annotations


# ---- weights for the overall blend -------------------------------------------------
_WEIGHTS = {
    "valuation": 0.30,
    "profitability": 0.30,
    "growth": 0.25,
    "leverage": 0.15,
}


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def _as_fraction(value: float) -> float:
    """Normalise a margin/ROE/growth value to a fraction (0.25 == 25%).

    Both yfinance and Alpha Vantage usually report fractions (0.25), but ROE can
    legitimately exceed 100% as a fraction (AAPL ≈ 1.49). Only treat clearly
    percent-scaled values (abs > 3, e.g. 25.0) as percents to divide down."""
    return value if abs(value) <= 3.0 else value / 100.0


def _pct(frac: float) -> str:
    """Human-readable percent from a fraction."""
    return f"{frac * 100:.1f}%"


# ---- valuation ---------------------------------------------------------------------

def _score_valuation(val: dict) -> dict:
    """Higher score = cheaper / more attractive. Sub-scores blended across the
    available multiples; missing ones simply drop out of the average."""
    pe = val.get("pe_ratio")
    pb = val.get("pb_ratio")
    peg = val.get("peg_ratio")
    ev = val.get("ev_to_ebitda")

    parts: list[float] = []
    notes: list[str] = []

    if pe is not None and pe > 0:
        # PE < 15 attractive (→100), > 40 expensive (→0), linear between.
        s = _clamp(100.0 * (40.0 - pe) / (40.0 - 15.0))
        parts.append(s)
        notes.append(f"PE {pe:.1f}")
    if pb is not None and pb > 0:
        # PB < 1.5 attractive, > 6 expensive.
        s = _clamp(100.0 * (6.0 - pb) / (6.0 - 1.5))
        parts.append(s)
        notes.append(f"P/B {pb:.1f}")
    if peg is not None and peg > 0:
        # PEG < 1 great (→100), > 2 poor (→0).
        s = _clamp(100.0 * (2.0 - peg) / (2.0 - 1.0))
        parts.append(s)
        notes.append(f"PEG {peg:.2f}")
    if ev is not None and ev > 0:
        # EV/EBITDA < 8 attractive, > 20 expensive.
        s = _clamp(100.0 * (20.0 - ev) / (20.0 - 8.0))
        parts.append(s)
        notes.append(f"EV/EBITDA {ev:.1f}")

    if not parts:
        return {"score": 50.0, "reason": "no valuation data"}

    score = round(sum(parts) / len(parts), 1)
    if score > 60:
        verdict = "attractive multiples"
    elif score >= 40:
        verdict = "fair multiples"
    else:
        verdict = "rich multiples"
    return {"score": score, "reason": f"{verdict} ({', '.join(notes)})"}


# ---- profitability -----------------------------------------------------------------

def _score_profitability(prof: dict) -> dict:
    """Higher margins / ROE → higher score."""
    roe = prof.get("roe")
    pm = prof.get("profit_margin")
    om = prof.get("operating_margin")

    parts: list[float] = []
    notes: list[str] = []

    if roe is not None:
        r = _as_fraction(roe)
        # ROE 0% → 0, 25%+ → 100.
        s = _clamp(100.0 * r / 0.25)
        parts.append(s)
        notes.append(f"ROE {_pct(r)}")
    if pm is not None:
        m = _as_fraction(pm)
        # Net margin 0% → 0, 20%+ → 100.
        s = _clamp(100.0 * m / 0.20)
        parts.append(s)
        notes.append(f"net margin {_pct(m)}")
    if om is not None:
        m = _as_fraction(om)
        # Operating margin 0% → 0, 25%+ → 100.
        s = _clamp(100.0 * m / 0.25)
        parts.append(s)
        notes.append(f"op margin {_pct(m)}")

    if not parts:
        return {"score": 50.0, "reason": "no profitability data"}

    score = round(sum(parts) / len(parts), 1)
    if score > 60:
        verdict = "strong profitability"
    elif score >= 40:
        verdict = "moderate profitability"
    else:
        verdict = "weak profitability"
    return {"score": score, "reason": f"{verdict} ({', '.join(notes)})"}


# ---- growth ------------------------------------------------------------------------

def _score_growth(growth: dict) -> dict:
    """Higher YoY growth → higher score; negative growth → low."""
    rev = growth.get("revenue_yoy")
    earn = growth.get("earnings_yoy")

    parts: list[float] = []
    notes: list[str] = []

    if rev is not None:
        g = _as_fraction(rev)
        # -10% → 0, +30%+ → 100; 0% maps to 25.
        s = _clamp(100.0 * (g + 0.10) / (0.30 + 0.10))
        parts.append(s)
        notes.append(f"revenue {_pct(g)} YoY")
    if earn is not None:
        g = _as_fraction(earn)
        # -20% → 0, +40%+ → 100.
        s = _clamp(100.0 * (g + 0.20) / (0.40 + 0.20))
        parts.append(s)
        notes.append(f"earnings {_pct(g)} YoY")

    if not parts:
        return {"score": 50.0, "reason": "no growth data"}

    score = round(sum(parts) / len(parts), 1)
    if score > 60:
        verdict = "growing"
    elif score >= 40:
        verdict = "flattish growth"
    else:
        verdict = "shrinking / weak growth"
    return {"score": score, "reason": f"{verdict} ({', '.join(notes)})"}


# ---- leverage ----------------------------------------------------------------------

def _score_leverage(lev: dict) -> dict:
    """Lower debt/equity → higher score."""
    de = lev.get("debt_to_equity")
    if de is None:
        return {"score": 50.0, "reason": "no leverage data"}

    # yfinance reports D/E as a percent (150.0 == 1.5x); AV as a ratio (1.5).
    de_ratio = de / 100.0 if de > 5 else de
    de_ratio = max(0.0, de_ratio)

    # D/E 0 → 100, 2.0+ → 0.
    score = round(_clamp(100.0 * (2.0 - de_ratio) / 2.0), 1)
    if score > 60:
        verdict = "low leverage"
    elif score >= 40:
        verdict = "moderate leverage"
    else:
        verdict = "high leverage"
    return {"score": score, "reason": f"{verdict} (D/E {de_ratio:.2f}x)"}


# ---- public API --------------------------------------------------------------------

def quality_score(fundamentals: dict) -> dict:
    """Current-state fundamental quality, 0–100, with interpretable components.

    See module docstring for the honesty rule and unit-handling heuristics.
    Returns the FROZEN Stream-2 contract shape, fully JSON-serialisable.
    """
    fundamentals = fundamentals or {}

    components = {
        "valuation": _score_valuation(fundamentals.get("valuation") or {}),
        "profitability": _score_profitability(fundamentals.get("profitability") or {}),
        "growth": _score_growth(fundamentals.get("growth") or {}),
        "leverage": _score_leverage(fundamentals.get("leverage") or {}),
    }

    overall = sum(components[k]["score"] * w for k, w in _WEIGHTS.items())
    overall = round(overall, 1)

    val_score = components["valuation"]["score"]
    if val_score > 60:
        assessment = "CHEAP"
    elif val_score >= 40:
        assessment = "FAIR"
    else:
        assessment = "EXPENSIVE"

    # Most salient reasons: lead with valuation (drives the assessment), then
    # the strongest and weakest of the remaining components for contrast.
    others = sorted(
        ("profitability", "growth", "leverage"),
        key=lambda k: components[k]["score"],
    )
    reasons = [
        components["valuation"]["reason"],
        components[others[-1]]["reason"],  # strongest non-valuation
        components[others[0]]["reason"],   # weakest non-valuation
    ]
    # De-duplicate "no data" filler while preserving order; keep 2–4 reasons.
    seen = set()
    deduped = []
    for r in reasons:
        if r not in seen:
            seen.add(r)
            deduped.append(r)
    reasons = deduped[:4]

    return {
        "score": overall,
        "components": components,
        "assessment": assessment,
        "reasons": reasons,
    }


if __name__ == "__main__":
    import json

    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        pass

    # Use yfinance (data.fetcher_india) for BOTH names to conserve the
    # Alpha Vantage daily quota — yfinance is keyless and handles US tickers too.
    from data import fetcher_india

    def _smoke(symbol: str) -> None:
        fundamentals = None
        for attempt in range(3):  # yfinance .info is flaky; retry a couple times
            try:
                fundamentals = fetcher_india.fetch_fundamentals(symbol)
                if fundamentals and any(
                    v is not None
                    for grp in ("valuation", "profitability", "growth", "leverage")
                    for v in (fundamentals.get(grp) or {}).values()
                ):
                    break
            except Exception as exc:  # noqa: BLE001 — smoke test only
                print(f"[{symbol}] fetch attempt {attempt + 1} failed: {exc}")
        result = quality_score(fundamentals or {})
        print(f"\n=== {symbol} ===")
        print(json.dumps(result, indent=2))

    _smoke("AAPL")
    _smoke("RELIANCE.NS")
