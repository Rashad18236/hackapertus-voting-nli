"""Session 13, step 4: what each Apertus role costs in a run (no model calls).

Run from track_2a/:

    python3 scripts/apertus_roles.py --run docs/runs/<final>_dev600 [--out FILE.json]

Reads task-A/raw_answers.jsonl and task-B/raw_answers.jsonl of a final run folder. Roles: the label call (every case
with an answer), AP-part (part named by Apertus), AP-structure (contents read by Apertus; a booklet's call is counted
in its first case), AP-translate (a claim translated for the BM25 fallback or B-BM25), A6 (second look,
`second_look_a6`). For each: calls per 100 cases of the task, and mean input and output tokens per call.
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

ROLE_OF_VERSION = {"AP-part": "AP-part", "AP-claim": "AP-part", "AP-structure": "AP-structure",
                   "AP-translate": "AP-translate"}


def role(version):
    for prefix, name in ROLE_OF_VERSION.items():
        if (version or "").startswith(prefix):
            return name
    return version or "unknown"


def load(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--run", required=True)
    parser.add_argument("--out")
    args = parser.parse_args()
    table = {}
    for task in ("A", "B"):
        path = Path(args.run) / f"task-{task}" / "raw_answers.jsonl"
        if not path.is_file():
            continue
        raws = load(path)
        calls = defaultdict(lambda: [0, 0, 0])  # role -> [calls, input tokens, output tokens]
        preds = {p["id"]: p for p in load(Path(args.run) / f"task-{task}" / "predictions.jsonl")}
        for r in raws:
            if r.get("answer") is not None or r.get("error"):
                c = calls["label"]
                c[0] += 1
                metrics = preds.get(r["id"], {}).get("metrics", {})
                ap_in, ap_out = r.get("ap_tokens", [0, 0])
                look = r.get("second_look_a6") or {}
                c[1] += metrics.get("input_tokens", 0) - ap_in - look.get("input_tokens", 0)
                c[2] += metrics.get("output_tokens", 0) - ap_out - look.get("output_tokens", 0)
            for call in r.get("ap_calls", []):
                c = calls[role(call.get("version"))]
                c[0] += 1
                c[1] += call.get("input_tokens", 0)
                c[2] += call.get("output_tokens", 0)
            if "answer" in (r.get("second_look_a6") or {}):
                look = r["second_look_a6"]
                c = calls["A6 second look"]
                c[0] += 1
                c[1] += look.get("input_tokens", 0)
                c[2] += look.get("output_tokens", 0)
        n = len(raws)
        table[task] = {"cases": n, "roles": {name: {"calls": v[0], "per_100_cases": round(100 * v[0] / n, 2),
                                                     "input_per_call": round(v[1] / v[0], 1) if v[0] else None,
                                                     "output_per_call": round(v[2] / v[0], 1) if v[0] else None}
                                              for name, v in calls.items()}}
        print(task, json.dumps(table[task]))
    if args.out:
        Path(args.out).write_text(json.dumps(table, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
