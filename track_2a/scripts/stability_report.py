"""Stability points of session 9: the same 600 dev cases, the same image and settings, at different times.

Run from track_2a/ after scoring each point with the starter's evaluate.py (official_score.json in its folder):

    python3 scripts/stability_report.py --points docs/runs/2026-10-09_rashad_stability-1_dev600 [...] \\
        [--json <file>] [--split-task-b]

Per point and task (A, B): the starter's Macro-F1 (and task A's evidence score), unreadable answers, failed
calls, gateway cache hits, mean input tokens, mean and p95 time, and per backend (the answer's
system_fingerprint, as in scripts/interleaved_analysis.py) the calls and the Macro-F1 on its cases.
Between points: how many labels agree, per task, on all cases and on the cases both points' answers came
from the same backend.

--split-task-b writes each point's task B lines (predictions, raw answers, scores) into <point>/task-B/, so
that the point's task B numbers get their own run.json (docs/runs/README.md: one task per run.json).
"""

import argparse
import json
import sys
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from src import evaluate  # noqa: E402
from interleaved_analysis import backend, cache_hit, group_by, load, macro  # noqa: E402

GOLD = ROOT / "data" / "dev" / "expected-labels.jsonl"


def task_numbers(folder, task, gold):
    preds, raws = load(folder / "predictions.jsonl"), load(folder / "raw_answers.jsonl")
    official = json.loads((folder / "official_score.json").read_text(encoding="utf-8"))["tasks"][task]
    ids = [i for i in gold if i.endswith(f"-{task}")]
    cost = evaluate.cost_scores([preds[i] for i in ids])
    out = {
        "cases": len(ids),
        "macro_f1": round(official["macro_f1"], 4),
        "f1": {k: round(v["f1"], 4) for k, v in official["per_class"].items()},
        "unreadable_answers": sum(1 for i in ids if raws[i].get("parse_reason")),
        "failed_calls": sum(1 for i in ids if raws[i].get("error")),
        "gateway_cache_hits": sum(1 for i in ids if cache_hit(raws[i])),
        "mean_input_tokens": round(cost["input_tokens_mean"], 1),
        "mean_output_tokens": round(sum(preds[i]["metrics"]["output_tokens"] for i in ids) / len(ids), 2),
        "mean_time_ms": round(cost["time_ms_mean"]),
        "p95_time_ms": cost["time_ms_p95"],
        "by_backend": {str(b): {"calls": len(sub), "macro_f1": macro(sub, gold, preds)}
                       for b, sub in group_by(ids, lambda i: backend(raws[i])).items()},
    }
    if task == "A":
        out["evidence"] = {"score": round(official["evidence_score"], 4), "found": official["evidence"]["found"],
                           "cases": official["evidence"]["cases"]}
    return out, preds, raws


def agreement(a, b, gold, task):
    (pa, ra), (pb, rb) = a, b
    ids = [i for i in gold if i.endswith(f"-{task}")]
    same_backend = [i for i in ids if backend(ra[i]) == backend(rb[i])]
    agree = lambda sub: sum(1 for i in sub if pa[i]["label"] == pb[i]["label"])  # noqa: E731
    return {"cases": len(ids), "labels_agree": agree(ids), "same_backend_cases": len(same_backend),
            "labels_agree_same_backend": agree(same_backend)}


def split_task_b(folder):
    """<point>/task-B/: the point's task B predictions and raw answers, and its official score (both tasks)."""
    out = folder / "task-B"
    out.mkdir(exist_ok=True)
    for name in ("predictions.jsonl", "raw_answers.jsonl"):
        lines = [l for l in (folder / name).read_text(encoding="utf-8").splitlines()
                 if l.strip() and json.loads(l)["id"].endswith("-B")]
        (out / name).write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "official_score.json").write_text((folder / "official_score.json").read_text(encoding="utf-8"),
                                             encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--points", nargs="+", type=Path, required=True)
    ap.add_argument("--json", type=Path)
    ap.add_argument("--split-task-b", action="store_true")
    args = ap.parse_args()
    gold = {r["id"]: r for r in evaluate.load_jsonl(GOLD)}
    report, loaded = {"points": {}, "agreement": {}}, {}
    for folder in args.points:
        name = folder.name
        report["points"][name] = {}
        for task in ("A", "B"):
            numbers, preds, raws = task_numbers(folder, task, gold)
            report["points"][name][task] = numbers
            loaded[(name, task)] = (preds, raws)
        if args.split_task_b:
            split_task_b(folder)
    for x, y in combinations([f.name for f in args.points], 2):
        report["agreement"][f"{x} vs {y}"] = {task: agreement(loaded[(x, task)], loaded[(y, task)], gold, task)
                                             for task in ("A", "B")}
    if args.json:
        args.json.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
