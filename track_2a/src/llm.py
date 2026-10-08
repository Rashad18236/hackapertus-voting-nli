"""The only module that talks to Apertus.

The endpoint speaks the OpenAI chat-completions protocol
(POST {LLM_BASE_URL}/chat/completions). Connection details come only from the
environment variables LLM_NAME, LLM_BASE_URL and LLM_API_KEY; their values are
never printed or logged, not even in error messages.

Every call returns the token counts reported by the server and the elapsed
wall-clock time, because the organisers score input tokens and speed.

There are no automatic retries: the organisers count every token, retries
included, so a failed call raises an error instead of being repeated silently.
"""

import logging
import os
import time
from dataclasses import dataclass

import requests

# Public AI rejects requests without a User-Agent header.
USER_AGENT = "hackapertus-voting-nli/0.1"
TIMEOUT_SECONDS = 120


class LLMError(RuntimeError):
    """A model call failed. The message never contains the URL or the key."""


@dataclass
class LLMResult:
    text: str
    input_tokens: int
    output_tokens: int
    elapsed_ms: int


def _settings():
    missing = [n for n in ("LLM_NAME", "LLM_BASE_URL", "LLM_API_KEY") if not os.environ.get(n)]
    if missing:
        raise LLMError(f"Missing environment variables: {', '.join(missing)}")
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
    headers = {"Authorization": f"Bearer {key}", "User-Agent": USER_AGENT}

    start = time.perf_counter()
    try:
        response = requests.post(
            f"{base}/chat/completions", json=payload, headers=headers, timeout=TIMEOUT_SECONDS
        )
    except requests.Timeout:
        raise LLMError(f"LLM call timed out after {TIMEOUT_SECONDS} s") from None
    except requests.ConnectionError as e:
        # `from None` drops the original exception, whose text includes the URL.
        raise LLMError(f"Could not connect to the LLM endpoint ({type(e).__name__})") from None
    elapsed_ms = round((time.perf_counter() - start) * 1000)

    if response.status_code != 200:
        raise LLMError(f"LLM call failed with HTTP {response.status_code}: {response.text[:300]}")

    data = response.json()
    usage = data.get("usage") or {}
    if "prompt_tokens" not in usage:
        logging.warning("Endpoint returned no token usage; recording 0 tokens")
    return LLMResult(
        text=data["choices"][0]["message"]["content"] or "",
        input_tokens=usage.get("prompt_tokens", 0),
        output_tokens=usage.get("completion_tokens", 0),
        elapsed_ms=elapsed_ms,
    )
