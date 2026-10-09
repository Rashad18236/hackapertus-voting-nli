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

Retries:
- HTTP 5xx answers and timeouts: exactly one retry, after RETRY_PAUSE_SECONDS;
  the request most likely never produced an answer (e.g. Public AI's gateway
  504 after about 61 s).
- HTTP 429 (rate limit; one task B case was lost to it on 2026-10-09): up to
  RATE_LIMIT_RETRIES retries. The wait is the server's Retry-After header if
  it sends one, otherwise 2 s, then 4 s; never more than RATE_LIMIT_MAX_WAIT.
The organisers count every token, retries included, so any usage reported by a
failed attempt is added to the result, and the elapsed time covers all
attempts and waits (it also counts in the case's inference_time_ms, which
src/cli.py measures around the whole case). All other failures raise LLMError
at once.
"""

import logging
import os
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime

import requests

# Public AI rejects requests without a User-Agent header.
USER_AGENT = "hackapertus-voting-nli/0.1"
TIMEOUT_SECONDS = 120
MAX_ATTEMPTS = 2          # 5xx and timeouts: the first call plus one retry
RETRY_PAUSE_SECONDS = 2
RATE_LIMIT_RETRIES = 2    # HTTP 429: up to two retries
RATE_LIMIT_PAUSES = (2, 4)  # seconds before the first and second 429 retry, without Retry-After
RATE_LIMIT_MAX_WAIT = 10  # never wait longer than this for one retry


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


def chat(messages, max_tokens=256, json_mode=False, json_schema=None):
    """Send one chat request and return the answer with usage and timing.

    json_mode=True asks the endpoint for any JSON object (`response_format`
    json_object). json_schema (a JSON Schema dict) asks for an answer that
    matches that schema exactly (`response_format` json_schema, strict), which
    also fixes the keys; it takes precedence over json_mode.
    """
    model, base, key = _settings()
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    if json_schema is not None:
        payload["response_format"] = {"type": "json_schema",
                                      "json_schema": {"name": "answer", "schema": json_schema, "strict": True}}
    elif json_mode:
        payload["response_format"] = {"type": "json_object"}
    headers = {"Authorization": f"Bearer {key}", "User-Agent": USER_AGENT}

    start = time.perf_counter()
    input_tokens = output_tokens = 0  # summed over attempts that report usage
    attempt = server_retries = rate_retries = 0
    while True:
        attempt += 1
        try:
            response = requests.post(
                f"{base}/chat/completions", json=payload, headers=headers, timeout=TIMEOUT_SECONDS
            )
        except requests.Timeout:
            if server_retries < MAX_ATTEMPTS - 1:
                server_retries += 1
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
        if response.status_code >= 500 and server_retries < MAX_ATTEMPTS - 1:
            server_retries += 1
            logging.warning("LLM call failed with HTTP %d; retrying once", response.status_code)
            time.sleep(RETRY_PAUSE_SECONDS)
            continue
        if response.status_code == 429 and rate_retries < RATE_LIMIT_RETRIES:
            wait = rate_limit_wait(response, rate_retries)
            rate_retries += 1
            logging.warning("LLM call rate-limited (HTTP 429); retry %d of %d in %.1f s",
                            rate_retries, RATE_LIMIT_RETRIES, wait)
            time.sleep(wait)
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


def rate_limit_wait(response, retries_so_far):
    """Seconds to wait before retrying an HTTP 429: Retry-After (seconds or an HTTP date) if the server sends it,
    otherwise RATE_LIMIT_PAUSES; always between 0 and RATE_LIMIT_MAX_WAIT."""
    header = (getattr(response, "headers", None) or {}).get("Retry-After")
    wait = RATE_LIMIT_PAUSES[min(retries_so_far, len(RATE_LIMIT_PAUSES) - 1)]
    if header:
        try:
            wait = float(header)
        except ValueError:
            try:
                wait = parsedate_to_datetime(header).timestamp() - time.time()
            except (TypeError, ValueError):
                pass  # an unreadable header: keep the default pause
    return max(0.0, min(float(wait), RATE_LIMIT_MAX_WAIT))


def _usage(response):
    """Token usage from a response body, or {} if there is none (e.g. an HTML error page)."""
    try:
        return response.json().get("usage") or {}
    except ValueError:
        return {}
