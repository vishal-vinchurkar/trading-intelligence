"""Portfolio equity curve — the honest "what would this do to my account."

Per-trade expectancy is necessary but not sufficient: trades overlap, so the
real questions are CAGR, volatility, Sharpe, and — the one that actually decides
whether you can stomach it — **max drawdown**. This builds a proper daily,
mark-to-market equity curve for the only strategy the backtests say is tradeable
(US long-only), equal-weighting open positions, netting costs, and compares it to
simply buying and holding SPY over the same window.

Assumptions (stated, not hidden):
  • US longs only (India + shorts are net-negative — excluded).
  • Equal weight across whatever positions are open each day; flat (cash, 0%) when
    none are open. No leverage. Capacity/position caps not modelled.
  • Round-trip cost charged on each position's entry day.
This is a simplified but valid portfolio sim — the forward Alpaca paper ledger is
the real-money-faithful version.

Run:
  PYTHONPATH=. python -m quant.portfolio
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from data.backfill import load_cached
from quant.backtest import COST_BPS
from quant.backtest_rules import _simulate_symbol

RESULTS_PATH = Path(__file__).parent / "portfolio_results.json"
TRADING_DAYS = 252


def _daily_returns(symbol: str) -> pd.Series:
    df = load_cached(symbol)
    return df["close"].pct_change() if df is not None else pd.Series(dtype=float)


def _curve_stats(equity: pd.Series, label: str) -> dict:
    rets = equity.pct_change().dropna()
    years = max((equity.index[-1] - equity.index[0]).days / 365.25, 1e-9)
    cagr = float(equity.iloc[-1] ** (1 / years) - 1)
    vol = float(rets.std() * np.sqrt(TRADING_DAYS))
    sharpe = float((rets.mean() * TRADING_DAYS) / vol) if vol > 0 else None
    peak = equity.cummax()
    max_dd = float(((equity - peak) / peak).min())
    return {
        "label": label,
        "total_return_pct": round((float(equity.iloc[-1]) - 1) * 100, 1),
        "cagr_pct": round(cagr * 100, 2),
        "vol_pct": round(vol * 100, 1),
        "sharpe": None if sharpe is None else round(sharpe, 2),
        "max_drawdown_pct": round(max_dd * 100, 1),
    }


def strategy_daily_returns() -> tuple[pd.Series, pd.DataFrame, pd.Series]:
    """The US-long book's daily return series — the honest equity-curve input.

    Returns (strat, tdf, spy_close): `strat` is the daily portfolio return on the
    master (SPY) calendar, net of entry-day cost; `tdf` the underlying trades;
    `spy_close` SPY's close over the same span. Factored out so the factor-
    attribution (quant.attribution) regresses the EXACT series this curve is built
    from, not a re-derived proxy.
    """
    trades = [t for s in __import__("data.universe", fromlist=["symbols"]).symbols("US")
              for t in _simulate_symbol(s) if t["direction"] == "long"]
    tdf = pd.DataFrame(trades)
    tdf["entry_date"] = pd.to_datetime(tdf["entry_date"])
    tdf["exit_date"] = pd.to_datetime(tdf["exit_date"])

    # Daily simple returns per symbol, once.
    rets = {s: _daily_returns(s) for s in tdf["symbol"].unique()}
    cost = COST_BPS["US"] / 1e4

    # Master calendar = SPY's trading days over the trade span.
    spy = load_cached("SPY")["close"]
    cal = spy.index[(spy.index >= tdf["entry_date"].min()) & (spy.index <= tdf["exit_date"].max())]

    # Each day: equal-weight the positions open that day; charge cost on entry day.
    strat = pd.Series(0.0, index=cal)
    for day in cal:
        open_t = tdf[(tdf["entry_date"] <= day) & (tdf["exit_date"] > day)]
        if open_t.empty:
            continue
        day_rets = []
        for _, tr in open_t.iterrows():
            r = rets[tr["symbol"]].get(day, 0.0)
            if pd.isna(r):
                r = 0.0
            if tr["entry_date"] == day:
                r -= cost  # entry-day cost drag
            day_rets.append(r)
        strat.loc[day] = float(np.mean(day_rets))
    return strat, tdf, spy


def run() -> dict:
    strat, tdf, spy = strategy_daily_returns()
    cal = strat.index

    strat_equity = (1 + strat).cumprod()
    spy_aligned = spy.reindex(cal).ffill()
    spy_equity = spy_aligned / spy_aligned.iloc[0]

    avg_positions = float(
        np.mean([
            len(tdf[(tdf["entry_date"] <= d) & (tdf["exit_date"] > d)]) for d in cal[:: 5]
        ])
    )

    result = {
        "meta": {
            "strategy": "US long-only, equal-weight open positions, daily, net of cost",
            "date_range": [str(cal[0].date()), str(cal[-1].date())],
            "trades": int(len(tdf)),
            "avg_open_positions": round(avg_positions, 1),
            "note": "Simplified portfolio sim (no leverage, no position cap). The "
                    "forward Alpaca paper ledger is the real-money-faithful test. "
                    "Not financial advice.",
        },
        "strategy": _curve_stats(strat_equity, "US longs (quant)"),
        "benchmark": _curve_stats(spy_equity, "SPY buy & hold"),
    }
    RESULTS_PATH.write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    r = run()
    m = r["meta"]
    print(f"\nPortfolio sim — {m['strategy']}")
    print(f"{m['date_range'][0]}→{m['date_range'][1]} · {m['trades']} trades · avg {m['avg_open_positions']} open positions\n")
    print(f"{'':22} {'total':>9} {'CAGR':>8} {'vol':>7} {'Sharpe':>7} {'maxDD':>8}")
    for k in ["strategy", "benchmark"]:
        s = r[k]
        print(f"{s['label']:22} {str(s['total_return_pct'])+'%':>9} {str(s['cagr_pct'])+'%':>8} "
              f"{str(s['vol_pct'])+'%':>7} {str(s['sharpe']):>7} {str(s['max_drawdown_pct'])+'%':>8}")
    print(f"\nSaved → {RESULTS_PATH}")
