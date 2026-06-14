"""Options wheel-strategy backtest — the income strategy, modelled honestly on free data.

The "wheel" sells cash-secured puts until assigned, then sells covered calls until
called away, collecting premium at every step. It's the retail income strategy the
video pitches. Problem: a faithful backtest needs historical option chains, which
are NOT free. So this prices each option with **Black-Scholes at trailing realised
volatility** on the free daily underlying history — a transparent approximation,
not a tradeable P&L.

What this DOES capture (honestly):
  • The wheel state machine on the real price path (assignment is decided by where
    the underlying actually closed at each monthly expiry).
  • Premium income, assignment/called-away mechanics, cost-basis reduction.
  • Return on the capital the strategy actually ties up (cash-secured puts reserve
    strike×100), vs buy-and-hold the same names.

What it does NOT capture (stated, not hidden):
  • Implied-vol skew and the vol-risk-premium — real sellers usually collect MORE
    than realised-vol BSM implies, so this is conservative on income.
  • Bid/ask, early assignment, dividends, pin risk. A small premium haircut stands
    in for transaction friction.
This is a hypothesis-grade model to decide whether the wheel is worth wiring to a
live paper account (Alpaca) — where the real option prices live.

Run:
  PYTHONPATH=. python -m quant.wheel
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from data import universe
from data.backfill import load_cached

RESULTS_PATH = Path(__file__).parent / "wheel_results.json"

HORIZON = 21          # trading days per cycle (~1 month to expiry)
PUT_OTM = 0.05        # sell the cash-secured put 5% below spot
CALL_OTM = 0.05       # sell the covered call 5% above the working cost basis
RISK_FREE = 0.04      # flat short-rate for BSM discounting
PREMIUM_HAIRCUT = 0.02  # friction: keep 98% of modelled premium
VOL_FLOOR, VOL_CAP = 0.12, 1.20  # clamp realised-vol estimates to sane bounds


def _phi(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _bsm(S: float, K: float, T: float, sig: float, r: float, kind: str) -> float:
    if T <= 0 or sig <= 0 or S <= 0 or K <= 0:
        return max(0.0, (S - K) if kind == "call" else (K - S))
    d1 = (math.log(S / K) + (r + 0.5 * sig * sig) * T) / (sig * math.sqrt(T))
    d2 = d1 - sig * math.sqrt(T)
    if kind == "call":
        return S * _phi(d1) - K * math.exp(-r * T) * _phi(d2)
    return K * math.exp(-r * T) * _phi(-d2) - S * _phi(-d1)


def _wheel_symbol(sym: str) -> dict | None:
    df = load_cached(sym)
    if df is None or len(df) < 260:
        return None
    close = df["close"].to_numpy()
    logret = np.diff(np.log(close))
    T = HORIZON / 252.0

    idxs = list(range(60, len(close) - HORIZON, HORIZON))  # monthly decision points
    if len(idxs) < 12:
        return None

    cash_pnl = 0.0           # cumulative realised $ per 1 contract (100 sh) of exposure
    reserved_sum, reserved_n = 0.0, 0
    state = "cash"           # "cash" (short put) | "shares" (long 100 + short call)
    cost_basis = None        # working basis per share once assigned
    puts_sold = puts_kept = calls_sold = called_away = assigned = 0

    for i in idxs:
        S = float(close[i])
        S_exp = float(close[i + HORIZON])
        # realised vol over the trailing month, annualised, clamped
        window = logret[max(0, i - HORIZON):i]
        sig = float(np.std(window) * math.sqrt(252)) if len(window) > 5 else VOL_FLOOR
        sig = min(max(sig, VOL_FLOOR), VOL_CAP)

        if state == "cash":
            K = S * (1 - PUT_OTM)
            prem = _bsm(S, K, T, sig, RISK_FREE, "put") * (1 - PREMIUM_HAIRCUT)
            cash_pnl += prem * 100
            puts_sold += 1
            reserved_sum += K * 100; reserved_n += 1  # cash-secured capital tied up
            if S_exp < K:                              # assigned → own 100 @ K
                assigned += 1
                cost_basis = K - prem                  # basis reduced by premium kept
                state = "shares"
            else:
                puts_kept += 1
        else:  # state == "shares": hold 100, sell a covered call
            K = max(cost_basis, S) * (1 + CALL_OTM)
            prem = _bsm(S, K, T, sig, RISK_FREE, "call") * (1 - PREMIUM_HAIRCUT)
            cash_pnl += prem * 100
            calls_sold += 1
            cost_basis -= prem                          # basis keeps dropping
            reserved_sum += S * 100; reserved_n += 1    # shares tie up ~spot×100
            if S_exp > K:                               # called away → realise gain
                called_away += 1
                cash_pnl += (K - cost_basis) * 100
                cost_basis = None
                state = "cash"

    # If still holding shares at the end, mark to last close.
    if state == "shares" and cost_basis is not None:
        cash_pnl += (float(close[-1]) - cost_basis) * 100

    avg_reserved = reserved_sum / max(reserved_n, 1)
    years = (df.index[idxs[-1] + HORIZON] - df.index[idxs[0]]).days / 365.25
    roc = cash_pnl / avg_reserved if avg_reserved else 0.0          # return on tied-up capital
    ann_roc = (1 + roc) ** (1 / max(years, 1e-9)) - 1 if roc > -1 else -1.0
    bh_cagr = (float(close[idxs[-1] + HORIZON]) / float(close[idxs[0]])) ** (1 / max(years, 1e-9)) - 1

    return {
        "symbol": sym,
        "cycles": len(idxs),
        "puts_sold": puts_sold,
        "put_keep_rate": round(puts_kept / puts_sold, 3) if puts_sold else None,
        "assignment_rate": round(assigned / puts_sold, 3) if puts_sold else None,
        "calls_sold": calls_sold,
        "called_away": called_away,
        "premium_pnl_per_contract": round(cash_pnl, 0),
        "avg_capital_reserved": round(avg_reserved, 0),
        "ann_return_on_capital_pct": round(ann_roc * 100, 1),
        "buyhold_cagr_pct": round(bh_cagr * 100, 1),
        "years": round(years, 1),
    }


def run() -> dict:
    rows = [r for s in universe.symbols("US") if (r := _wheel_symbol(s))]
    df = pd.DataFrame(rows)
    agg = {
        "names": int(len(df)),
        "median_ann_roc_pct": round(float(df["ann_return_on_capital_pct"].median()), 1),
        "median_buyhold_cagr_pct": round(float(df["buyhold_cagr_pct"].median()), 1),
        "median_put_keep_rate": round(float(df["put_keep_rate"].median()), 3),
        "median_assignment_rate": round(float(df["assignment_rate"].median()), 3),
        "share_beating_buyhold": round(float((df["ann_return_on_capital_pct"] > df["buyhold_cagr_pct"]).mean()), 2),
    }
    result = {
        "meta": {
            "what": "Options wheel (cash-secured puts → covered calls), Black-Scholes at realised vol.",
            "params": {"horizon_days": HORIZON, "put_otm": PUT_OTM, "call_otm": CALL_OTM,
                       "risk_free": RISK_FREE, "premium_haircut": PREMIUM_HAIRCUT},
            "caveat": "MODEL, NOT P&L. BSM at realised vol ignores skew + the vol-risk-premium "
                      "(real sellers usually collect more), bid/ask, early assignment, dividends. "
                      "Use to decide whether to wire the wheel to live Alpaca paper, where real "
                      "option prices live. Not financial advice.",
        },
        "aggregate": agg,
        "by_symbol": rows,
    }
    RESULTS_PATH.write_text(json.dumps(result, indent=2))
    return result


def _print(r: dict) -> None:
    a = r["aggregate"]
    print(f"\nWheel backtest (BSM @ realised vol) — {a['names']} US names\n")
    print(f"{'symbol':8} {'cyc':>4} {'keep%':>6} {'assign%':>8} {'annROC%':>8} {'B&H%':>7}")
    for s in sorted(r["by_symbol"], key=lambda x: x["ann_return_on_capital_pct"], reverse=True):
        print(f"{s['symbol']:8} {s['cycles']:>4} {str(round((s['put_keep_rate'] or 0)*100,1)):>6} "
              f"{str(round((s['assignment_rate'] or 0)*100,1)):>8} {str(s['ann_return_on_capital_pct']):>8} "
              f"{str(s['buyhold_cagr_pct']):>7}")
    print(f"\nMedian annual return on capital: {a['median_ann_roc_pct']}%  "
          f"(vs buy&hold median {a['median_buyhold_cagr_pct']}%)")
    print(f"Median put-keep rate {int(a['median_put_keep_rate']*100)}% · "
          f"assignment {int(a['median_assignment_rate']*100)}% · "
          f"{int(a['share_beating_buyhold']*100)}% of names beat buy&hold")
    print(f"\n⚠ {r['meta']['caveat']}")


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    _print(run())
    print(f"\nSaved → {RESULTS_PATH}")
