"""Session 13: the numbers the PAIRED RULE needs for every arm of one interleaved run, against its arm "today".

Run from track_2a/ after scoring each arm with the starter's evaluate.py (official_score.json in each arm's folder):

    python3 scripts/arm_table.py --run docs/runs/<folder> --task A --expected output/devA/expected-labels.jsonl \\
        --today today --arms A1-says A2-residual ... [--ontopic data/ontopic_neutral/expected-labels.jsonl] \\
        [--focus docs/runs/2026-10-13_rashad_final-s12_val1160/task-A] [--cases CASES.jsonl] --out FILE.json

Per arm, on the cases of --expected only (an on-topic case is scored only in its own row):
Macro-F1 and per-label F1 (the starter's official_score.json), evidence (task A), mean input and output tokens per
case (response metrics: all calls of the case), unreadable answers (raw answers with a parse_reason), failed calls,
fixes and breaks against "today" with a one-sided sign test (exact binomial; the two-sided p too), the error row the session follows
(task A: gold contradiction answered neutral; task B: gold neutral answered contradiction, split by whether claim and
reference share a language, from --cases), the on-topic neutral share (--ontopic), A6's second looks
(raw "second_look_a6") and, with --focus, which of session 12's errors of that kind (answered neutral in task A,
answered contradiction in task B) the arm fixes and which new ones it makes.
"""

import argparse
import json
import math
from pathlib import Path


def load(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def sign_test(fixes, breaks):
    """One-sided exact binomial p-value of at least `fixes` successes in fixes + breaks trials at p = 0.5."""
    n = fixes + breaks
    if n == 0:
        return 1.0
    return sum(math.comb(n, k) for k in range(fixes, n + 1)) / 2 ** n


def arm_numbers(folder, task, gold, today_pred, ontopic, focus, languages):
    preds = {p["id"]: p for p in load(folder / "predictions.jsonl")}
    raws = {}
    for r in load(folder / "raw_answers.jsonl"):
        raws[r["id"]] = r
    official = json.loads((folder / "official_score.json").read_text())["tasks"][task]
    ids = [i for i in gold if i in preds]
    out = {"cases": len(ids), "macro_f1": round(official["macro_f1"], 4),
           "f1": {k: round(v["f1"], 4) for k, v in official["per_class"].items()}}
    if task == "A":
        out["evidence"] = {"score": round(official["evidence_score"], 4), "found": official["evidence"]["found"],
                           "cases": official["evidence"]["cases"]}
    out["input_tokens"] = round(sum(preds[i]["metrics"]["input_tokens"] for i in ids) / len(ids), 1)
    out["output_tokens"] = round(sum(preds[i]["metrics"]["output_tokens"] for i in ids) / len(ids), 1)
    out["unreadable"] = sum(1 for i in ids if raws.get(i, {}).get("parse_reason"))
    out["failed_calls"] = sum(1 for i in ids if raws.get(i, {}).get("error"))
    wrong_from, wrong_to = (2, 1) if task == "A" else (1, 2)
    row = [i for i in ids if gold[i] == wrong_from and preds[i]["label"] == wrong_to]
    out["error_row"] = {"name": ("gold contradiction answered neutral" if task == "A"
                                 else "gold neutral answered contradiction"), "count": len(row)}
    if languages:
        same = sum(1 for i in row if languages.get(i))
        out["error_row"].update(same_language=same, cross_language=len(row) - same)
    if today_pred is not None:
        fixes = [i for i in ids if today_pred[i]["label"] != gold[i] and preds[i]["label"] == gold[i]]
        breaks = [i for i in ids if today_pred[i]["label"] == gold[i] and preds[i]["label"] != gold[i]]
        one = sign_test(len(fixes), len(breaks))
        two = min(1.0, 2 * min(one, sign_test(len(breaks), len(fixes))))
        out.update(fixes=len(fixes), breaks=len(breaks), sign_test_p=round(one, 4), sign_test_p_two_sided=round(two, 4),
                   fix_ids=fixes, break_ids=breaks)
    if ontopic:
        on = [i for i in ontopic if i in preds]
        out["ontopic"] = {"cases": len(on), "neutral": sum(1 for i in on if preds[i]["label"] == 1)}
        out["ontopic"]["share"] = round(out["ontopic"]["neutral"] / len(on), 4) if on else None
        out["ontopic"]["not_neutral_ids"] = [i for i in on if preds[i]["label"] != 1]
    looks = [raws[i]["second_look_a6"] for i in raws if "second_look_a6" in raws[i]]
    if looks:
        scope = [i for i in ids if "second_look_a6" in raws.get(i, {})]
        out["second_look_a6"] = {"calls": len(looks), "calls_on_scored_cases": len(scope),
                                 "per_100_cases": round(100 * len(scope) / len(ids), 2),
                                 "unreadable": sum(1 for x in looks if x.get("parse_reason")),
                                 "failed": sum(1 for x in looks if x.get("error")),
                                 "changed": sum(1 for i in scope if preds[i]["label"] != 1),
                                 "fixes": sum(1 for i in scope if preds[i]["label"] != 1 and preds[i]["label"] == gold[i]),
                                 "breaks": sum(1 for i in scope if preds[i]["label"] != 1 and gold[i] == 1)}
    if focus is not None:
        before = {i for i in ids if i in focus and focus[i]["label"] != gold[i] and focus[i]["label"] == wrong_to}
        now = {i for i in ids if preds[i]["label"] != gold[i] and preds[i]["label"] == wrong_to}
        out["focus"] = {"session_12": len(before), "fixed": sorted(i for i in before if preds[i]["label"] == gold[i]),
                        "still_wrong": sorted(before & now), "new": sorted(now - before)}
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--run", required=True)
    parser.add_argument("--task", choices=["A", "B"], required=True)
    parser.add_argument("--expected", required=True)
    parser.add_argument("--today", default="today")
    parser.add_argument("--arms", nargs="+", required=True)
    parser.add_argument("--ontopic")
    parser.add_argument("--focus", help="folder with session 12's predictions.jsonl of the same cases")
    parser.add_argument("--cases", help="cases.jsonl, for the same-/cross-language split (task B)")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    run = Path(args.run)
    gold = {e["id"]: e["label"] for e in load(args.expected) if e["id"].endswith(f"-{args.task}")}
    ontopic = [e["id"] for e in load(args.ontopic)] if args.ontopic else None
    focus = {p["id"]: p for p in load(Path(args.focus) / "predictions.jsonl")} if args.focus else None
    languages = None
    if args.cases:
        languages = {c["id"]: c["claim"].get("language") == (c.get("reference") or c.get("booklet") or {}).get("language")
                     for c in load(args.cases)}
    today_pred = {p["id"]: p for p in load(run / args.today / "predictions.jsonl")}
    table = {"run": str(run), "task": args.task, "expected": args.expected, "today": args.today, "arms": {}}
    for arm in [args.today] + [a for a in args.arms if a != args.today]:
        table["arms"][arm] = arm_numbers(run / arm, args.task, gold, None if arm == args.today else today_pred,
                                         ontopic, focus, languages)
        a = table["arms"][arm]
        print(f"{arm:16s} F1 {a['macro_f1']:.4f}  ev {a.get('evidence', {}).get('score', '-')}  "
              f"in {a['input_tokens']} out {a['output_tokens']}  unread {a['unreadable']}  "
              f"row {a['error_row']['count']}  fix/break {a.get('fixes', '-')}/{a.get('breaks', '-')} "
              f"p {a.get('sign_test_p', '-')}  ontopic {a.get('ontopic', {}).get('neutral', '-')}"
              + (f"  A6 {a['second_look_a6']}" if "second_look_a6" in a else "")
              + (f"  focus fixed {len(a['focus']['fixed'])}/{a['focus']['session_12']} new {len(a['focus']['new'])}"
                 if "focus" in a else ""))
    Path(args.out).write_text(json.dumps(table, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
