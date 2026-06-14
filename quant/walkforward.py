"""Walk-forward / temporal-stability test — is the edge persistent, or one regime?

The reviewer's critique: "No walk-forward / no out-of-sample on a frozen universe
— 'out-of-sample' here is just time out-of-sample on today's tickers." Fair. This
module answers the *temporal* half: does the US-long edge show up consistently
across the decade, or is it a 2020-21 momentum-bubble artifact wearing a 10-year
costume?

A note on method: this strategy has NO fitted parameters — score weights (35/30/
25/10), the 2xATR stop, the 1.5 R:R gate are all fixed a priori, not optimised on
the data. So classic walk-forward (re-fit each window, test on the next) has
nothing to re-fit; the honest analogue is **temporal partitioning** — slice the
trades into sequential periods and ask whether the edge holds in each. Two views:

  • Per calendar year  — the cleanest "which years paid, which didn't."
  • Rolling 12-month    — stepped quarterly, to catch regime transitions years miss.

Headline: the share of periods with a positive net edge, and the worst period. An
edge that's positive in most years across different regimes is a far stronger
claim than a single 10-year average that could be one fat tail.

Run:
  PYTHONPATH=. python -m quant.walkforward
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from data import universe
from quant.backtest_rules import _simulate_symbol, _stats

RESULTS_PATH = Path(__file__).parent / "walkforward_results.json"


def _us_long_trades() -> pd.DataFrame:
    rows = [t for s in universe.symbols("US")
            for t in _simulate_symbol(s) if t["direction"] == "long"]
    t = pd.DataFrame(rows)
    t["entry_date"] = pd.to_datetime(t["entry_date"])
    return t.sort_values("entry_date").reset_index(drop=True)


def _period_stats(t: pd.DataFrame, key: str) -> list[dict]:
    out = []
    for label, grp in t.groupby(key):
        s = _stats(grp)
        if s.get("n", 0) == 0:
            continue
        out.append({
            "period": str(label),
            "n": s["n"],
            "win_rate": s["win_rate"],
            "expectancy_pct": s["expectancy_pct"],
            "profit_factor": s["profit_factor"],
        })
    return out


def _rolling_12m(t: pd.DataFrame) -> list[dict]:
    """Non-overlapping-labelled rolling 12-month windows, stepped quarterly."""
    start, end = t["entry_date"].min(), t["entry_date"].max()
    out, cur = [], start
    while cur + pd.DateOffset(months=12) <= end + pd.DateOffset(days=1):
        win = t[(t["entry_date"] >= cur) & (t["entry_date"] < cur + pd.DateOffset(months=12))]
        s = _stats(win)
        if s.get("n", 0) >= 10:  # ignore thin windows — noise, not signal
            out.append({
                "window_start": str(cur.date()),
                "n": s["n"], "win_rate": s["win_rate"],
                "expectancy_pct": s["expectancy_pct"], "profit_factor": s["profit_factor"],
            })
        cur += pd.DateOffset(months=3)
    return out


def _consistency(periods: list[dict]) -> dict:
    exps = [p["expectancy_pct"] for p in periods if p["expectancy_pct"] is not None]
    if not exps:
        return {}
    pos = [e for e in exps if e > 0]
    worst = min(periods, key=lambda p: p["expectancy_pct"])
    return {
        "periods": len(exps),
        "positive": len(pos),
        "share_positive": round(len(pos) / len(exps), 2),
        "median_expectancy_pct": round(float(np.median(exps)), 3),
        "worst_period": worst["period"] if "period" in worst else worst.get("window_start"),
        "worst_expectancy_pct": worst["expectancy_pct"],
    }


def run() -> dict:
    t = _us_long_trades()
    t["year"] = t["entry_date"].dt.year

    by_year = _period_stats(t, "year")
    rolling = _rolling_12m(t)
    yc = _consistency(by_year)

    result = {
        "meta": {
            "what": "US-long edge across time — per calendar year and rolling 12-month windows.",
            "method": "Strategy has no fitted parameters, so this is temporal partitioning, "
                      "not parameter walk-forward. Trades bucketed by entry date.",
            "date_range": [str(t["entry_date"].min().date()), str(t["entry_date"].max().date())],
            "note": "Net of cost. Per-year edge persistence is the regime-robustness test. "
                    "Not financial advice.",
        },
        "by_year": by_year,
        "rolling_12m": rolling,
        "year_consistency": yc,
        # Robust if the edge is positive in a clear majority of years.
        "robust": bool(yc.get("share_positive", 0) >= 0.7),
    }
    RESULTS_PATH.write_text(json.dumps(result, indent=2))
    return result


def _print(r: dict) -> None:
    print(f"\nWalk-forward / temporal stability — {r['meta']['what']}")
    print(f"{r['meta']['date_range'][0]}→{r['meta']['date_range'][1]}\n")
    print(f"{'year':>6} {'n':>5} {'win%':>7} {'exp%':>9} {'PF':>6}")
    for p in r["by_year"]:
        print(f"{p['period']:>6} {p['n']:>5} {str(p['win_rate']):>7} {str(p['expectancy_pct']):>9} {str(p['profit_factor']):>6}")
    yc = r["year_consistency"]
    print(f"\nConsistency: edge positive in {yc.get('positive')}/{yc.get('periods')} years "
          f"({int(yc.get('share_positive', 0) * 100)}%) · median {yc.get('median_expectancy_pct')}%/trade · "
          f"worst year {yc.get('worst_period')} at {yc.get('worst_expectancy_pct')}%")
    print(f"Verdict: {'ROBUST across regimes' if r['robust'] else 'REGIME-DEPENDENT — edge not consistent year to year'}")
    print(f"\nRolling 12m windows: {len(r['rolling_12m'])} (stepped quarterly)")


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    _print(run())
    print(f"\nSaved → {RESULTS_PATH}")
