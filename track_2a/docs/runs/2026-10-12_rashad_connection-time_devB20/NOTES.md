### Connection set-up per model call: new connection vs one kept connection (session 10, step 1)

20 dev task B cases (the first 20 whose reference has at most 8,000 characters, so no embedding model is
loaded), each answered twice by `cli.predict()` with the default settings, back to back, in an order that
alternates from case to case: once with `src/llm.py` as on `main` (`requests.post`, which opens a new
connection for every call), once with the same code but `requests.post` replaced by the `post` of one
`requests.Session` kept for the whole run. 40 real calls to Public AI's `apertus-v1.5-8b`, paced at one
request per second, all HTTP 200.

| | new connection per call (main) | one kept connection |
|---|---|---|
| connections opened | 20 | 1 |
| set-up before the first byte, mean | 486.0 ms | 24.3 ms |
| set-up, median | 465.3 ms | 1.2 ms |
| set-up after the first call, mean | 484.2 ms | 1.2 ms |
| whole call, mean | 1339.9 ms | 623.1 ms |

Set-up is the time from `post()` to the first byte of the request written to the socket: building the
request, reading the proxy settings, DNS, TCP, the sandbox's proxy tunnel (CONNECT) and TLS. It is local time
in the organisers' sense (no request has reached their proxy yet). The sandbox reaches the endpoint through
an egress proxy, so the absolute numbers belong to this sandbox; the organisers' proxy may be closer. The
difference is what a kept connection saves on every call after the first. The whole-call times also differ
because the second of two identical requests can come from the gateway's cache (about 10 minutes); they are
not compared.

Files: `calls.jsonl` (one line per call: case, arm, set-up, connect and total time, connections opened,
HTTP status), `summary.json`.
