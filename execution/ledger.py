"""Forward paper-trading ledger — the unbiased, real-time track record.

The backtest is survivorship-biased (it runs on today's winners). The only way
to know if the edge is real is to log what the engine says NOW and grade it as
the future arrives. This is that ledger:

  record    — append today's TRADEABLE signals (US longs that cleared the
              backtest) with their entry/stop/target. Dedupes by (symbol, date).
  reconcile — for every still-open trade, pull fresh prices and resolve it with
              the SAME rules the backtest used (entry next open, 2xATR stop,
              target, 20-day time-stop), net of cost.
  summary   — realised win-rate / expectancy of CLOSED trades vs the backtest's
              promise. This is the number that earns (or destroys) trust.

No broker required — it reconciles against free yfinance prices. A real Alpaca
paper layer (execution/alpaca_paper.py) can place actual bracket orders once keys
are set; this ledger is the source of truth either way.

Run:
  PYTHONPATH=. python -m execution.ledger record
  PYTHONPATH=. python -m execution.ledger reconcile
  PYTHONPATH=. python -m execution.ledger summary
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from quant.backtest import COST_BPS, DEFAULT_COST_BPS
from quant.backtest_rules import MAX_HOLD

LEDGER_PATH = Path(__file__).parent / "ledger.json"
SCAN_PATH = Path(__file__).parent.parent / "quant" / "latest_scan.json"


def _load() -> list[dict]:
    return json.loads(LEDGER_PATH.read_text()) if LEDGER_PATH.exists() else []


def _save(rows: list[dict]) -> None:
    LEDGER_PATH.write_text(json.dumps(rows, indent=2))


def record() -> None:
    """Append today's tradeable signals (deduped by symbol+signal date)."""
    scan = json.loads(SCAN_PATH.read_text())
    ledger = _load()
    seen = {(r["symbol"], r["signal_date"]) for r in ledger}
    added = 0
    for s in scan["signals"]:
        if not s["calibration"].get("tradeable") or not s.get("trade"):
            continue
        key = (s["symbol"], s["as_of"])
        if key in seen:
            continue
        t = s["trade"]
        ledger.append({
            "symbol": s["symbol"], "market": s["market"], "signal_date": s["as_of"],
            "direction": t["direction"], "ref_price": s["last_close"],
            "stop": t["stop"], "target": t["target"], "score": s["score"],
            "status": "open", "entry_price": None, "entry_date": None,
            "exit_price": None, "exit_date": None, "exit_reason": None, "net_return_pct": None,
        })
        added += 1
    _save(ledger)
    print(f"Recorded {added} new tradeable signal(s); ledger now has {len(ledger)} entries.")


def _bars_after(symbol: str, signal_date: str) -> pd.DataFrame:
    """Fresh daily bars on/after the signal date (yfinance, free)."""
    import yfinance as yf

    try:
        df = yf.Ticker(symbol).history(period="1y", interval="1d", auto_adjust=False)
    except Exception:
        return pd.DataFrame()  # transient fetch failure — leave the trade open
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close"})
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df[df.index > pd.to_datetime(signal_date)]


def reconcile() -> None:
    """Resolve open trades against fresh prices with the backtest's exact rules."""
    ledger = _load()
    resolved = 0
    for r in ledger:
        if r["status"] != "open":
            continue
        bars = _bars_after(r["symbol"], r["signal_date"])
        if len(bars) < 2:
            continue  # not enough forward data yet — still open
        entry = float(bars["open"].iloc[0])           # next session's open
        r["entry_price"], r["entry_date"] = round(entry, 2), str(bars.index[0].date())
        stop, target, direction = r["stop"], r["target"], r["direction"]
        cost = COST_BPS.get(r["market"], DEFAULT_COST_BPS) / 1e4

        exit_px = exit_reason = exit_date = None
        window = bars.iloc[1 : 1 + MAX_HOLD]
        for idx, bar in window.iterrows():
            hi, lo = float(bar["high"]), float(bar["low"])
            if direction == "long":
                if lo <= stop:
                    exit_px, exit_reason, exit_date = stop, "stop", idx; break
                if hi >= target:
                    exit_px, exit_reason, exit_date = target, "target", idx; break
            else:
                if hi >= stop:
                    exit_px, exit_reason, exit_date = stop, "stop", idx; break
                if lo <= target:
                    exit_px, exit_reason, exit_date = target, "target", idx; break

        if exit_px is None:
            if len(window) >= MAX_HOLD:               # time-stop reached
                last = window.iloc[-1]
                exit_px, exit_reason, exit_date = float(last["close"]), "time", window.index[-1]
            else:
                continue  # trade still running

        gross = (exit_px / entry - 1) if direction == "long" else (entry / exit_px - 1)
        r.update({
            "status": "closed", "exit_price": round(float(exit_px), 2),
            "exit_date": str(pd.to_datetime(exit_date).date()), "exit_reason": exit_reason,
            "net_return_pct": round((gross - cost) * 100, 2),
        })
        resolved += 1
    _save(ledger)
    print(f"Reconciled: {resolved} trade(s) closed this run.")
    summary()


def summary() -> None:
    ledger = _load()
    closed = [r for r in ledger if r["status"] == "closed"]
    open_ = [r for r in ledger if r["status"] == "open"]
    print(f"\nLedger: {len(ledger)} total · {len(open_)} open · {len(closed)} closed")
    if closed:
        rets = [r["net_return_pct"] for r in closed]
        wins = [x for x in rets if x > 0]
        win_rate = round(len(wins) / len(rets) * 100, 1)
        exp = round(sum(rets) / len(rets), 2)
        print(f"Realised (forward, unbiased): win {win_rate}% · expectancy {exp}%/trade · n={len(closed)}")
        print("Backtest promised (US long OOS): win 57.3% · expectancy 0.97%/trade")
    else:
        print("No closed trades yet — forward track record accrues as time passes.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "summary"
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    {"record": record, "reconcile": reconcile, "summary": summary}.get(cmd, summary)()
