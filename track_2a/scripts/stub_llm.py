"""A fake Apertus endpoint for tests: a tiny local server with the chat completions interface.

Run from track_2a/:

    python3 scripts/stub_llm.py --port 8099
    BASE_URL=http://127.0.0.1:8099/v1 API_KEY=stub python3 -m src.cli --input ... --output ...

No model is involved and nothing leaves the machine. Standard library only, so
it also runs inside the pipeline's Docker image (CI: .github/workflows/).

POST /v1/chat/completions (or /chat/completions) answers like the real
endpoint: HTTP 200, the answer in choices[0].message.content, and token counts
in usage. The answer is fixed and always valid for the request's answer
format (read from response_format.json_schema, as src/llm.py sends it):

- schema with "paragraphs" (task A, section-route):  {"paragraphs": [1], "label": L}
- schema with "pages" (task A, page contexts):        {"pages": [P], "label": L}, P = the first
                                                       "=== PAGE n ===" number in the request, else 1
- anything else (task B):                             {"label": L}

L is --label (default 0). prompt_tokens and completion_tokens are fixed
(--prompt-tokens, --completion-tokens), so tests can check the metrics.

Failures for chosen calls, either by call number (1-based, counted over all
requests the server gets, retries included) or by a marker anywhere in the
request's messages (independent of the order of the cases):

    --fail-calls 2,5      HTTP 500 for these calls (src/llm.py retries once on 5xx)
    --garbage-calls 3     HTTP 200 with a content that is not JSON
    --html-calls 4        HTTP 200 with an HTML page instead of a JSON body
    --error-calls 6       HTTP 400 (no retry)

    STUB_FAIL       HTTP 500 on every attempt (the case's call fails)
    STUB_FAIL_ONCE  HTTP 500 on the first attempt of this request only, then the normal answer
    STUB_GARBAGE    HTTP 200, content "certainly! the label is probably entailment {"
    STUB_EMPTY      HTTP 200, content null
    STUB_HTML       HTTP 200, an HTML body (not JSON)
    STUB_400        HTTP 400 with an error message
    STUB_NO_USAGE   the normal answer without a usage block
    STUB_LABEL_1, STUB_LABEL_2   the normal answer with that label
    STUB_BAD_PAGES  {"pages": [9999], "paragraphs": [9999], "label": L}: numbers outside what was sent

GET /_stub/calls returns the log of all calls so far (number, path, model,
whether an Authorization header and a User-Agent were sent, the answer kind,
and request_sha256, the SHA-256 of the request body: see request_hash);
POST /_stub/reset clears it. The API key's value is never stored or printed.

Replay (session 8): --replay TABLE.json, a JSON object {request_sha256: answer
text}. A request whose hash is in the table gets that text as its answer
(kind "replay"): a saved real answer for exactly this request. Any other
request gets the fixed answer above (kind "ok"). scripts/prompt_snapshot.py
builds the table from saved runs. With keep_payloads=True (module use only)
every call's request body is kept in the log, for matching calls to cases.

As a module (tests): `server, url = start(port=0, label=0)`, then `server.shutdown()`.
"""

import argparse
import hashlib
import json
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MARKERS = ("STUB_FAIL_ONCE", "STUB_FAIL", "STUB_GARBAGE", "STUB_EMPTY", "STUB_HTML", "STUB_400", "STUB_NO_USAGE",
           "STUB_LABEL_1", "STUB_LABEL_2", "STUB_BAD_PAGES")
GARBAGE = "certainly! the label is probably entailment {"
HTML = "<html><body><h1>502 Bad Gateway</h1></body></html>"
_PAGE = re.compile(r"=== PAGE (\d+) ===")
_MARKER = re.compile(r"STUB_[A-Z0-9_]+")


def request_hash(payload):
    """SHA-256 of a request body (model, messages, max_tokens, temperature, response_format, ...) in a canonical
    form: keys sorted, no spaces, non-ASCII characters as they are. Equal hashes = byte-identical requests."""
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class Config:
    def __init__(self, label=0, prompt_tokens=100, completion_tokens=10, fail_calls=(), garbage_calls=(),
                 html_calls=(), error_calls=(), replay=None, keep_payloads=False):
        self.label = label
        self.replay = replay            # {request_sha256: answer text}, or None
        self.keep_payloads = keep_payloads
        self.prompt_tokens, self.completion_tokens = prompt_tokens, completion_tokens
        self.by_call = {}
        for kind, calls in (("fail", fail_calls), ("garbage", garbage_calls), ("html", html_calls),
                            ("error", error_calls)):
            for n in calls:
                self.by_call[int(n)] = kind
        self.lock = threading.Lock()
        self.calls = []         # one dict per call, in arrival order
        self.failed_once = set()  # request hashes that already got their STUB_FAIL_ONCE failure


def _schema_keys(payload):
    fmt = payload.get("response_format") or {}
    schema = (fmt.get("json_schema") or {}).get("schema") or {}
    return set(schema.get("properties") or {})


def _text(payload):
    return "\n".join(str(m.get("content", "")) for m in payload.get("messages") or [] if isinstance(m, dict))


def answer_for(payload, label):
    """The fixed valid answer for this request's answer format."""
    keys, text = _schema_keys(payload), _text(payload)
    if "paragraphs" in keys:
        return {"paragraphs": [1], "label": label}
    if "pages" in keys:
        pages = _PAGE.findall(text)
        return {"pages": [int(pages[0]) if pages else 1], "label": label}
    return {"label": label}


def decide(payload, config, number):
    """(kind, label) for this call. kind: ok, fail, garbage, empty, html, error, no_usage, bad_pages."""
    found = set(_MARKER.findall(_text(payload))) & set(MARKERS)
    label = config.label
    for n in (1, 2):
        if f"STUB_LABEL_{n}" in found:
            label = n
    if number in config.by_call:
        return config.by_call[number], label
    if "STUB_FAIL_ONCE" in found:
        key = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
        with config.lock:
            first = key not in config.failed_once
            config.failed_once.add(key)
        return ("fail" if first else "ok"), label
    for marker, kind in (("STUB_FAIL", "fail"), ("STUB_GARBAGE", "garbage"), ("STUB_EMPTY", "empty"),
                         ("STUB_HTML", "html"), ("STUB_400", "error"), ("STUB_NO_USAGE", "no_usage"),
                         ("STUB_BAD_PAGES", "bad_pages")):
        if marker in found:
            return kind, label
    return "ok", label


def make_handler(config):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # keep test output quiet
            pass

        def _send(self, status, body, content_type="application/json"):
            data = body.encode("utf-8") if isinstance(body, str) else json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path.rstrip("/") == "/_stub/calls":
                with config.lock:
                    return self._send(200, {"calls": list(config.calls)})
            if self.path.rstrip("/") in ("/health", "/v1/models"):
                return self._send(200, {"data": [{"id": "stub"}]})
            self._send(404, {"error": {"message": "not found"}})

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length)
            if self.path.rstrip("/") == "/_stub/reset":
                with config.lock:
                    config.calls.clear()
                    config.failed_once.clear()
                return self._send(200, {"ok": True})
            if self.path.rstrip("/") not in ("/v1/chat/completions", "/chat/completions"):
                return self._send(404, {"error": {"message": "not found"}})
            try:
                payload = json.loads(body)
            except ValueError:
                return self._send(400, {"error": {"message": "request body is not JSON"}})
            with config.lock:
                number = len(config.calls) + 1
                entry = {"number": number, "path": self.path, "model": payload.get("model"),
                         "authorization": self.headers.get("Authorization", "").startswith("Bearer "),
                         "user_agent": self.headers.get("User-Agent", ""),
                         "schema_keys": sorted(_schema_keys(payload)), "max_tokens": payload.get("max_tokens"),
                         "request_sha256": request_hash(payload)}
                if config.keep_payloads:
                    entry["payload"] = payload
                config.calls.append(entry)
            kind, label = decide(payload, config, number)
            if kind == "ok" and config.replay is not None and entry["request_sha256"] in config.replay:
                kind = "replay"
            entry["kind"] = kind
            usage = {"prompt_tokens": config.prompt_tokens, "completion_tokens": config.completion_tokens,
                     "total_tokens": config.prompt_tokens + config.completion_tokens}
            if kind == "fail":
                return self._send(500, {"error": {"message": "stub: internal server error"}})
            if kind == "error":
                return self._send(400, {"error": {"message": "stub: bad request"}})
            if kind == "html":
                return self._send(200, HTML, "text/html")
            if kind == "garbage":
                content = GARBAGE
            elif kind == "empty":
                content = None
            elif kind == "replay":
                content = config.replay[entry["request_sha256"]]
            else:
                answer = answer_for(payload, label)
                if kind == "bad_pages":
                    answer = {k: ([9999] if isinstance(v, list) else v) for k, v in answer.items()}
                content = json.dumps(answer)
            reply = {"id": f"stub-{number}", "object": "chat.completion", "model": payload.get("model"),
                     "choices": [{"index": 0, "finish_reason": "stop",
                                  "message": {"role": "assistant", "content": content}}]}
            if kind != "no_usage":
                reply["usage"] = usage
            self._send(200, reply)

    return Handler


def start(host="127.0.0.1", port=0, **config_args):
    """Start the server in a background thread. Returns (server, base URL with /v1)."""
    config = Config(**config_args)
    server = ThreadingHTTPServer((host, port), make_handler(config))
    server.config = config
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://{host}:{server.server_address[1]}/v1"


def _numbers(text):
    return [int(n) for n in text.split(",") if n.strip()] if text else []


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="127.0.0.1", help="0.0.0.0 inside a container")
    ap.add_argument("--port", type=int, default=8099)
    ap.add_argument("--label", type=int, choices=(0, 1, 2), default=0)
    ap.add_argument("--prompt-tokens", type=int, default=100)
    ap.add_argument("--completion-tokens", type=int, default=10)
    ap.add_argument("--fail-calls", type=_numbers, default=[])
    ap.add_argument("--garbage-calls", type=_numbers, default=[])
    ap.add_argument("--html-calls", type=_numbers, default=[])
    ap.add_argument("--error-calls", type=_numbers, default=[])
    ap.add_argument("--replay", help="JSON file {request_sha256: answer text} (scripts/prompt_snapshot.py)")
    args = ap.parse_args()
    replay = None
    if args.replay:
        with open(args.replay, encoding="utf-8") as f:
            replay = json.load(f)
    config = Config(label=args.label, prompt_tokens=args.prompt_tokens, completion_tokens=args.completion_tokens,
                    fail_calls=args.fail_calls, garbage_calls=args.garbage_calls, html_calls=args.html_calls,
                    error_calls=args.error_calls, replay=replay)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(config))
    print(f"stub LLM listening on http://{args.host}:{server.server_address[1]}/v1", file=sys.stderr, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
