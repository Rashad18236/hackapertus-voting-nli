"""The only module that talks to Apertus.

The endpoint speaks the OpenAI chat-completions protocol
(POST {base URL}/chat/completions). Configuration, environment first:

- base URL: BASE_URL (official contract), else LLM_BASE_URL (our local .env)
- API key:  API_KEY  (official contract), else LLM_API_KEY
- model:    MODEL, else LLM_NAME, else DEFAULT_MODEL

At evaluation the organisers inject BASE_URL (a token-counting proxy) and
API_KEY. Values are never printed or logged, not even in error messages.

Every call returns the token counts reported by the server and the elapsed
wall-clock time, because the organisers score input tokens and speed.

Retries: exactly one, and only for HTTP 5xx answers and timeouts, where the
request most likely never produced an answer (e.g. Public AI's gateway 504
after about 61 s). The organisers count every token, retries included, so any
usage reported by a failed attempt is added to the result, and the elapsed
time covers both attempts. All other failures raise LLMError at once.
"""

import logging
import os
import time
from dataclasses import dataclass

import requests

# Public AI rejects requests without a User-Agent header.
USER_AGENT = "hackapertus-voting-nli/0.1"
TIMEOUT_SECONDS = 120
MAX_ATTEMPTS = 2          # the first call plus one retry
RETRY_PAUSE_SECONDS = 2


class LLMError(RuntimeError):
    """A model call failed. The message never contains the URL or the key."""


@dataclass
class LLMResult:
    text: str
    input_tokens: int
    output_tokens: int
    elapsed_ms: int
    attempts: int = 1


DEFAULT_MODEL = "swiss-ai/Apertus-v1.5-8B"


def _first_set(*names):
    for name in names:
        if os.environ.get(name):
            return os.environ[name]
    return None


def _settings():
    base = _first_set("BASE_URL", "LLM_BASE_URL")
    key = _first_set("API_KEY", "LLM_API_KEY")
    missing = [n for n, v in (("BASE_URL (or LLM_BASE_URL)", base), ("API_KEY (or LLM_API_KEY)", key)) if not v]
    if missing:
        raise LLMError(f"Missing environment variables: {', '.join(missing)}")
    base = base.rstrip("/")
    # Accept the base URL with or without a trailing /v1.
    if not base.endswith("/v1"):
        base += "/v1"
    return _first_set("MODEL", "LLM_NAME") or DEFAULT_MODEL, base, key


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
    input_tokens = output_tokens = 0  # summed over attempts that report usage
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.post(
                f"{base}/chat/completions", json=payload, headers=headers, timeout=TIMEOUT_SECONDS
            )
        except requests.Timeout:
            if attempt < MAX_ATTEMPTS:
                logging.warning("LLM call timed out; retrying once")
                time.sleep(RETRY_PAUSE_SECONDS)
                continue
            raise LLMError(f"LLM call timed out after {TIMEOUT_SECONDS} s ({attempt} attempts)") from None
        except requests.ConnectionError as e:
            # `from None` drops the original exception, whose text includes the URL.
            raise LLMError(f"Could not connect to the LLM endpoint ({type(e).__name__})") from None

        usage = _usage(response)
        input_tokens += usage.get("prompt_tokens", 0)
        output_tokens += usage.get("completion_tokens", 0)
        if response.status_code >= 500 and attempt < MAX_ATTEMPTS:
            logging.warning("LLM call failed with HTTP %d; retrying once", response.status_code)
            time.sleep(RETRY_PAUSE_SECONDS)
            continue
        break
    elapsed_ms = round((time.perf_counter() - start) * 1000)

    if response.status_code != 200:
        raise LLMError(f"LLM call failed with HTTP {response.status_code} ({attempt} attempts): "
                       f"{response.text[:300]}")

    data = response.json()
    if "prompt_tokens" not in (data.get("usage") or {}):
        logging.warning("Endpoint returned no token usage; recording 0 tokens")
    return LLMResult(
        text=data["choices"][0]["message"]["content"] or "",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        elapsed_ms=elapsed_ms,
        attempts=attempt,
    )


def _usage(response):
    """Token usage from a response body, or {} if there is none (e.g. an HTML error page)."""
    try:
        return response.json().get("usage") or {}
    except ValueError:
        return {}
