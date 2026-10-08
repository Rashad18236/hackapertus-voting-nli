"""Check a predictions file against the official response format.

Run from track_2a/:  python3 scripts/check_format.py PREDICTIONS CASES

Checks, per the contract (docs/official_contract.md): exactly one response per
request id; label in 0/1/2 with the matching label_name; evidence a list of
objects with `text` (non-empty, at most 5,000 characters) and `page` (an int
>= 1 for task A, null for task B); metrics with non-negative integer
input_tokens, output_tokens and inference_time_ms. Exits 1 on any problem.
"""

import json
import sys
from collections import Counter

NAMES = {0: "entailment", 1: "neutral", 2: "contradiction"}


def main():
    preds = [json.loads(line) for line in open(sys.argv[1], encoding="utf-8") if line.strip()]
    cases = {json.loads(line)["id"]: json.loads(line) for line in open(sys.argv[2], encoding="utf-8") if line.strip()}
    problems = Counter()
    ids = Counter(p.get("id") for p in preds)
    problems["missing response"] = sum(1 for i in cases if i not in ids)
    problems["duplicate id"] = sum(1 for v in ids.values() if v > 1)
    problems["unknown id"] = sum(1 for i in ids if i not in cases)
    for p in preds:
        case = cases.get(p.get("id"), {})
        task_a = "booklet" in case
        label = p.get("label")
        if not isinstance(label, int) or isinstance(label, bool) or label not in NAMES:
            problems["invalid label"] += 1
        elif p.get("label_name") != NAMES[label]:
            problems["label_name does not match"] += 1
        evidence = p.get("evidence")
        if not isinstance(evidence, list):
            problems["evidence not a list"] += 1
            evidence = []
        for item in evidence:
            if not isinstance(item, dict) or not isinstance(item.get("text"), str) or not item["text"].strip():
                problems["evidence item without text"] += 1
                continue
            if len(item["text"]) > 5000:
                problems["evidence item over 5,000 characters"] += 1
            page = item.get("page")
            if task_a and not (isinstance(page, int) and not isinstance(page, bool) and page >= 1):
                problems["task A evidence page not an int >= 1"] += 1
            if not task_a and page is not None:
                problems["task B evidence page not null"] += 1
        if task_a and label in (0, 2) and not evidence:
            problems["(warning) task A label 0/2 without evidence"] += 1
        metrics = p.get("metrics")
        for key in ("input_tokens", "output_tokens", "inference_time_ms"):
            value = metrics.get(key) if isinstance(metrics, dict) else None
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                problems[f"metrics.{key} not a non-negative int"] += 1
    errors = {k: v for k, v in problems.items() if v and not k.startswith("(warning)")}
    warnings = {k: v for k, v in problems.items() if v and k.startswith("(warning)")}
    print(f"{len(preds)} responses for {len(cases)} requests")
    print("errors:", errors or "none")
    print("warnings:", warnings or "none")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
