"""The only module that talks to Apertus.

The endpoint is expected to speak the OpenAI chat-completions protocol
(POST {base}/v1/chat/completions). Connection details come only from the
environment variables LLM_NAME, LLM_BASE_URL and LLM_API_KEY; their values are
never printed or logged.

Every call returns the token counts reported by the server and the elapsed
wall-clock time, because the organisers score input tokens and speed.
"""

import os
import time
from dataclasses import dataclass

import requests

# A completed response always costs tokens, so we never retry after one.
# We only retry when the request did not reach the model: a connection error,
# or 503 while a scaled-to-zero Hugging Face endpoint is waking up.
MAX_ATTEMPTS = 4
RETRY_WAIT_SECONDS = 15
TIMEOUT_SECONDS = 300


@dataclass
class LLMResult:
    text: str
    input_tokens: int
    output_tokens: int
    elapsed_ms: int


def _settings():
    missing = [n for n in ("LLM_NAME", "LLM_BASE_URL", "LLM_API_KEY") if not os.environ.get(n)]
    if missing:
        raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")
    base = os.environ["LLM_BASE_URL"].rstrip("/")
    # Accept the base URL with or without a trailing /v1.
    if not base.endswith("/v1"):
        base += "/v1"
    return os.environ["LLM_NAME"], base, os.environ["LLM_API_KEY"]


def chat(messages, max_tokens=256):
    """Send one chat request and return the answer with usage and timing."""
    model, base, key = _settings()
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    headers = {"Authorization": f"Bearer {key}"}

    start = time.perf_counter()
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.post(
                f"{base}/chat/completions", json=payload, headers=headers, timeout=TIMEOUT_SECONDS
            )
        except requests.ConnectionError:
            if attempt == MAX_ATTEMPTS:
                raise
            time.sleep(RETRY_WAIT_SECONDS)
            continue
        if response.status_code == 503 and attempt < MAX_ATTEMPTS:
            time.sleep(RETRY_WAIT_SECONDS)
            continue
        if response.status_code != 200:
            # Body only, never the request: the request carries the key.
            raise RuntimeError(f"LLM call failed with HTTP {response.status_code}: {response.text[:500]}")
        break
    elapsed_ms = round((time.perf_counter() - start) * 1000)

    data = response.json()
    usage = data.get("usage") or {}
    return LLMResult(
        text=data["choices"][0]["message"]["content"] or "",
        input_tokens=usage.get("prompt_tokens", 0),
        output_tokens=usage.get("completion_tokens", 0),
        elapsed_ms=elapsed_ms,
    )
