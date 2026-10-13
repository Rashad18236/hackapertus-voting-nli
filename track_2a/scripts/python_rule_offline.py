"""Offline score of the Python rule "neutral with a citation -> contradiction" (session 10, step 6). No model calls.

Run from track_2a/:

    python3 scripts/python_rule_offline.py --arm docs/runs/<run>/<arm> --expected data/dev/expected-labels.jsonl \\
        [--arm ... --expected ...] [--json out.json]

The rule is never part of the pipeline (Rashad's instruction: every label comes from an answer of Apertus, and
Python never changes one); this script only scores what it would do, from saved answers. For every task A case
whose saved answer has label 1 and a non-empty "paragraphs" (or "pages") list, the rule's label is 2; every other
label stays. Reports, per arm, Macro-F1 and neutral recall as answered and under the rule, how many answers it
changes, and how many of those become right and wrong.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import evaluate  # noqa: E402


def load(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def cites(raw):
    try:
        answer = json.loads(raw.get("answer") or "")
    except ValueError:
        return False
    return isinstance(answer, dict) and bool(answer.get("paragraphs") or answer.get("pages"))


def score(arm, expected):
    gold = {g["id"]: g["label"] for g in load(expected)}
    preds = {p["id"]: p["label"] for p in load(Path(arm) / "predictions.jsonl")}
    raws = {r["id"]: r for r in load(Path(arm) / "raw_answers.jsonl")}
    ids = sorted(i for i in preds if i in gold and i.endswith("-A"))
    ruled = {i: (2 if preds[i] == 1 and cites(raws.get(i, {})) else preds[i]) for i in ids}
    changed = [i for i in ids if ruled[i] != preds[i]]
    before = evaluate.label_scores([gold[i] for i in ids], [preds[i] for i in ids])
    after = evaluate.label_scores([gold[i] for i in ids], [ruled[i] for i in ids])
    return {"arm": str(arm), "cases": len(ids), "changed": len(changed),
            "changed_now_right": sum(1 for i in changed if ruled[i] == gold[i]),
            "changed_now_wrong": sum(1 for i in changed if preds[i] == gold[i]),
            "macro_f1": round(before["macro_f1"], 4), "macro_f1_rule": round(after["macro_f1"], 4),
            "neutral_recall": round(before["per_class"]["neutral"]["recall"], 4),
            "neutral_recall_rule": round(after["per_class"]["neutral"]["recall"], 4), "changed_ids": changed}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arm", action="append", required=True)
    ap.add_argument("--expected", action="append", required=True)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()
    rows = [score(a, e) for a, e in zip(args.arm, args.expected)]
    for r in rows:
        print(f"{r['arm']}: {r['cases']} cases, rule changes {r['changed']} ({r['changed_now_right']} now right, "
              f"{r['changed_now_wrong']} now wrong); Macro-F1 {r['macro_f1']} -> {r['macro_f1_rule']}, "
              f"neutral recall {r['neutral_recall']} -> {r['neutral_recall_rule']}")
    if args.json:
        args.json.write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
