"""Session 10's acceptance rules for the arms of one interleaved run against the arm "today" (no model calls).

Run from track_2a/ (each arm folder holds predictions.jsonl and raw_answers.jsonl, as scripts/paired_run.py
writes them):

    python3 scripts/rule_check.py --run docs/runs/<run> --task A --today today --arms P-short K4 \\
        --expected data/dev/expected-labels.jsonl [--json out.json]

Per arm, on all cases and on the cases where every arm was answered by the same backend (system_fingerprint of
the answer; src/llm.py records it per call): Macro-F1 (src/evaluate.py, equal to the starter's), task A's evidence
score (the starter's rule, scripts/evidence_loss.py), neutral recall, unreadable answers (an answer that could not
be read, so the case got the neutral fallback), failed calls, mean input and output tokens per case.

TOKEN RULE (step 5; one set; the decision needs dev and val): against today, Macro-F1 at most 0.005 lower, evidence
at most 0.010 lower (task A), neutral recall at least 0.98 (task A), no more unreadable answers, input tokens at
least 10 % lower. Printed per criterion, pass or fail, on all cases. Cases outside --expected are left out (the
on-topic neutral set has its own file).

Fixes and breaks (step 6's PAIRED RULE (c)): cases wrong under today and right under the arm, and the other way
round, with the exact two-sided sign test's p-value; printed per arm, to be added over dev and val.
"""

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import evidence_loss as el  # noqa: E402
from src import evaluate  # noqa: E402


def load(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def backend(raw):
    return (raw.get("endpoint") or {}).get("system_fingerprint")


def sign_test(fixes, breaks):
    """Exact two-sided sign test (binomial, p = 0.5) on fixes against breaks."""
    n = fixes + breaks
    if n == 0:
        return 1.0
    k = min(fixes, breaks)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def arm_numbers(arm, ids, gold, task):
    labels = [arm["preds"][i]["label"] for i in ids]
    scores = evaluate.label_scores([gold[i]["label"] for i in ids], labels)
    out = {"cases": len(ids), "macro_f1": round(scores["macro_f1"], 4),
           "neutral_recall": round(scores["per_class"]["neutral"]["recall"], 4),
           "unreadable": sum(1 for i in ids if arm["raws"][i].get("parse_reason")),
           "failed_calls": sum(1 for i in ids if arm["raws"][i].get("error")),
           "input_tokens": round(sum(arm["preds"][i]["metrics"]["input_tokens"] for i in ids) / len(ids), 1),
           "output_tokens": round(sum(arm["preds"][i]["metrics"]["output_tokens"] for i in ids) / len(ids), 1)}
    if task == "A":
        gold_cases = [i for i in ids if gold[i]["label"] in (0, 2) and gold[i].get("reference")]
        found = sum(1 for i in gold_cases
                    if el.evidence_found(arm["preds"][i]["evidence"][:5], el.norm(gold[i]["reference"])))
        out["evidence"] = round(found / len(gold_cases), 4) if gold_cases else None
    return out


def token_rule(new, today, task):
    checks = {"macro_f1 at most 0.005 lower": new["macro_f1"] >= today["macro_f1"] - 0.005 - 1e-9,
              "no more unreadable answers": new["unreadable"] <= today["unreadable"],
              "input tokens at least 10 % lower": new["input_tokens"] <= 0.9 * today["input_tokens"]}
    if task == "A":
        checks["evidence at most 0.010 lower"] = (new["evidence"] or 0) >= (today["evidence"] or 0) - 0.010 - 1e-9
        checks["neutral recall at least 0.98"] = new["neutral_recall"] >= 0.98 - 1e-9
    return checks


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--task", choices=("A", "B"), required=True)
    ap.add_argument("--today", required=True)
    ap.add_argument("--arms", nargs="+", required=True)
    ap.add_argument("--expected", type=Path, required=True)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()
    gold = {g["id"]: g for g in load(args.expected)}
    names = [args.today] + args.arms
    arms = {}
    for name in names:
        preds = {p["id"]: p for p in load(args.run / name / "predictions.jsonl")}
        raws = {r["id"]: r for r in load(args.run / name / "raw_answers.jsonl")}
        arms[name] = {"preds": preds, "raws": raws}
    ids = sorted(i for i in set.intersection(*(set(a["preds"]) for a in arms.values())) if i in gold)
    same = [i for i in ids if len({backend(arms[n]["raws"][i]) for n in names}) == 1]
    result = {"cases": len(ids), "same_backend_cases": len(same),
              "backends": dict(Counter(backend(arms[args.today]["raws"][i]) for i in ids)), "arms": {}}
    for name in names:
        result["arms"][name] = {"all": arm_numbers(arms[name], ids, gold, args.task),
                                "same_backend": arm_numbers(arms[name], same, gold, args.task) if same else None}
    today = result["arms"][args.today]["all"]
    for name in args.arms:
        new = result["arms"][name]["all"]
        right_today = {i for i in ids if arms[args.today]["preds"][i]["label"] == gold[i]["label"]}
        right_new = {i for i in ids if arms[name]["preds"][i]["label"] == gold[i]["label"]}
        fixes, breaks = len(right_new - right_today), len(right_today - right_new)
        result["arms"][name]["token_rule"] = token_rule(new, today, args.task)
        result["arms"][name]["fixes_breaks"] = {"fixes": fixes, "breaks": breaks, "sign_test_p": round(sign_test(fixes, breaks), 4),
                                                "fixed": sorted(right_new - right_today), "broken": sorted(right_today - right_new)}
    print(f"{args.run.name}: {len(ids)} cases, {len(same)} with one backend for all arms; backends {result['backends']}")
    keys = ["macro_f1", "evidence", "neutral_recall", "unreadable", "failed_calls", "input_tokens", "output_tokens"]
    print("| arm | " + " | ".join(keys) + " | same-backend Macro-F1 |")
    for name in names:
        a, s = result["arms"][name]["all"], result["arms"][name]["same_backend"]
        print(f"| {name} | " + " | ".join(str(a.get(k)) for k in keys) + f" | {s['macro_f1'] if s else '-'} |")
    for name in args.arms:
        rule, fb = result["arms"][name]["token_rule"], result["arms"][name]["fixes_breaks"]
        print(f"{name}: TOKEN RULE {'PASS' if all(rule.values()) else 'FAIL'} "
              + "; ".join(f"{k}: {'ok' if v else 'NO'}" for k, v in rule.items())
              + f" | fixes {fb['fixes']}, breaks {fb['breaks']}, p {fb['sign_test_p']}")
    if args.json:
        args.json.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
