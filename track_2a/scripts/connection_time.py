"""Connection set-up time per model call on the real endpoint, new connection per call vs one reused connection
(session 10, step 1). Real model calls: 2 per case.

Run from track_2a/ (key in .env or the environment; never printed):

    LLM_MIN_INTERVAL=1 python3 scripts/connection_time.py --cases output/devB/cases.jsonl --n 20 --out <folder>

Every case runs src/cli.py's predict() twice, back to back, in an order that alternates from case to case:

- "today": src/llm.py as it is (requests.post: a new connection for every call);
- "reused": the same code with requests.post replaced by the post of one requests.Session kept for the whole
  run (keep-alive: one connection, reused while the server keeps it open).

For every call the script records, around src/llm.py's requests.post:

    setup_ms      from the call of post() to the first byte of the request written to the socket: building the
                  request, reading proxy settings, DNS, TCP connect and TLS (through the sandbox's proxy here)
    connect_ms    the part spent in urllib3's connect() (DNS, TCP, proxy tunnel, TLS); 0 when a connection
                  was reused
    total_ms      from the call of post() to the response read

Local time in the organisers' sense is the time without a request in flight; set-up before the request's first
byte reaches the proxy is local time. The sandbox reaches the endpoint through an egress proxy, so the
absolute numbers are indicative; the difference between the two arms is the point. Writes <folder>/calls.jsonl
(one line per call: case, arm, the three times, whether a connection was opened; no headers, no key) and
<folder>/summary.json, and prints the summary.
"""

import argparse
import http.client
import json
import statistics
import sys
import time
from pathlib import Path

import requests
import urllib3.connection

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import cli, llm  # noqa: E402

_probe = {"connect_s": 0.0, "connects": 0, "first_send": None, "in_connect": False}


def _patch_sockets():
    """Record time spent in urllib3's connect() and the moment of the first send() of a request."""
    for cls in {urllib3.connection.HTTPConnection, urllib3.connection.HTTPSConnection}:
        original = cls.connect

        def connect(self, _original=original):
            t = time.perf_counter()
            _probe["in_connect"] = True  # a proxy tunnel's CONNECT is sent during connect(): not the request
            try:
                return _original(self)
            finally:
                _probe["in_connect"] = False
                _probe["connect_s"] += time.perf_counter() - t
                _probe["connects"] += 1
        cls.connect = connect
    original_send = http.client.HTTPConnection.send

    def send(self, data):
        if _probe["first_send"] is None and not _probe["in_connect"]:
            _probe["first_send"] = time.perf_counter()
        return original_send(self, data)
    http.client.HTTPConnection.send = send


def timed(post, log, arm, case_id):
    def wrapper(*args, **kwargs):
        _probe.update(connect_s=0.0, connects=0, first_send=None)
        t0 = time.perf_counter()
        response = post(*args, **kwargs)
        t1 = time.perf_counter()
        first = _probe["first_send"] or t1
        log.append({"case": case_id, "arm": arm, "setup_ms": round((first - t0) * 1000, 2),
                    "connect_ms": round(_probe["connect_s"] * 1000, 2), "connections_opened": _probe["connects"],
                    "total_ms": round((t1 - t0) * 1000, 1), "status": response.status_code})
        return response
    return wrapper


def summary(log):
    out = {}
    for arm in ("today", "reused"):
        rows = [r for r in log if r["arm"] == arm]
        if not rows:
            continue
        out[arm] = {"calls": len(rows), "connections_opened": sum(r["connections_opened"] for r in rows)}
        for key in ("setup_ms", "connect_ms", "total_ms"):
            values = [r[key] for r in rows]
            out[arm][key] = {"mean": round(statistics.mean(values), 1), "median": round(statistics.median(values), 1),
                             "max": round(max(values), 1)}
        later = [r["setup_ms"] for r in rows[1:]]
        if later:
            out[arm]["setup_ms_after_first_call_mean"] = round(statistics.mean(later), 1)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cases", required=True, help="task B cases (no booklets needed)")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cases = [json.loads(line) for line in Path(args.cases).read_text(encoding="utf-8").splitlines() if line.strip()]
    cases = [c for c in cases if "reference" in c][:args.n]
    _patch_sockets()
    plain_post = requests.post
    session = requests.Session()
    log = []
    for i, case in enumerate(cases):
        arms = ("today", "reused") if i % 2 == 0 else ("reused", "today")
        for arm in arms:
            post = plain_post if arm == "today" else session.post
            llm.requests.post = timed(post, log, arm, case["id"])
            try:
                cli.predict(case, settings=cli.Settings())
            finally:
                llm.requests.post = plain_post
        print(f"[{i + 1}/{len(cases)}] {case['id']}", file=sys.stderr)
    with open(out / "calls.jsonl", "w", encoding="utf-8") as f:
        for row in log:
            f.write(json.dumps(row) + "\n")
    result = {"cases": len(cases), "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "arms": summary(log)}
    (out / "summary.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
