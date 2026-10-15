"""Session 16, step 1e: the sealed run's numbers, pooled and per voting date (no model calls).

Run from track_2a/ after the run (both tasks) and its local-time measurements:

    python3 scripts/sealed_report.py --run docs/runs/2026-10-15_rashad_sealed-once --starter <starter checkout>

Reads data/sealed/cases.jsonl and expected-labels.jsonl, and the run's task-A/ and task-B/ (predictions.jsonl,
raw_answers.jsonl). Per date (a task B case's date is its row's task A booklet date) and pooled, per task: the
starter's evaluate.py on that subset (Macro-F1, per-label F1, evidence for task A), cases, mean input and output tokens
per case, Python-written labels (neutral fallbacks: a raw answer with an error or an unreadable answer), failed calls,
backend identity and gateway cache hits of every call, A6 second looks, task A paths (`scripts/prompt_snapshot.py`'s
path_taken) and AP-translate calls; local time per case at 1.0 and 0.3 s per request from
<run>/local_time/<scope>_<task>_d<delay>/local_time.json when present, and REF SCORE (scripts/official_score.py).
The error list holds ids, gold and answered labels and the path only (no booklet text). Writes <run>/sealed_report.json.
"""

import argparse
import json
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import official_score as os_  # noqa: E402
from prompt_snapshot import path_taken  # noqa: E402

NAMES = {0: "entailment", 1: "neutral", 2: "contradiction"}


def load(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def starter_score(starter, preds, expected):
    """The starter's evaluate.py on one subset; returns its JSON."""
    with tempfile.TemporaryDirectory() as d:
        p, e, j = Path(d) / "p.jsonl", Path(d) / "e.jsonl", Path(d) / "s.json"
        p.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in preds), encoding="utf-8")
        e.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in expected), encoding="utf-8")
        subprocess.run(["uv", "run", "--no-sync", "python", "evaluate.py", "--predictions", str(p), "--expected",
                        str(e), "--json", str(j)], cwd=starter, check=True, capture_output=True)
        return json.loads(j.read_text())


def calls_of(raw):
    """Every model call recorded in one raw answer: (kind, call dict)."""
    out = [("answer", raw)] if ("answer" in raw or "error" in raw) else []
    out += [("ap", c) for c in raw.get("ap_calls", [])]
    if raw.get("second_look_a6"):
        out.append(("a6", raw["second_look_a6"]))
    return out


def task_numbers(task, ids, preds, raws, gold, starter, expected_rows):
    official = starter_score(starter, [preds[i] for i in ids], [expected_rows[i] for i in ids])["tasks"][task]
    calls = [c for i in ids for c in calls_of(raws[i])]
    backends = Counter()
    for _, c in calls:
        e = c.get("endpoint") or {}
        if e:
            backends[f"{(e.get('headers') or {}).get('x-litellm-model-api-base', '?')} | {e.get('system_fingerprint')}"] += 1
    out = {"cases": len(ids), "macro_f1": round(official["macro_f1"], 4),
           "f1": {k: round(v["f1"], 4) for k, v in official["per_class"].items()},
           "input_tokens": round(sum(preds[i]["metrics"]["input_tokens"] for i in ids) / len(ids), 1),
           "output_tokens": round(sum(preds[i]["metrics"]["output_tokens"] for i in ids) / len(ids), 1),
           "python_labels": sum(1 for i in ids if raws[i].get("error") or raws[i].get("parse_reason")),
           "failed_calls": sum(1 for _, c in calls if c.get("error")),
           "calls": len(calls), "backends": dict(backends),
           "cache_hits": sum(1 for _, c in calls if (c.get("endpoint") or {}).get("gateway_cache_hit"))}
    if task == "A":
        out["evidence"] = round(official["evidence_score"], 4)
        out["evidence_found"] = f"{official['evidence']['found']} of {official['evidence']['cases']}"
        out["a6_second_looks"] = sum(1 for i in ids if raws[i].get("second_look_a6"))
        out["a6_changed"] = sum(1 for i in ids if raws[i].get("second_look_a6") and preds[i]["label"] != 1)
        out["paths"] = dict(Counter(path_taken(raws[i]) for i in ids).most_common())
        out["ap_calls"] = dict(Counter(c.get("version", "?") for i in ids for c in raws[i].get("ap_calls", [])))
    out["errors"] = [{"id": i, "gold": NAMES[gold[i]], "answer": preds[i]["label_name"], "path": path_taken(raws[i])}
                     for i in ids if preds[i]["label"] != gold[i]]
    return out


def local_time(run, scope, task, delay):
    f = run / "local_time" / f"{scope}_{task}_d{delay}" / "local_time.json"
    return json.loads(f.read_text())["local_per_case_s"] if f.exists() else None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--run", required=True)
    ap.add_argument("--starter", required=True)
    args = ap.parse_args()
    run = Path(args.run)
    cases = {c["id"]: c for c in load(ROOT / "data" / "sealed" / "cases.jsonl")}
    expected_rows = {e["id"]: e for e in load(ROOT / "data" / "sealed" / "expected-labels.jsonl")}
    gold = {i: e["label"] for i, e in expected_rows.items()}
    row_date = {i.rsplit("-", 1)[0]: c["booklet"]["path"].split("/")[1][:10].replace("_", "-")
                for i, c in cases.items() if "booklet" in c}
    date = {i: row_date[i.rsplit("-", 1)[0]] for i in cases}
    report = {"run": str(run), "scopes": {}}
    for scope in ["pooled"] + sorted(set(date.values())):
        entry = {}
        for task in "AB":
            preds = {p["id"]: p for p in load(run / f"task-{task}" / "predictions.jsonl")}
            raws = {r["id"]: r for r in load(run / f"task-{task}" / "raw_answers.jsonl")}
            ids = sorted(i for i in cases if i.endswith(f"-{task}") and (scope == "pooled" or date[i] == scope))
            entry[task] = task_numbers(task, ids, preds, raws, gold, args.starter, expected_rows)
            entry[task]["local_time_s"] = {d: local_time(run, scope, task, d) for d in ("1.0", "0.3")}
        ref = {}
        for d in ("1.0", "0.3"):
            ta, tb = entry["A"]["local_time_s"][d], entry["B"]["local_time_s"][d]
            if ta is None or tb is None:
                continue
            a = os_.task_score("A", entry["A"]["macro_f1"], entry["A"]["input_tokens"] + entry["A"]["output_tokens"],
                               ta, entry["A"]["evidence"])
            b = os_.task_score("B", entry["B"]["macro_f1"], entry["B"]["input_tokens"] + entry["B"]["output_tokens"], tb)
            ref[d] = {"A": a, "B": b, "score": os_.total(a, b)}
        entry["ref_score"] = ref
        report["scopes"][scope] = entry
    (run / "sealed_report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for scope, e in report["scopes"].items():
        a, b = e["A"], e["B"]
        print(f"{scope:10s} A {a['cases']} F1 {a['macro_f1']:.4f} ev {a['evidence']:.4f} tok {a['input_tokens']}+{a['output_tokens']} "
              f"py {a['python_labels']} fail {a['failed_calls']} cache {a['cache_hits']} a6 {a['a6_second_looks']} | "
              f"B {b['cases']} F1 {b['macro_f1']:.4f} tok {b['input_tokens']}+{b['output_tokens']} py {b['python_labels']} "
              f"fail {b['failed_calls']} | REF {({d: v['score'] for d, v in e['ref_score'].items()})}")


if __name__ == "__main__":
    main()
