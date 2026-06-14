"""Two-way Telegram bridge — async control channel between you and the agent.

The push module (telegram_push.py) is one-way: signals → your phone. This adds the
return path so the agent can ask a question, you answer from your phone, and the
agent reads the reply on its next wake-up and acts — no keyboard required.

  • send "<text>"   — push a message (used for status updates / questions).
  • poll            — fetch messages YOU sent the bot since the last poll, as JSON
                      on stdout. Advances a stored offset so each call only returns
                      what's new (no re-reading old replies).
  • reset-offset    — drop the stored offset (next poll returns recent backlog).

Offset state lives in execution/telegram_bridge_state.json (gitignored). Only
messages from TELEGRAM_CHAT_ID are returned — the bot ignores anyone else.

Run:
  PYTHONPATH=. python -m execution.telegram_bridge send "your question here"
  PYTHONPATH=. python -m execution.telegram_bridge poll
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

STATE_PATH = Path(__file__).parent / "telegram_bridge_state.json"
API = "https://api.telegram.org/bot{token}/{method}"


def _creds() -> tuple[str, str]:
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat):
        raise RuntimeError("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set in .env")
    return token, chat


def _call(method: str, params: dict, timeout: int = 40) -> dict:
    token, _ = _creds()
    url = API.format(token=token, method=method)
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data)
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def _load_offset() -> int | None:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text()).get("offset")
    return None


def _save_offset(offset: int) -> None:
    STATE_PATH.write_text(json.dumps({"offset": offset}))


def send(text: str) -> bool:
    _, chat = _creds()
    resp = _call("sendMessage", {"chat_id": chat, "text": text}, timeout=20)
    ok = bool(resp.get("ok"))
    print("sent" if ok else f"telegram error: {resp}")
    return ok


def poll() -> list[dict]:
    """Return new messages from the configured chat since the last poll."""
    _, chat = _creds()
    params: dict = {"timeout": 0, "allowed_updates": json.dumps(["message"])}
    offset = _load_offset()
    if offset is not None:
        params["offset"] = offset
    resp = _call("getUpdates", params)
    if not resp.get("ok"):
        print(json.dumps({"error": resp}))
        return []

    msgs, max_update_id = [], offset - 1 if offset else None
    for upd in resp.get("result", []):
        uid = upd["update_id"]
        max_update_id = uid if max_update_id is None else max(max_update_id, uid)
        m = upd.get("message") or {}
        if str(m.get("chat", {}).get("id")) != str(chat):
            continue  # ignore anyone who isn't you
        text = m.get("text")
        if text is None:
            continue
        msgs.append({"date": m.get("date"), "text": text})
    if max_update_id is not None:
        _save_offset(max_update_id + 1)  # ack: next poll starts after the last seen
    print(json.dumps(msgs, indent=2))
    return msgs


def main() -> int:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    cmd = args[0]
    if cmd == "send":
        if len(args) < 2:
            print("usage: send \"<text>\"")
            return 1
        return 0 if send(" ".join(args[1:])) else 1
    if cmd == "poll":
        poll()
        return 0
    if cmd == "reset-offset":
        STATE_PATH.unlink(missing_ok=True)
        print("offset reset")
        return 0
    print(f"unknown command: {cmd}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
