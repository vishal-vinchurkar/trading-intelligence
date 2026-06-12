"""Telegram push — today's tradeable signals to your phone.

The signal product is push-native: you shouldn't have to remember to open a
dashboard. This formats the tradeable US-long setups (the only validated edge),
plus any earnings-risk flags, and sends them to a Telegram chat. Carries the
backtested win-rate + the survivorship caveat so the message never oversells.

One-time setup (yours):
  1. Message @BotFather on Telegram → /newbot → copy the token.
  2. Message your new bot once, then visit
     https://api.telegram.org/bot<TOKEN>/getUpdates to find your chat id.
  3. Put both in .env:
       TELEGRAM_BOT_TOKEN=...
       TELEGRAM_CHAT_ID=...

Run:
  PYTHONPATH=. python -m execution.telegram_push            # dry-run: print the message
  PYTHONPATH=. python -m execution.telegram_push --send     # actually send
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

SCAN_PATH = Path(__file__).parent.parent / "quant" / "latest_scan.json"


def build_message() -> str:
    scan = json.loads(SCAN_PATH.read_text())
    ev = scan.get("evidence", {}).get("us_long_oos", {})
    tradeable = [s for s in scan["signals"] if s["calibration"].get("tradeable")]
    tradeable.sort(key=lambda s: s["score"], reverse=True)

    lines = [f"📊 Sovian — {scan['as_of']}", ""]
    if tradeable:
        lines.append(f"Tradeable (US longs · backtested {ev.get('win_rate','?')}% win, PF {ev.get('profit_factor','?')}):")
        for s in tradeable[:8]:
            t = s.get("trade") or {}
            tag = "✅" if t.get("actionable") else "⏳"  # actionable now vs wait-for-entry
            warn = " ⚠earnings" if (s.get("events") or {}).get("event_within_horizon") else ""
            rr = t.get("risk_reward")
            lines.append(
                f"{tag} {s['symbol']} {s['label'].replace('_',' ')} ({s['score']:.0f}) "
                f"@ ${s['last_close']} → tgt ${t.get('target','?')} / stop ${t.get('stop','?')} (R:R {rr}){warn}"
            )
    else:
        lines.append("No tradeable US-long setups today.")
    lines += ["", "Upper-bound backtest (survivorship-biased). Not financial advice."]
    return "\n".join(lines)


def send(text: str) -> None:
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat):
        print("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set in .env — printing instead of sending.\n")
        print(text)
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
    try:
        resp = json.load(urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=20))
        print("sent" if resp.get("ok") else f"telegram error: {resp}")
    except Exception as e:  # noqa: BLE001
        print(f"send failed: {e}")


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    msg = build_message()
    if "--send" in sys.argv:
        send(msg)
    else:
        print(msg)
