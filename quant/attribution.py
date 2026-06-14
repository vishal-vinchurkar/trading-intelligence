"""Factor attribution — is the edge real alpha, or repackaged momentum smart-beta?

The single most damaging critique a sophisticated subscriber (or an independent
reviewer) levels at a trend/momentum screener: "factor-neutralise it vs MTUM —
if the alpha collapses once you control for the momentum ETF, you're just selling
smart-beta anyone can buy for 15bps." This module answers that head-on.

It takes the EXACT daily return series the portfolio equity curve is built from
(quant.portfolio.strategy_daily_returns — the US-long book, net of cost) and
regresses it on two factors:

  • MKT  = SPY daily return                  (the market)
  • MOM  = MTUM daily return − SPY return     (the momentum tilt, market-stripped)

Two nested models, OLS with **Newey-West** standard errors (daily strategy
returns are autocorrelated — overlapping positions — so plain OLS t-stats would
overstate significance):

  Model A (CAPM):            r = α + β_mkt·MKT
  Model B (CAPM + momentum): r = α + β_mkt·MKT + β_mom·MOM

The verdict hinges on Model B's α: if it stays positive and significant after
adding MOM, there is selection edge beyond what a momentum ETF gives you. If it
goes insignificant, the honest answer to the reviewer is "yes — on this evidence
it's smart-beta," and we say so.

Run:
  PYTHONPATH=. python -m quant.attribution
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from data.backfill import load_cached
from quant.portfolio import strategy_daily_returns

RESULTS_PATH = Path(__file__).parent / "attribution_results.json"
TRADING_DAYS = 252


def _newey_west_ols(y: np.ndarray, X: np.ndarray, lags: int | None = None) -> dict:
    """OLS with Newey-West (HAC) standard errors. X includes the intercept column.

    Returns coefficients, HAC standard errors, t-stats (large-sample normal), and
    R². Newey-West corrects for the heteroskedasticity + autocorrelation that
    overlapping daily strategy returns inevitably carry.
    """
    n, k = X.shape
    # macOS's Accelerate BLAS emits spurious divide/overflow warnings from matmul
    # even on finite inputs (inputs are asserted finite by the caller).
    with np.errstate(all="ignore"):
        XtX_inv = np.linalg.inv(X.T @ X)
        beta = XtX_inv @ (X.T @ y)
        resid = y - X @ beta

        if lags is None:
            lags = int(np.floor(4 * (n / 100.0) ** (2.0 / 9.0)))  # standard NW rule

        # Sandwich: meat = S0 + sum_l w_l (S_l + S_l'), w_l = 1 - l/(lags+1)
        S = (X * resid[:, None]).T @ (X * resid[:, None])  # S0
        for l in range(1, lags + 1):
            w = 1.0 - l / (lags + 1.0)
            g = (X[l:] * resid[l:, None]).T @ (X[:-l] * resid[:-l, None])
            S += w * (g + g.T)
        cov = XtX_inv @ S @ XtX_inv
        se = np.sqrt(np.diag(cov))
        t = beta / se

        ss_res = float(resid @ resid)
        ss_tot = float(((y - y.mean()) ** 2).sum())
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return {"beta": beta, "se": se, "t": t, "r2": r2, "n": n, "lags": lags}


def _daily_ret(symbol: str) -> pd.Series:
    df = load_cached(symbol)
    return df["close"].pct_change() if df is not None else pd.Series(dtype=float)


SIG = 1.96  # |t| for 5% two-sided (large-sample normal; n is in the thousands)


def _fmt_coef(name: str, b: float, t: float, annualize: bool = False) -> str:
    val = b * TRADING_DAYS if annualize else b
    unit = "%/yr" if annualize else ""
    star = "***" if abs(t) >= 2.58 else "**" if abs(t) >= SIG else "*" if abs(t) >= 1.64 else ""
    show = f"{val * 100:+.2f}{unit}" if annualize else f"{b:+.4f}"
    return f"  {name:18} {show:>12}   t={t:+.2f} {star}"


def run() -> dict:
    strat, _tdf, _spy = strategy_daily_returns()
    # Active days only: the book is flat (exactly 0.0) when no position is open;
    # cash days carry no factor exposure and would bias α/β toward zero. The
    # honest factor question is "WHEN INVESTED, is it just momentum?"
    active = strat[strat != 0.0]

    spy_r = _daily_ret("SPY")
    mtum_r = _daily_ret("MTUM")

    df = pd.concat(
        {"strat": active, "spy": spy_r, "mtum": mtum_r}, axis=1
    ).dropna()
    if len(df) < 100:
        raise RuntimeError(f"Too few overlapping days ({len(df)}) — is MTUM cached?")

    y = df["strat"].to_numpy()
    mkt = df["spy"].to_numpy()
    mom = (df["mtum"] - df["spy"]).to_numpy()  # market-stripped momentum tilt
    if not (np.isfinite(y).all() and np.isfinite(mkt).all() and np.isfinite(mom).all()):
        raise RuntimeError("Non-finite returns in regression inputs — check the price cache.")
    ones = np.ones(len(df))

    capm = _newey_west_ols(y, np.column_stack([ones, mkt]))
    full = _newey_west_ols(y, np.column_stack([ones, mkt, mom]))

    corr_mtum = float(np.corrcoef(y, df["mtum"].to_numpy())[0, 1])
    corr_spy = float(np.corrcoef(y, mkt)[0, 1])

    alpha_ann = float(full["beta"][0] * TRADING_DAYS)
    alpha_t = float(full["t"][0])
    survives = alpha_t >= SIG and alpha_ann > 0

    result = {
        "meta": {
            "what": "Factor attribution of the US-long book vs SPY (market) + MTUM (momentum).",
            "date_range": [str(df.index[0].date()), str(df.index[-1].date())],
            "active_days": int(len(df)),
            "se": f"Newey-West HAC, {full['lags']} lags",
            "factors": {"MKT": "SPY daily return", "MOM": "MTUM return − SPY return"},
            "note": "Active (invested) days only. Significance: * |t|≥1.64, ** ≥1.96, *** ≥2.58. "
                    "Not financial advice.",
        },
        "correlations": {"strat_vs_MTUM": round(corr_mtum, 3), "strat_vs_SPY": round(corr_spy, 3)},
        "capm": {
            "alpha_daily": float(capm["beta"][0]), "alpha_annual_pct": round(capm["beta"][0] * TRADING_DAYS * 100, 2),
            "alpha_t": round(float(capm["t"][0]), 2),
            "beta_mkt": round(float(capm["beta"][1]), 3), "beta_mkt_t": round(float(capm["t"][1]), 2),
            "r2": round(capm["r2"], 3),
        },
        "capm_plus_momentum": {
            "alpha_daily": float(full["beta"][0]), "alpha_annual_pct": round(alpha_ann * 100, 2),
            "alpha_t": round(alpha_t, 2),
            "beta_mkt": round(float(full["beta"][1]), 3), "beta_mkt_t": round(float(full["t"][1]), 2),
            "beta_mom": round(float(full["beta"][2]), 3), "beta_mom_t": round(float(full["t"][2]), 2),
            "r2": round(full["r2"], 3),
        },
        "verdict": {
            "alpha_survives_momentum_neutralization": bool(survives),
            "alpha_annual_pct_net_of_momentum": round(alpha_ann * 100, 2),
            "plain_english": (
                f"After controlling for the momentum ETF, the book retains "
                f"{alpha_ann * 100:+.1f}%/yr of alpha at t={alpha_t:+.1f} — "
                + ("statistically significant: there is selection edge beyond smart-beta."
                   if survives else
                   "NOT statistically distinguishable from momentum/market exposure. "
                   "On this evidence the edge is smart-beta you could approximate with MTUM.")
            ),
        },
    }
    RESULTS_PATH.write_text(json.dumps(result, indent=2))
    return result


def _print(r: dict) -> None:
    m = r["meta"]
    print(f"\nFactor attribution — US-long book")
    print(f"{m['date_range'][0]}→{m['date_range'][1]} · {m['active_days']} active days · {m['se']}\n")
    c = r["correlations"]
    print(f"Correlation:  vs MTUM {c['strat_vs_MTUM']:+.2f}   vs SPY {c['strat_vs_SPY']:+.2f}\n")

    a = r["capm"]
    print("Model A — CAPM (market only):")
    print(_fmt_coef("alpha", a["alpha_daily"], a["alpha_t"], annualize=True))
    print(_fmt_coef("beta_mkt (SPY)", a["beta_mkt"], a["beta_mkt_t"]))
    print(f"  R² {a['r2']}\n")

    b = r["capm_plus_momentum"]
    print("Model B — CAPM + momentum (the neutralization test):")
    print(_fmt_coef("alpha", b["alpha_daily"], b["alpha_t"], annualize=True))
    print(_fmt_coef("beta_mkt (SPY)", b["beta_mkt"], b["beta_mkt_t"]))
    print(_fmt_coef("beta_mom (MTUM)", b["beta_mom"], b["beta_mom_t"]))
    print(f"  R² {b['r2']}\n")

    v = r["verdict"]
    flag = "✓ ALPHA SURVIVES" if v["alpha_survives_momentum_neutralization"] else "✗ NO ALPHA BEYOND MOMENTUM"
    print(f"VERDICT: {flag}")
    print(f"  {v['plain_english']}")


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    _print(run())
    print(f"\nSaved → {RESULTS_PATH}")
