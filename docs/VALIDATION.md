# VALIDATION — answering the skeptic, with evidence

This is the credibility ledger for Sovian. An independent AI review (2026-06-14)
called the system "a competent personal research tool, not an investable system"
and listed five specific critiques. This doc tracks each one and what was built to
answer it. The honest posture throughout: **bound and disclose** what free data
can't eliminate; the forward paper ledger is the only unbiased test.

> Posture (owner decision, 2026-06-14): private validation first — prove the
> hypothesis with own capital, then pursue RIA registration before any public
> launch. No public customers yet, so this is a personal validation tool.

## The reviewer's critiques → status

| # | Critique | Status | Evidence |
|---|----------|--------|----------|
| 1 | **Survivorship bias** — backtest on today's winners overstates returns | ⚠️ Bounded, not eliminated (needs paid delisted-history data) | `quant/robustness.py` — drop-top-5 still +0.41%/trade; name-bootstrap 100% of draws positive |
| 2 | **Factors aren't novel; edge well-arbed; is it just smart-beta?** | ✅ Answered | `quant/attribution.py` — **+10.2%/yr alpha SURVIVES (t=4.0)** after neutralising vs SPY + MTUM, Newey-West SEs |
| 3 | **No walk-forward / edge could be one regime** | ✅ Answered | `quant/walkforward.py` — net-positive in **8/10 years (80%)**; only down years 2018 (flat) + 2022 (momentum crash) |
| 4 | **Costs/slippage not visibly modelled** | ✅ Answered | `quant/slippage.py` — survives **~42 bps** slippage before break-even; +0.64%/trade at a realistic 10 bps |
| 5 | **No live track record — all backtest** | 🔄 In progress | `execution/ledger.py` — forward paper ledger live, 17 entries accumulating; the unbiased test, needs calendar time |

## What each test concluded (net of cost, out-of-sample)

- **Momentum-neutralisation (the sharpest critique).** Regressing the US-long
  book's daily returns on the market (SPY) and the momentum ETF (MTUM) with
  Newey-West standard errors: the momentum tilt is real (β≈0.15, t=3.1) but does
  **not** explain the returns away — **+10.2%/yr of alpha remains, t=4.0.** The
  edge is not MTUM you could buy for 15 bps.
- **Walk-forward.** Edge net-positive in 8 of 10 calendar years; the 2022 loss is
  the momentum-style drawdown you'd expect, not a broken model. Strategy has **no
  fitted parameters** (weights/stops fixed a priori), so there's nothing to
  overfit — the risk was regime-dependence, and the year-by-year persistence
  addresses it.
- **Slippage.** On top of per-market commission/spread, the edge survives ~42 bps
  of additional execution shortfall before break-even. A few bps (realistic for
  liquid US large-caps) barely dents it.

## New strategy builds this session

- **Options wheel (`quant/wheel.py`).** Black-Scholes-at-realised-vol model of the
  cash-secured-put → covered-call wheel on the free price history. Finding: an
  **income / lower-volatility** strategy, not alpha — median ~7.8% annual return on
  reserved capital ≈ buy-and-hold, with 81% of puts expiring worthless. Pricing at
  realised vol is conservative (ignores the vol-risk-premium real sellers collect),
  so live income is likely higher. **Needs real option chains + Alpaca paper to
  confirm** — this is a hypothesis-grade model.
- **Congressional alt-data overlay (`data/congress.py`, `quant/congress_signal.py`).**
  Pluggable adapters (Quiver / free House-Clerk PTR PDFs / synthetic demo). Quiver
  went paid, so the working source is the **free, no-key House-Clerk filings** — a
  regex parser over the machine-readable PTR PDFs (partial coverage; scanned/
  handwritten filings are skipped). The backtest is **disclosure-lag-aware by
  construction** — entries are the next open *after* the public filing date, never
  the trade date.
  **Real-data finding (486 trades, 2022-2024, 80 filings/yr): NO edge.** Following
  congressional buys with the real lag returns **−0.54%/trade over 21 days, −0.93%
  alpha vs SPY, beats SPY only 41% of the time.** The naive "copy Congress" thesis
  does not survive the disclosure lag in this sample — confirming the prior
  skepticism and saving the spend on paid congress data. (Caveat: capped sample,
  equal-weight all buys; member-level selection is unexplored but not a priority.)
  Kept as a current-state overlay only — never folded into the backtested price score.

## The honesty rules (unchanged, load-bearing)

1. Anything not backtestable from price alone (fundamentals, macro, congress flow,
   news) is a **current-state overlay**, never part of the backtested score.
2. Survivorship is **bounded, not removed** — returns are an upper bound until a
   point-in-time universe with delisted names is provisioned (paid data).
3. The **forward paper ledger** is the only unbiased test. Everything else is a
   backtest on today's universe.

## What still needs the owner

- **Quiver API key** (free) → unlocks the real congressional backtest (item A).
- **Alpaca paper keys** → live execution + the unbiased forward test (+ real wheel
  option prices).
- **Data budget ~$80-150/mo** (Norgate/Tiingo/Polygon) → kills the survivorship
  caveat (delisted history) and makes data commercially licensable for launch.
