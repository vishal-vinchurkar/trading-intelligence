"""Congressional-trades signal — honest, disclosure-lag-aware backtest + overlay.

The seductive pitch ("politicians beat the market, copy them") ignores the catch:
you can only act on a trade once it's DISCLOSED, which is 30-45 days after the
fact. This module bakes that lag in by construction — it enters the underlying at
the next open AFTER the disclosure date, never the transaction date — and asks the
honest question: does following congressional BUYS, with the real lag and net of
cost, actually beat just holding the index over the same window?

Two outputs:
  • backtest()  — forward return of lag-aware congress-buy entries vs SPY over the
                  same horizon. The edge (or absence of one), stated plainly.
  • overlay()   — a current-state "congress buying pressure" score per ticker from
                  recent disclosures. Like all non-price signals here it is an
                  OVERLAY (context), NEVER folded into the backtested price score.

Runs on whatever data.congress.fetch_trades returns — real Quiver data if a key is
set, else clearly-labelled synthetic demo data so the logic is verifiable solo.

Run:
  PYTHONPATH=. python -m quant.congress_signal           # auto data source
  PYTHONPATH=. python -m quant.congress_signal --demo    # force synthetic
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from data import congress
from data.backfill import load_cached
from quant.backtest import COST_BPS

RESULTS_PATH = Path(__file__).parent / "congress_results.json"
HORIZON = 21          # trading days held after disclosure
COST = COST_BPS["US"] / 1e4


def _fwd_return(df: pd.DataFrame, on_or_after: pd.Timestamp, horizon: int) -> tuple[float, pd.Timestamp] | None:
    """Enter at the next available open ON/AFTER a date, exit `horizon` bars later."""
    pos = df.index.searchsorted(on_or_after)
    if pos >= len(df) - 1:
        return None
    entry_i = pos + 1  # next session's open — you can't trade the disclosure-day close
    exit_i = entry_i + horizon
    if exit_i >= len(df):
        return None
    entry = float(df["open"].iloc[entry_i])
    exit_px = float(df["close"].iloc[exit_i])
    if entry <= 0:
        return None
    return exit_px / entry - 1.0, df.index[entry_i]


def backtest(trades: list[congress.CongressTrade]) -> dict:
    spy = load_cached("SPY")
    rets, alphas, n_used = [], [], 0
    for t in trades:
        if t.txn_type != "buy" or not t.disclosure_date:
            continue
        df = load_cached(t.ticker)
        if df is None:
            continue
        d = pd.Timestamp(t.disclosure_date)
        r = _fwd_return(df, d, HORIZON)
        if r is None:
            continue
        ret, entry_date = r
        net = ret - COST
        b = _fwd_return(spy, entry_date, HORIZON) if spy is not None else None
        rets.append(net)
        if b is not None:
            alphas.append(net - b[0])
        n_used += 1

    if not rets:
        return {"n": 0, "note": "No usable buy disclosures mapped to price history."}
    rets_a = np.array(rets)
    alphas_a = np.array(alphas) if alphas else np.array([])
    return {
        "n": int(n_used),
        "horizon_days": HORIZON,
        "mean_net_return_pct": round(float(rets_a.mean()) * 100, 3),
        "win_rate_pct": round(float((rets_a > 0).mean()) * 100, 1),
        "mean_alpha_vs_spy_pct": round(float(alphas_a.mean()) * 100, 3) if alphas_a.size else None,
        "share_beating_spy_pct": round(float((alphas_a > 0).mean()) * 100, 1) if alphas_a.size else None,
        "note": "Entry = next open AFTER disclosure (lag-aware), net of US cost, vs SPY same window.",
    }


def overlay(trades: list[congress.CongressTrade], lookback_days: int = 120) -> dict:
    """Current-state congress buying pressure per ticker (net buys − sells, recent
    disclosures). Context overlay — NOT part of the backtested price score."""
    if not trades:
        return {}
    latest = max(pd.Timestamp(t.disclosure_date) for t in trades if t.disclosure_date)
    cutoff = latest - pd.Timedelta(days=lookback_days)
    agg: dict[str, dict] = defaultdict(lambda: {"buys": 0, "sells": 0, "reps": set()})
    for t in trades:
        if not t.disclosure_date or pd.Timestamp(t.disclosure_date) < cutoff:
            continue
        a = agg[t.ticker]
        a["buys" if t.txn_type == "buy" else "sells"] += 1
        a["reps"].add(t.representative)
    return {
        tk: {
            "net_buys": v["buys"] - v["sells"],
            "buys": v["buys"], "sells": v["sells"],
            "distinct_members": len(v["reps"]),
            "bias": "accumulating" if v["buys"] > v["sells"] else
                    "distributing" if v["sells"] > v["buys"] else "mixed",
        }
        for tk, v in sorted(agg.items(), key=lambda kv: kv[1]["buys"] - kv[1]["sells"], reverse=True)
    }


def run(prefer_demo: bool = False) -> dict:
    trades, source = congress.fetch_trades(prefer_demo=prefer_demo)
    is_real = source in ("quiver", "house-clerk")
    caveats = {
        "demo-synthetic": "SYNTHETIC demo data — logic/wiring validation only, NOT a real result. "
                          "No congress data source available.",
        "house-clerk": "REAL data — free House-Clerk PTR filings (PARTIAL coverage: capped filings/yr, "
                       "machine-readable PDFs only). Overlay is current-state context, NOT folded into "
                       "the backtested price score. Not financial advice.",
        "quiver": "REAL Quiver data. Overlay is current-state context, NOT folded into the backtested "
                  "price score. Not financial advice.",
    }
    result = {
        "meta": {
            "source": source,
            "is_real": is_real,
            "what": "Lag-aware congressional-buy backtest + current buying-pressure overlay.",
            "caveat": caveats.get(source, ""),
        },
        "backtest": backtest(trades),
        "overlay_top": dict(list(overlay(trades).items())[:15]),
    }
    RESULTS_PATH.write_text(json.dumps(result, indent=2))
    return result


def _print(r: dict) -> None:
    m, b = r["meta"], r["backtest"]
    print(f"\nCongress signal — source: {m['source']} ({'REAL' if m['is_real'] else 'SYNTHETIC'})")
    print(f"⚠ {m['caveat']}\n")
    if b.get("n", 0) == 0:
        print("No usable trades."); return
    print(f"Lag-aware buy backtest: n={b['n']} · {b['horizon_days']}d hold")
    print(f"  mean net return {b['mean_net_return_pct']}% · win {b['win_rate_pct']}% · "
          f"alpha vs SPY {b['mean_alpha_vs_spy_pct']}% · beat SPY {b['share_beating_spy_pct']}%")
    print("\nTop buying-pressure (recent disclosures):")
    for tk, v in list(r["overlay_top"].items())[:8]:
        print(f"  {tk:8} net {v['net_buys']:+d}  ({v['buys']}b/{v['sells']}s, {v['distinct_members']} members) {v['bias']}")


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    _print(run(prefer_demo="--demo" in sys.argv))
    print(f"\nSaved → {RESULTS_PATH}")
