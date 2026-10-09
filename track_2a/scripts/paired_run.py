"""Run two or more pipeline configurations on the same cases, back to back, for a fair comparison.

Run from track_2a/:

    python3 scripts/paired_run.py --cases CASES.jsonl --data-dir DIR --out-dir OUT \\
        --arm '{"name": "fulldoc-prompt"}' --arm '{"name": "fulldoc-schema", "schema_a": true, "max_tokens_a": 128}'

Each arm is a JSON object: "name" plus any fields of src.cli.Settings.
For every case all arms run one after the other, and the order rotates from
case to case (arm_order): with two arms, even cases run the first arm first
and odd cases the second; with an even number of arms, the orders of a
balanced Latin square (Williams design) take turns, so over every n cases
each arm is in each position once and directly follows each other arm once.
So endpoint drift over time and prompt-prefix caching (two arms that send the
same prompt profit from each other's cache) affect all arms equally. With an
odd number of arms the order is a plain rotation.

--min-interval S keeps at least S seconds between the starts of two requests
(across arms), to stay under the endpoint's rate limit. The pause lies
outside the timed case. Retries inside a call (src/llm.py) are not paced.

Before timing starts, every booklet referenced by the cases is parsed once
(warm cache), so neither arm's times include PDF parsing.

Output per arm: OUT/<name>/predictions.jsonl and raw_answers.jsonl, appended
after every case (a stopped run keeps its finished cases), and run.log with
the status counts, the HTTP 429 answers and the retries. Each raw answer also
records its position in the case's order and the UTC time it was sent.
--resume continues a stopped run: cases already present in an arm's output
are skipped for that arm (the order rule stays the same), nothing is re-run.
Calls the same code as the official entrypoint (src.cli.predict).
"""

import argparse
import datetime
import json
import logging
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import cli, env, parse  # noqa: E402


def arm_order(i, n):
    """The order of the n arms for case i (0-based); see the module docstring. For n = 4 the four orders are
    0 1 3 2, 1 2 0 3, 2 3 1 0 and 3 0 2 1."""
    first = list(range(n))
    if n % 2 == 0:  # Williams design: 0, 1, n-1, 2, n-2, ...
        first, low, high = [0], 1, n - 1
        while len(first) < n:
            first.append(low)
            low += 1
            if len(first) < n:
                first.append(high)
                high -= 1
    return [(arm + i) % n for arm in first]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cases", type=Path, required=True)
    p.add_argument("--data-dir", type=Path, required=True, help="folder that booklet paths are relative to")
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--arm", action="append", required=True, help="JSON settings; give two or more")
    p.add_argument("--min-interval", type=float, default=0.0,
                   help="seconds between the starts of two requests (default 0: no pause)")
    p.add_argument("--resume", action="store_true", help="continue a stopped run in the same --out-dir")
    args = p.parse_args()
    if len(args.arm) < 2:
        p.error("give at least two --arm options")
    arms = [json.loads(a) for a in args.arm]
    names = [a.pop("name") for a in arms]
    settings = [cli.Settings(**a) for a in arms]

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    env.load_env_file()
    cases = [json.loads(line) for line in args.cases.read_text(encoding="utf-8").splitlines() if line.strip()]

    booklets = sorted({c["booklet"]["path"] for c in cases if "booklet" in c})
    for b in booklets:  # warm the cache: parsing time stays out of the comparison
        if (args.data_dir / b).is_file():
            parse.load_pages(args.data_dir / b)
    print(f"{len(cases)} cases, {len(booklets)} booklets parsed; arms: {names}", flush=True)

    out, done = {}, {}
    mode = "a" if args.resume else "w"
    calls = {name: Counter() for name in names}  # per arm: HTTP 429 answers and retries
    for name, s in zip(names, settings):
        d = args.out_dir / name
        d.mkdir(parents=True, exist_ok=True)
        done[name] = set()
        counts = Counter()
        if args.resume and (d / "raw_answers.jsonl").exists():
            for line in (d / "raw_answers.jsonl").read_text(encoding="utf-8").splitlines():
                raw = json.loads(line)
                done[name].add(raw["id"])
                counts["ok" if not (raw.get("error") or raw.get("parse_reason")) else "resumed: earlier failure"] += 1
                count_calls(calls[name], raw)
        else:
            (d / "settings.json").write_text(json.dumps({"name": name, **vars(s)}, indent=1) + "\n", encoding="utf-8")
        out[name] = (open(d / "predictions.jsonl", mode, encoding="utf-8"),
                     open(d / "raw_answers.jsonl", mode, encoding="utf-8"), counts)

    last_start = 0.0
    for i, case in enumerate(cases):
        order = arm_order(i, len(names))
        line = []
        for k in order:
            name, s = names[k], settings[k]
            if case["id"] in done[name]:
                continue
            time.sleep(max(0.0, last_start + args.min_interval - time.monotonic()))  # pacing, outside the timed case
            last_start = time.monotonic()
            sent = f"{datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M:%S}"
            try:
                resp, status, raw = cli.predict(case, args.data_dir, s)
            except Exception as e:  # same guarantee as the CLI: never drop a case
                resp, status, raw = cli.response(case["id"], cli.FALLBACK_LABEL), f"unexpected error ({type(e).__name__})", {"id": case["id"]}
            raw["order"], raw["sent_utc"] = order.index(k) + 1, sent
            count_calls(calls[name], raw)
            preds, raws, counts = out[name]
            preds.write(json.dumps(resp, ensure_ascii=False) + "\n")
            raws.write(json.dumps(raw, ensure_ascii=False) + "\n")
            preds.flush()
            raws.flush()
            counts[status] += 1
            line.append(f"{name}: {resp['label_name']}{'' if status == 'ok' else ' (' + status + ')'}")
        if line:
            print(f"[{i + 1}/{len(cases)}] {case['id']} | " + " | ".join(line), flush=True)

    for name in names:
        preds, raws, counts = out[name]
        preds.close()
        raws.close()
        summary = ", ".join(f"{k}: {v}" for k, v in counts.most_common())
        summary += f"; HTTP 429 answers: {calls[name]['http_429']}, retries: {calls[name]['retries']}"
        (args.out_dir / name / "run.log").write_text(summary + "\n", encoding="utf-8")
        print(f"{name}: {summary}", flush=True)


def count_calls(counter, raw):
    """Add one case's HTTP 429 answers and retries (requests beyond the first) to counter."""
    counter["http_429"] += raw.get("http_429", 0)
    counter["retries"] += max(0, raw.get("attempts", 1) - 1)


if __name__ == "__main__":
    main()
