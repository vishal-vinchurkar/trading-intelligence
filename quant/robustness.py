"""Survivorship-robustness harness — bound the bias we can't fully eliminate.

The universe is TODAY's names, so the backtest never eats the losses of stocks
that delisted (SVB, First Republic, Bed Bath…). Free price data (yfinance) purges
delisted tickers, so a true point-in-time membership set isn't buildable on this
budget. Instead of pretending the bias is gone, this module BOUNDS it and answers
the skeptic's real question: *is the US-long edge carried by a few hindsight
megawinners (NVDA, AMD), or does it survive when you take them away?*

Three lenses, all on the same rule-based trades the dashboard shows (US longs,
net of cost), reusing quant.backtest_rules._simulate_symbol so the trade logic
can't drift from the headline:
  1. Leave-one-out by name  — drop each symbol in turn; report the worst case
     (the name whose removal hurts expectancy most) and the spread.
  2. Drop-top-K contributors — remove the 1/3/5 names with the largest total net
     contribution; if the edge holds without them, it isn't a few-winners artifact.
  3. Name-level bootstrap   — resample the SET OF NAMES with replacement (the unit
     survivorship acts on) 2000x; the 5th-percentile expectancy is the honest
     "edge if the universe had been a luckier/unluckier draw of survivors."

A positive 5th-percentile expectancy is the headline: the edge is robust to which
survivors happened to populate the universe. It is NOT proof the bias is zero —
the forward paper ledger remains the only unbiased test.

Run:
  PYTHONPATH=. python -m quant.robustness
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from data import universe
from quant.backtest import OOS_MONTHS
from quant.backtest_rules import _simulate_symbol

RESULTS_PATH = Path(__file__).parent / "robustness_results.json"
BOOTSTRAP_N = 2000
BOOTSTRAP_SEED = 7  # fixed → reproducible; no Math.random non-determinism


def _expectancy(net: np.ndarray) -> float:
    """Mean net return per trade, in percent."""
    return round(float(net.mean()) * 100, 3) if len(net) else 0.0


def _profit_factor(net: np.ndarray) -> float | None:
    wins, losses = net[net > 0].sum(), -net[net <= 0].sum()
    return round(float(wins / losses), 2) if losses > 0 else None


def _us_long_trades() -> pd.DataFrame:
    """Every US-long rule-based trade across the universe (the headline edge)."""
    rows: list[dict] = []
    for sym in universe.symbols("US"):
        rows.extend(t for t in _simulate_symbol(sym) if t["direction"] == "long")
    t = pd.DataFrame(rows)
    if not len(t):
        return t
    t["date"] = pd.to_datetime(t["date"])
    return t


def _leave_one_out(t: pd.DataFrame) -> dict:
    base = _expectancy(t["net"].to_numpy())
    rows = []
    for sym, grp in t.groupby("symbol"):
        rest = t[t["symbol"] != sym]["net"].to_numpy()
        rows.append({
            "symbol": sym,
            "trades": int(len(grp)),
            "expectancy_without_pct": _expectancy(rest),
            "delta_pct": round(_expectancy(rest) - base, 3),  # +ve = removing it helps (it was a drag)
        })
    rows.sort(key=lambda r: r["expectancy_without_pct"])  # worst (most edge-carrying name removed) first
    worst = rows[0]
    return {
        "baseline_expectancy_pct": base,
        "worst_case": worst,  # removing this name leaves the LOWEST expectancy → it carried the most edge
        "worst_case_still_positive": worst["expectancy_without_pct"] > 0,
        "per_name": rows,
    }


def _drop_top_k(t: pd.DataFrame, ks=(1, 3, 5)) -> dict:
    contrib = t.groupby("symbol")["net"].sum().sort_values(ascending=False)
    ranked = list(contrib.index)
    out = {"top_contributors": [{"symbol": s, "total_net_pct": round(float(contrib[s]) * 100, 1)}
                                for s in ranked[:max(ks)]]}
    for k in ks:
        kept = t[~t["symbol"].isin(ranked[:k])]["net"].to_numpy()
        out[f"drop_top_{k}"] = {
            "removed": ranked[:k],
            "expectancy_pct": _expectancy(kept),
            "profit_factor": _profit_factor(kept),
            "win_rate_pct": round(float((kept > 0).mean()) * 100, 1) if len(kept) else None,
            "trades": int(len(kept)),
            "still_positive": _expectancy(kept) > 0,
        }
    return out


def _bootstrap_over_names(t: pd.DataFrame, n: int = BOOTSTRAP_N) -> dict:
    """Resample the SET OF NAMES with replacement — survivorship's unit of action."""
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    by_name = {sym: grp["net"].to_numpy() for sym, grp in t.groupby("symbol")}
    names = list(by_name.keys())
    k = len(names)
    means = np.empty(n)
    for i in range(n):
        draw = rng.choice(k, size=k, replace=True)
        pooled = np.concatenate([by_name[names[j]] for j in draw])
        means[i] = pooled.mean()
    pct = lambda q: round(float(np.percentile(means, q)) * 100, 3)
    return {
        "iterations": n,
        "resample_unit": "symbol (block bootstrap by name)",
        "mean_expectancy_pct": round(float(means.mean()) * 100, 3),
        "ci90_pct": [pct(5), pct(95)],
        "p05_expectancy_pct": pct(5),
        "share_positive": round(float((means > 0).mean()), 3),
        "robust": pct(5) > 0,  # headline: edge survives an unlucky draw of survivors
    }


def run() -> dict:
    t = _us_long_trades()
    if not len(t):
        raise SystemExit("No US-long trades — run `python -m data.backfill` then `python -m quant.backtest_rules` first.")

    split = t["date"].max() - pd.DateOffset(months=OOS_MONTHS)
    oos = t[t["date"] > split]

    boot = _bootstrap_over_names(t)
    result = {
        "meta": {
            "scope": "US long, rule-based trades (the headline edge), net of cost",
            "names": int(t["symbol"].nunique()),
            "trades": int(len(t)),
            "date_range": [str(t["date"].min().date()), str(t["date"].max().date())],
            "note": "Bounds survivorship bias; does NOT eliminate it. Free price data purges "
                    "delisted names, so a true point-in-time universe isn't buildable here. The "
                    "forward paper ledger remains the only unbiased test. Not financial advice.",
        },
        "leave_one_out": _leave_one_out(t),
        "drop_top_contributors": _drop_top_k(t),
        "name_bootstrap": boot,
        "name_bootstrap_oos": _bootstrap_over_names(oos) if oos["symbol"].nunique() > 1 else {"robust": None},
        # One honest line the dashboard can show verbatim.
        "verdict": (
            f"Edge survives an unlucky draw of survivors: 5th-pct expectancy "
            f"{boot['p05_expectancy_pct']}%/trade across {boot['iterations']} name-bootstraps, "
            f"{int(boot['share_positive'] * 100)}% of draws positive."
            if boot["robust"] else
            f"FRAGILE: 5th-pct expectancy {boot['p05_expectancy_pct']}%/trade — edge depends on "
            f"which survivors populate the universe. Trust the forward ledger, not this backtest."
        ),
    }
    RESULTS_PATH.write_text(json.dumps(result, indent=2))
    return result


def _print(r: dict) -> None:
    m = r["meta"]
    print(f"\nSurvivorship robustness — {m['scope']}")
    print(f"{m['names']} names · {m['trades']} trades · {m['date_range'][0]}→{m['date_range'][1]}\n")

    lo = r["leave_one_out"]
    w = lo["worst_case"]
    print(f"Baseline expectancy: {lo['baseline_expectancy_pct']}%/trade")
    print(f"Leave-one-out worst case: drop {w['symbol']} → {w['expectancy_without_pct']}%/trade "
          f"({'still +' if lo['worst_case_still_positive'] else 'goes NEGATIVE'})\n")

    print("Drop top contributors (does a few winners carry it?):")
    dt = r["drop_top_contributors"]
    for k in (1, 3, 5):
        d = dt[f"drop_top_{k}"]
        print(f"  −top{k} ({', '.join(d['removed'])}): exp {d['expectancy_pct']}%  "
              f"win {d['win_rate_pct']}%  PF {d['profit_factor']}  ({'+' if d['still_positive'] else 'NEG'})")

    b = r["name_bootstrap"]
    print(f"\nName-level bootstrap ({b['iterations']}x): mean {b['mean_expectancy_pct']}%  "
          f"90% CI [{b['ci90_pct'][0]}, {b['ci90_pct'][1]}]  p05 {b['p05_expectancy_pct']}%  "
          f"{int(b['share_positive']*100)}% positive")
    print(f"\n{r['verdict']}")


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    _print(run())
    print(f"\nSaved → {RESULTS_PATH}")
