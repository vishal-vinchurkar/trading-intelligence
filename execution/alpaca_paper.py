"""Optional real-broker layer — place the trades on Alpaca PAPER.

The ledger (execution/ledger.py) is the source of truth and needs no broker. This
adds realistic paper FILLS: it places a bracket order (entry + stop-loss + take-
profit) on Alpaca's paper account for each tradeable US-long signal, sized to a
fixed fraction of equity. Use it to feel real slippage/partial fills before any
live capital.

Safe by default:
  • Requires ALPACA_API_KEY / ALPACA_SECRET_KEY in .env (paper keys).
  • Dry-run unless you pass --live (even paper orders touch your account).
  • US equities only (Alpaca doesn't trade NSE) — which is also the only market
    the backtest found tradeable, so the scope lines up.

NOTE: untested in this build because no Alpaca keys are set. The REST calls
follow Alpaca's documented v2 API; verify against a fresh paper account.

Run:
  PYTHONPATH=. python -m execution.alpaca_paper            # dry-run: show intended orders
  PYTHONPATH=. python -m execution.alpaca_paper --live     # actually place paper orders
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

SCAN_PATH = Path(__file__).parent.parent / "quant" / "latest_scan.json"
RISK_FRACTION = 0.02   # risk ~2% of equity per trade (distance entry→stop)


def _cfg():
    base = (os.environ.get("ALPACA_BASE_URL") or "https://paper-api.alpaca.markets").rstrip("/")
    return os.environ.get("ALPACA_API_KEY"), os.environ.get("ALPACA_SECRET_KEY"), base


def _req(path: str, method: str = "GET", body: dict | None = None):
    key, sec, base = _cfg()
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(base + path, data=data, method=method, headers={
        "APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec, "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def _account():
    return _req("/v2/account")


def place(live: bool = False) -> None:
    key, sec, base = _cfg()
    if not (key and sec):
        print("ALPACA_API_KEY / ALPACA_SECRET_KEY not set in .env — cannot place paper orders.")
        print("Add paper keys from https://app.alpaca.markets (Paper Trading) and re-run.")
        return

    acct = _account()
    equity = float(acct["equity"])
    print(f"Alpaca paper account: equity ${equity:,.0f}, status {acct.get('status')}")

    scan = json.loads(SCAN_PATH.read_text())
    # Only US longs that cleared the backtest AND whose entry is worth it today.
    picks = [s for s in scan["signals"]
             if s["market"] == "US" and s["calibration"].get("tradeable")
             and s.get("trade") and s["trade"]["actionable"]]
    if not picks:
        print("No actionable US-long setups today (R:R≥1.5). Nothing to place — that's discipline, not a bug.")
        return

    for s in picks:
        t = s["trade"]
        risk_per_share = t["entry"] - t["stop"]
        if risk_per_share <= 0:
            continue
        qty = max(1, int((equity * RISK_FRACTION) / risk_per_share))
        order = {
            "symbol": s["symbol"], "qty": qty, "side": "buy", "type": "market",
            "time_in_force": "gtc", "order_class": "bracket",
            "take_profit": {"limit_price": round(t["target"], 2)},
            "stop_loss": {"stop_price": round(t["stop"], 2)},
        }
        print(f"  {'PLACE' if live else 'DRY-RUN'} {s['symbol']}: {qty} sh @mkt, "
              f"target {t['target']}, stop {t['stop']} (risk ${risk_per_share*qty:,.0f})")
        if live:
            try:
                resp = _req("/v2/orders", "POST", order)
                print(f"    → order {resp.get('id')} status {resp.get('status')}")
            except Exception as e:  # noqa: BLE001
                print(f"    → FAILED: {e}")


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    place(live="--live" in sys.argv)
