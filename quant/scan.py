"""Scan the whole universe → the ranked 'Top Signals' the dashboard shows.

For every name: compute the conviction score, size the volatility, build the
trade construct, and attach the band's BACKTESTED hit-rate (the honest, out-of-
sample calibration — this is what the dashboard shows instead of an LLM's made-up
confidence). The user never browses the universe; they read the top of this list
and their pinned favourites.

Writes quant/latest_scan.json, which the Next.js dashboard reads directly (no DB
migration needed to demo). A later cron can also push to Supabase.

Run:
  PYTHONPATH=. python -m quant.scan
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from data import events as ev_mod
from data import fetcher_india  # yfinance fundamentals — keyless, works for US tickers too
from data import fetcher_macro
from data import universe
from data.backfill import load_cached
from indicators import technical as ta
from quant import quality as quality_mod
from quant import score as qscore
from quant import trade as qtrade

OUT_PATH = Path(__file__).parent / "latest_scan.json"
RULES_PATH = Path(__file__).parent / "backtest_rules_results.json"
PORTFOLIO_PATH = Path(__file__).parent / "portfolio_results.json"

# The user's pinned watchlist — always shown front-and-centre regardless of score.
# Edit freely; these must exist in data/universe.py.
FAVOURITES = ["AAPL", "RELIANCE.NS"]


def _rules() -> dict:
    return json.loads(RULES_PATH.read_text()) if RULES_PATH.exists() else {}


def _calibration(band: str, market: str | None, direction: str, rules: dict) -> dict:
    """Calibration from the RULE-BASED backtest — i.e. the exact trade we show
    (entry/2xATR stop/target/time-stop), net of cost, out-of-sample. This is the
    honest number, and it carries whether the trade is actually tradeable: only
    US longs cleared the bar; India longs and all shorts were net-negative."""
    if direction == "long":
        src = (rules.get("by_market_long", {}).get(market, {}) or {}).get("out_of_sample", {})
    elif direction == "short":
        src = (rules.get("by_band", {}).get(band, {}) or {}).get("out_of_sample", {})
    else:
        src = {}

    exp = src.get("expectancy_pct")
    tradeable = bool(market == "US" and direction == "long" and exp is not None and exp > 0)
    if direction == "none":
        reason = "NEUTRAL — no trade"
    elif tradeable:
        reason = "US long — net-positive expectancy out-of-sample"
    elif direction == "short":
        reason = "Shorts were net-negative in backtest — informational only"
    elif market == "India":
        reason = "India price signal had no net edge — informational only"
    else:
        reason = "Below the tradeable bar — informational only"

    return {
        "band": band,
        "market": market,
        "tradeable": tradeable,
        "reason": reason,
        "win_rate": src.get("win_rate"),
        "expectancy_pct": exp,
        "profit_factor": src.get("profit_factor"),
        "samples": src.get("n"),
        "avg_hold_days": src.get("avg_hold_days"),
    }


def _enrich(symbol: str) -> tuple[dict | None, dict | None]:
    """Fundamental quality + event context for a name (Phase B overlay).

    Keyless yfinance for both (fetcher_india.fetch_fundamentals works on US
    tickers too) so we never touch the Alpha Vantage daily limit. Each is a
    current-state overlay — NOT folded into the backtested quant score. Failures
    degrade to None rather than breaking the scan."""
    quality = events = None
    try:
        quality = quality_mod.quality_score(fetcher_india.fetch_fundamentals(symbol))
    except Exception:  # noqa: BLE001 — yfinance .info is flaky; overlay is optional
        pass
    try:
        events = ev_mod.event_context(symbol)
    except Exception:  # noqa: BLE001
        pass
    return quality, events


def scan_one(symbol: str, rules: dict, enrich: bool = False) -> dict | None:
    df = load_cached(symbol)
    if df is None or len(df) < 200:
        return None
    market = universe.market_of(symbol)
    bench = load_cached(universe.benchmark_for(symbol))
    bc = bench["close"] if bench is not None else None

    ind = ta.compute_all(df)
    sc = qscore.score(df, bc)
    direction = qtrade.direction_for(sc["label"])
    cal = _calibration(sc["label"], market, direction, rules)
    # Enrich the names you'd actually act on (tradeable or pinned) — keyless, so
    # the rest of the scan stays fast and the Alpha Vantage quota is untouched.
    quality, events = (_enrich(symbol) if (enrich and (cal["tradeable"] or symbol in FAVOURITES)) else (None, None))

    # Last 120 sessions of price + 50DMA for the dashboard chart (closes only —
    # enough to draw the trend and overlay the trade levels, small JSON footprint).
    tail = df.tail(120)
    sma50 = ta.sma(df["close"], 50).tail(120)
    history = [
        {"d": idx.strftime("%Y-%m-%d"), "c": round(float(c), 2),
         "m": (None if pd.isna(m) else round(float(m), 2))}
        for idx, c, m in zip(tail.index, tail["close"], sma50)
    ]
    trade = qtrade.build(
        ind["last_close"], ind["volatility"]["atr_14"],
        ind["key_levels"]["support"], ind["key_levels"]["resistance"], direction,
    )
    return {
        "symbol": symbol,
        "market": market,
        "sector": universe.sector_of(symbol),
        "as_of": str(df.index[-1].date()),
        "last_close": ind["last_close"],
        "score": sc["score"],
        "label": sc["label"],
        "core": sc["core"],
        "conviction": round(abs(sc["score"] - 50), 1),  # distance from neutral → ranking key
        "components": sc["components"],
        "timing": sc["timing"],
        "volatility": ind["volatility"],
        "expected_move": ind["expected_move"],
        "key_levels": ind["key_levels"],
        "trade": trade,
        "calibration": cal,
        "quality": quality,   # Phase B: current-state fundamental overlay (None if not enriched)
        "events": events,     # Phase B: earnings/event-risk flag (None if not enriched)
        "history": history,
        "is_favourite": symbol in FAVOURITES,
    }


def run(enrich: bool = True) -> dict:
    rules = _rules()
    signals = [s for s in (scan_one(sym, rules, enrich=enrich) for sym in universe.symbols()) if s]
    # Rank by conviction (distance from neutral): strongest longs and shorts float up.
    signals.sort(key=lambda s: s["conviction"], reverse=True)
    as_of = max((s["as_of"] for s in signals), default=None)

    portfolio = json.loads(PORTFOLIO_PATH.read_text()) if PORTFOLIO_PATH.exists() else {}
    us_long = (rules.get("by_market_long", {}).get("US", {}) or {}).get("out_of_sample", {})

    # Macro regime once per market present (Phase B overlay — context, not a signal).
    macro = {}
    for mkt in sorted({s["market"] for s in signals if s["market"]}):
        try:
            macro[mkt] = fetcher_macro.macro_context(mkt)
        except Exception:  # noqa: BLE001
            macro[mkt] = None

    result = {
        "as_of": as_of,
        "universe_size": len(signals),
        "macro": macro,
        # The honest, validated headline: the rule-based US-long result + the
        # portfolio curve, with the survivorship caveat travelling alongside.
        "evidence": {
            "us_long_oos": {
                "win_rate": us_long.get("win_rate"),
                "expectancy_pct": us_long.get("expectancy_pct"),
                "profit_factor": us_long.get("profit_factor"),
                "trades": us_long.get("n"),
            },
            "portfolio": portfolio.get("strategy", {}),
            "benchmark": portfolio.get("benchmark", {}),
            "rule": rules.get("meta", {}).get("rule"),
            "date_range": rules.get("meta", {}).get("date_range"),
            "caveats": "Backtested on TODAY's universe (survivorship bias) — treat returns as an "
                       "upper bound, not a forward expectation. Perfect stop fills assumed. The "
                       "forward Alpaca paper ledger is the unbiased test. Not financial advice.",
        },
        "favourites": FAVOURITES,
        "signals": signals,
    }
    OUT_PATH.write_text(json.dumps(result, indent=2))
    # Mirror into the dashboard so the Next.js app bundles the latest scan at build
    # time (no DB round-trip needed to demo). A later cron can push to Supabase too.
    dash = Path(__file__).parent.parent / "dashboard" / "data" / "scan.json"
    dash.parent.mkdir(parents=True, exist_ok=True)
    dash.write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    r = run()
    ev = r["evidence"]
    print(f"Scanned {r['universe_size']} names · as of {r['as_of']}")
    print(f"US-long OOS: win {ev['us_long_oos'].get('win_rate')}% · exp {ev['us_long_oos'].get('expectancy_pct')}%/trade · PF {ev['us_long_oos'].get('profit_factor')}\n")
    print(f"{'rank':>4}  {'symbol':12} {'score':>6} {'label':11} {'win%':>6} {'R:R':>5} {'tradeable':>9}")
    for i, s in enumerate(r["signals"][:14], 1):
        cal = s["calibration"]
        rr = s["trade"]["risk_reward"] if s["trade"] else None
        fav = "★" if s["is_favourite"] else " "
        td = "TRADE" if cal["tradeable"] else "info"
        print(f"{i:>4}{fav} {s['symbol']:12} {s['score']:>6} {s['label']:11} {str(cal['win_rate']):>6} {str(rr):>5} {td:>9}")
    print(f"\nSaved → {OUT_PATH}")
