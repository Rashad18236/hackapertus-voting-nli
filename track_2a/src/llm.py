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

Endpoint identity (task B cheap fixes, continued): Public AI changed what it
serves under the same model name twice in 13 hours. Every result therefore
carries what the response says about who answered it (`endpoint_identity`):
the body's `model` and `system_fingerprint`, the response headers that name a
model, backend or provider, and the Cloudflare data centre. Nothing secret
and nothing that changes with every call (request ids, dates, durations,
spend and cost) is kept. Public AI's gateway also answers a request identical
to one sent in the last ~10 minutes from its cache (measured on 2026-10-09);
such an answer is marked `gateway_cache_hit`.
"""

import logging
import os
import re
import time
from dataclasses import dataclass, field
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


# Response headers kept as endpoint identity: the ones Public AI's gateway (LiteLLM behind Cloudflare) sent on
# 2026-10-09, plus any other header whose name mentions a model, backend, upstream, region, deployment or
# fingerprint, so that a new kind of backend still shows up. NOT_LOGGED wins over both: account data (key, spend,
# cost, ...) and values that differ on every call (request ids, dates, durations) are never kept.
IDENTITY_HEADERS = (
    "x-litellm-model-api-base",       # the backend LiteLLM forwarded the request to
    "x-litellm-model-id",             # LiteLLM's id of that deployment
    "x-litellm-model-name",           # the deployment's own model name
    "x-litellm-model-group",          # the model name we asked for
    "x-litellm-version",
    "x-litellm-attempted-fallbacks",  # > 0: LiteLLM fell back to another deployment
    "x-litellm-attempted-retries",
    "llm_provider-server",            # the backend's web server
    "server",
    "cf-placement",                   # where Cloudflare ran the gateway
)
IDENTITY_PATTERN = re.compile(r"model|backend|upstream|region|deployment|fingerprint", re.I)
NOT_LOGGED = re.compile(r"key|auth|cookie|token|secret|spend|cost|budget|request-id|call-id|date|duration", re.I)
# LiteLLM sends this header (its value is a hash; we keep only the fact that it is there) when the answer comes
# from its response cache: the same request was answered earlier, and this answer is a copy of that one.
CACHE_HIT_HEADER = "x-litellm-cache-key"


class LLMError(RuntimeError):
    """A model call failed. The message never contains the URL or the key.

    attempts, http_429 and endpoint describe the failed call like the fields of LLMResult."""

    def __init__(self, message, attempts=0, http_429=0, endpoint=None):
        super().__init__(message)
        self.attempts, self.http_429, self.endpoint = attempts, http_429, endpoint or {}


@dataclass
class LLMResult:
    text: str
    input_tokens: int
    output_tokens: int
    elapsed_ms: int
    attempts: int = 1        # requests sent for this call: 1 plus retries
    http_429: int = 0        # how many of them were answered with HTTP 429
    endpoint: dict = field(default_factory=dict)  # endpoint_identity() of the last answer
    fallbacks: list = field(default_factory=list)  # session 9: fallbacks this call used (see chat())


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


# Fallbacks when the endpoint refuses our request (session 9, A1). They hold for the rest of the run (this
# process): once response_format was refused it is not sent again, and once the model name was replaced, the
# new name is used. At most MAX_EXTRA_REQUESTS extra requests per run go to them.
MAX_EXTRA_REQUESTS = 3
_run = {"no_response_format": False, "model": None, "models_read": False, "extra_requests": 0, "last_start": 0.0}


def reset_run_state():
    """Forget the run's fallbacks (tests; a new process starts clean anyway)."""
    _run.update(no_response_format=False, model=None, models_read=False, extra_requests=0, last_start=0.0)


def min_interval():
    """Seconds between the starts of two requests: LLM_MIN_INTERVAL (development runs; default 0, no pause)."""
    try:
        return max(0.0, float(os.environ.get("LLM_MIN_INTERVAL") or 0))
    except ValueError:
        return 0.0


def chat(messages, max_tokens=256, json_mode=False, json_schema=None):
    """Send one chat request and return the answer with usage and timing.

    json_mode=True asks the endpoint for any JSON object (`response_format`
    json_object). json_schema (a JSON Schema dict) asks for an answer that
    matches that schema exactly (`response_format` json_schema, strict), which
    also fixes the keys; it takes precedence over json_mode.

    Fallbacks (session 9), each at most once per run and within MAX_EXTRA_REQUESTS extra requests per run:
    (a) HTTP 400 or 422 to a request with response_format: the same request again without it, and no
        response_format for the rest of the run (the parsers also read answers that are not forced JSON);
    (b) HTTP 404, or HTTP 400 once (a) has happened (the model name is the likely cause): read BASE_URL/models
        once, pick the id that names Apertus v1.5 8B (ignoring case; the shortest if several), and send the
        request again with it; that id is used for the rest of the run.
    Tokens and time of every request of the call are counted in its result.
    """
    configured_model, base, key = _settings()
    payload = {
        "model": _run["model"] or configured_model,
        "messages": messages,
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    if not _run["no_response_format"]:
        if json_schema is not None:
            payload["response_format"] = {"type": "json_schema",
                                          "json_schema": {"name": "answer", "schema": json_schema, "strict": True}}
        elif json_mode:
            payload["response_format"] = {"type": "json_object"}
    headers = {"Authorization": f"Bearer {key}", "User-Agent": USER_AGENT}

    start = time.perf_counter()
    counts = {"input_tokens": 0, "output_tokens": 0, "attempts": 0, "http_429": 0}  # over all requests
    fallbacks = []
    response = _post(base, payload, headers, counts)
    if (response.status_code in (400, 422) and "response_format" in payload
            and _run["extra_requests"] + 1 <= MAX_EXTRA_REQUESTS):
        logging.warning("The endpoint refused response_format (HTTP %d); sending the request again without it, "
                        "and no response_format for the rest of the run", response.status_code)
        _run["no_response_format"] = True
        _run["extra_requests"] += 1
        fallbacks.append("no response_format")
        payload = {k: v for k, v in payload.items() if k != "response_format"}
        response = _post(base, payload, headers, counts)
    if ((response.status_code == 404 or (response.status_code == 400 and _run["no_response_format"]))
            and not _run["models_read"] and _run["extra_requests"] + 2 <= MAX_EXTRA_REQUESTS):
        _run["models_read"] = True
        _run["extra_requests"] += 1
        picked = pick_model(list_models(base, headers))
        if picked and picked != payload["model"]:
            logging.warning("The endpoint refused the model name (HTTP %d); using %s, listed by the endpoint, for "
                            "the rest of the run", response.status_code, picked)
            _run["model"] = picked
            _run["extra_requests"] += 1
            fallbacks.append(f"model {picked}")
            payload = {**payload, "model": picked}
            response = _post(base, payload, headers, counts)
    elapsed_ms = round((time.perf_counter() - start) * 1000)

    if response.status_code != 200:
        raise LLMError(f"LLM call failed with HTTP {response.status_code} ({counts['attempts']} attempts): "
                       f"{response.text[:300]}", counts["attempts"], counts["http_429"], endpoint_identity(response))

    data = response.json()
    if "prompt_tokens" not in (data.get("usage") or {}):
        logging.warning("Endpoint returned no token usage; recording 0 tokens")
    return LLMResult(
        text=data["choices"][0]["message"]["content"] or "",
        input_tokens=counts["input_tokens"],
        output_tokens=counts["output_tokens"],
        elapsed_ms=elapsed_ms,
        attempts=counts["attempts"],
        http_429=counts["http_429"],
        endpoint=endpoint_identity(response),
        fallbacks=fallbacks,
    )


def _post(base, payload, headers, counts):
    """POST one chat request, with the retries for timeouts, HTTP 5xx and HTTP 429 (module docstring); add every
    attempt's tokens and the attempt and 429 counts to counts. Returns the last response."""
    server_retries = rate_retries = 0
    while True:
        counts["attempts"] += 1
        wait = _run["last_start"] + min_interval() - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _run["last_start"] = time.monotonic()
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
            raise LLMError(f"LLM call timed out after {TIMEOUT_SECONDS} s ({counts['attempts']} attempts)",
                           counts["attempts"], counts["http_429"]) from None
        except requests.ConnectionError as e:
            # `from None` drops the original exception, whose text includes the URL.
            raise LLMError(f"Could not connect to the LLM endpoint ({type(e).__name__})", counts["attempts"],
                           counts["http_429"]) from None

        usage = _usage(response)
        counts["input_tokens"] += usage.get("prompt_tokens", 0)
        counts["output_tokens"] += usage.get("completion_tokens", 0)
        if response.status_code == 429:
            counts["http_429"] += 1
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
        return response


def list_models(base, headers):
    """The model ids BASE_URL/models lists, or [] if it cannot be read."""
    try:
        response = requests.get(f"{base}/models", headers=headers, timeout=TIMEOUT_SECONDS)
        return [str(m.get("id")) for m in response.json().get("data", []) if isinstance(m, dict) and m.get("id")]
    except (requests.RequestException, ValueError, AttributeError):
        return []


def pick_model(ids):
    """The id that names Apertus v1.5 8B, ignoring case ("apertus", "v1.5" and "8b" as a size); the shortest if
    several (the plain model before variants such as "-thinking"), or None."""
    found = [i for i in ids if "apertus" in i.lower() and "v1.5" in i.lower()
             and re.search(r"(?<![\d.])8b\b", i.lower())]
    return min(found, key=lambda i: (len(i), i)) if found else None


def endpoint_identity(response):
    """What one response says about who answered it: the body's model and system_fingerprint (if present), the
    identifying headers (IDENTITY_HEADERS, IDENTITY_PATTERN; never NOT_LOGGED), Cloudflare's data centre (the
    code after the dash in CF-RAY; the ray id before it is per call) and gateway_cache_hit: True when the gateway
    answered from its cache (CACHE_HIT_HEADER present; then the routing headers describe the gateway's current
    choice, while model and system_fingerprint belong to the cached answer). Values lose any query string, in
    case a URL carries one, and are cut at 200 characters."""
    identity = {}
    try:
        body = response.json()
    except ValueError:
        body = None
    if isinstance(body, dict):
        identity.update({k: body[k] for k in ("model", "system_fingerprint") if body.get(k) is not None})
    headers = {}
    for name, value in (getattr(response, "headers", None) or {}).items():
        name = name.lower()
        if (name in IDENTITY_HEADERS or IDENTITY_PATTERN.search(name)) and not NOT_LOGGED.search(name):
            headers[name] = str(value).split("?")[0][:200]
        elif name == "cf-ray" and "-" in str(value):
            identity["cf_ray_datacentre"] = str(value).rsplit("-", 1)[1][:10]
        elif name == CACHE_HIT_HEADER:
            identity["gateway_cache_hit"] = True
    if headers:
        identity["headers"] = dict(sorted(headers.items()))
    return identity


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
