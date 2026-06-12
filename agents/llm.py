"""LLM backends for the agents — all free, no Anthropic key required.

Two providers, both reachable behind one `json_complete()` call:

- groq   : Groq Cloud free tier (OpenAI-compatible). Agents 1 & 2 use a fast
           Llama 4 model; the Arbitrator uses a larger reasoning-grade model.
- ollama : Local models on the MacBook (M5) via the Ollama HTTP API. Zero
           network cost; the fallback when Groq is rate-limited or offline.

Every call requests JSON-object output and validates that the body parses.
One retry on malformed output, per the project's JSON-schema-enforcement rule.
"""

from __future__ import annotations

import json
import os

import requests

GROQ_BASE = "https://api.groq.com/openai/v1/chat/completions"
OLLAMA_BASE = os.environ.get("OLLAMA_HOST", "http://localhost:11434")


class LLMError(RuntimeError):
    pass


def _parse_json_or_raise(text: str) -> dict:
    text = text.strip()
    # Tolerate accidental ```json fences.
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.lstrip().startswith("json"):
            text = text.lstrip()[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise LLMError(f"Model did not return valid JSON: {e}") from e


def _groq(system: str, user: str, model: str, temperature: float) -> dict:
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise LLMError("GROQ_API_KEY not set. Add it to your .env (see .env.example).")
    resp = requests.post(
        GROQ_BASE,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        },
        timeout=60,
    )
    if resp.status_code != 200:
        raise LLMError(f"Groq error {resp.status_code}: {resp.text[:300]}")
    content = resp.json()["choices"][0]["message"]["content"]
    return _parse_json_or_raise(content)


def _ollama(system: str, user: str, model: str, temperature: float) -> dict:
    resp = requests.post(
        f"{OLLAMA_BASE}/api/chat",
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "format": "json",
            "stream": False,
            "options": {"temperature": temperature},
        },
        timeout=180,
    )
    if resp.status_code != 200:
        raise LLMError(f"Ollama error {resp.status_code}: {resp.text[:300]}")
    return _parse_json_or_raise(resp.json()["message"]["content"])


def json_complete(
    system: str,
    user: str,
    *,
    provider: str,
    model: str,
    temperature: float = 0.3,
    retries: int = 1,
) -> dict:
    """Run a chat completion that must return a JSON object. Retries once on
    malformed output before giving up."""
    backend = {"groq": _groq, "ollama": _ollama}.get(provider)
    if backend is None:
        raise LLMError(f"Unknown LLM provider {provider!r}. Use 'groq' or 'ollama'.")

    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return backend(system, user, model, temperature)
        except LLMError as e:
            last_err = e
            if "valid JSON" not in str(e):
                raise  # auth / rate-limit errors shouldn't be retried blindly
    raise LLMError(f"Failed to get valid JSON after {retries + 1} attempts: {last_err}")
