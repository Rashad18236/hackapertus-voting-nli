"""Session 15, step 5: stability of the final defaults over repeated runs of the same dev cases (no model calls here).

Each run folder holds task-A/ and task-B/ (predictions.jsonl, raw_answers.jsonl, official_score.json from the
starter's evaluate.py), as written by one run of the image on all 600 dev cases. Run from track_2a/:

    python3 scripts/stability.py --runs docs/runs/<run 1> docs/runs/<run 2> docs/runs/<run 3> --out FILE.json

Per run and task: Macro-F1 (the starter's official_score.json) and its 95 % bootstrap interval (scripts/analysis_offline.py's
method: 2,000 resamples of the cases, seed 42), the run's start and end, and the backend identity of its calls (the
endpoint's system_fingerprint and the gateway's x-litellm-model-api-base, from the raw answers, first calls and second looks alike; how many were gateway
cache hits). Over the runs: per task the cases whose label ever changed (ids, with each run's label), and the largest
difference in Macro-F1 between two runs. (scripts/stability_report.py does the same for session 9's points, which ran
both tasks in one container; since session 10 the tasks run in separate containers, task-A/ and task-B/.)
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

from analysis_offline import bootstrap  # noqa: E402

EXPECTED = {"A": "output/devA/expected-labels.jsonl", "B": "output/devB/expected-labels.jsonl"}


def load(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def identities(raws):
    """Backend identity of every call recorded in the raw answers (first answer, A6 and B6 second looks)."""
    found, cache = Counter(), 0
    for raw in raws:
        for call in (raw, raw.get("second_look_a6") or {}, raw.get("second_look_b6") or {}, *raw.get("ap_calls", [])):
            endpoint = call.get("endpoint")
            if not endpoint:
                continue
            host = (endpoint.get("headers") or {}).get("x-litellm-model-api-base", "")
            found[f"{endpoint.get('system_fingerprint')} | {host}"] += 1
            cache += bool(endpoint.get("gateway_cache_hit"))
    return dict(found.most_common()), cache


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = {"runs": {}, "tasks": {}}
    labels = {"A": {}, "B": {}}
    for run in args.runs:
        run = Path(run)
        entry = {}
        for task, expected in EXPECTED.items():
            folder = run / f"task-{task}"
            gold = {e["id"]: e["label"] for e in load(ROOT / expected)}
            preds = {p["id"]: p["label"] for p in load(folder / "predictions.jsonl")}
            ids = sorted(gold)
            official = json.loads((folder / "official_score.json").read_text())["tasks"][task]
            raws = load(folder / "raw_answers.jsonl")
            backends, cache = identities(raws)
            entry[task] = {"macro_f1": round(official["macro_f1"], 4),
                           "bootstrap_95": bootstrap([gold[i] for i in ids], [preds.get(i, -1) for i in ids]),
                           "missing": sum(1 for i in ids if i not in preds),
                           "started_utc": (folder / "started_utc.txt").read_text().strip()
                           if (folder / "started_utc.txt").exists() else None,
                           "ended_utc": (folder / "ended_utc.txt").read_text().strip()
                           if (folder / "ended_utc.txt").exists() else None,
                           "backends": backends, "gateway_cache_hits": cache}
            for i in ids:
                labels[task].setdefault(i, []).append(preds.get(i))
        out["runs"][run.name] = entry
    for task in EXPECTED:
        changed = {i: v for i, v in labels[task].items() if len(set(v)) > 1}
        scores = [out["runs"][r][task]["macro_f1"] for r in out["runs"]]
        out["tasks"][task] = {"cases": len(labels[task]), "labels_ever_changed": len(changed),
                              "changed": changed, "macro_f1_range": round(max(scores) - min(scores), 4)}
    Path(args.out).write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for run, entry in out["runs"].items():
        print(run, {t: (e["macro_f1"], e["bootstrap_95"]["low"], e["bootstrap_95"]["high"], e["backends"])
                    for t, e in entry.items()})
    print({t: {k: v for k, v in e.items() if k != "changed"} for t, e in out["tasks"].items()})


if __name__ == "__main__":
    main()
