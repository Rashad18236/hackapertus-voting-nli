"""Task B confirmation: compare two runs of the same prompt, and list the first run's errors.

Run from track_2a/ after scoring both runs with the starter's evaluate.py:

    python3 scripts/taskb_analysis.py --runs docs/runs/<run 1> docs/runs/<run 2> \\
        [--intro docs/taskb_errors_intro.md] --errors docs/taskb_errors.md --out <folder>

Per run: Macro-F1 and per-label F1 (official_score.json, starter's scorer),
failed calls and unreadable answers (raw_answers.jsonl). Between the runs: the
cases whose labels differ, and the Macro-F1 gap (the noise floor of a rerun).
For the first run: the confusion matrix; Macro-F1 by claim language, by passage
language, and same-language against cross-language, with case counts; every
wrong case, grouped by error pattern, written to --errors (id, languages, gold,
predicted, claim, first 300 characters of the passage). --intro is markdown
placed at the top of that file (the patterns described in plain words).
Writes analysis.json to --out.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import evaluate  # noqa: E402

NAMES = {0: "entailment", 1: "neutral", 2: "contradiction"}
# (gold, predicted) -> the error pattern in plain words
PATTERNS = {
    (0, 1): "Supported claim called neutral: the passage supports the claim, the model said it does not decide it.",
    (0, 2): "Supported claim called a contradiction: the passage supports the claim, the model said it refutes it.",
    (1, 0): "Unrelated claim called entailed: the passage does not decide the claim, the model said it supports it.",
    (1, 2): "Unrelated claim called a contradiction: the passage does not decide the claim, the model said it refutes it.",
    (2, 0): "Refuted claim called entailed: the passage refutes the claim, the model said it supports it.",
    (2, 1): "Refuted claim called neutral: the passage refutes the claim, the model said it does not decide it.",
}


def load(path):
    return {json.loads(l)["id"]: json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()}


def macro(ids, gold, pred):
    return round(evaluate.label_scores([gold[i]["label"] for i in ids], [pred[i]["label"] for i in ids])["macro_f1"], 3)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", nargs=2, type=Path, required=True)
    ap.add_argument("--cases", type=Path, default=ROOT / "output" / "devB")
    ap.add_argument("--intro", type=Path)
    ap.add_argument("--errors", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    cases, gold = load(args.cases / "cases.jsonl"), load(args.cases / "expected-labels.jsonl")
    ids = list(cases)
    out, preds, raws = {"runs": {}}, [], []
    for run in args.runs:
        p, r = load(run / "predictions.jsonl"), load(run / "raw_answers.jsonl")
        preds.append(p)
        raws.append(r)
        official = json.loads((run / "official_score.json").read_text(encoding="utf-8"))["tasks"]["B"]
        out["runs"][run.name] = {
            "macro_f1": round(official["macro_f1"], 4),
            "f1": {k: round(v["f1"], 3) for k, v in official["per_class"].items()},
            "failed_calls": sum(1 for i in ids if r[i].get("error")),
            "unreadable_answers": sum(1 for i in ids if r[i].get("parse_reason")),
        }
    differ = [i for i in ids if preds[0][i]["label"] != preds[1][i]["label"]]
    f1s = [v["macro_f1"] for v in out["runs"].values()]
    out["between_runs"] = {"labels_differ": len(differ), "ids": differ,
                           "transitions": dict(Counter(f"{NAMES[preds[0][i]['label']]} -> {NAMES[preds[1][i]['label']]}"
                                                       for i in differ)),
                           "macro_f1_gap": round(abs(f1s[0] - f1s[1]), 4)}

    p1, r1 = preds[0], raws[0]
    conf = Counter((gold[i]["label"], p1[i]["label"]) for i in ids)
    out["first_run"] = {"confusion_rows_gold_E_N_C_cols_pred_E_N_C": [[conf[(g, q)] for q in (0, 1, 2)] for g in (0, 1, 2)]}
    groups = {}
    for lang in ("de", "fr", "it"):
        groups[f"claim {lang}"] = [i for i in ids if cases[i]["claim"]["language"] == lang]
    for lang in ("de", "fr", "it"):
        groups[f"passage {lang}"] = [i for i in ids if cases[i]["reference"]["language"] == lang]
    groups["same-language"] = [i for i in ids if cases[i]["claim"]["language"] == cases[i]["reference"]["language"]]
    groups["cross-language"] = [i for i in ids if cases[i]["claim"]["language"] != cases[i]["reference"]["language"]]
    out["first_run"]["by_group"] = {k: {"cases": len(v), "macro_f1": macro(v, gold, p1)} for k, v in groups.items()}

    wrong = [i for i in ids if p1[i]["label"] != gold[i]["label"]]
    lines = ["<!-- Written by scripts/taskb_analysis.py; the introduction comes from --intro. -->", ""]
    if args.intro:
        lines += [args.intro.read_text(encoding="utf-8").rstrip(), ""]
    lines += [f"## Every wrong case of `{args.runs[0].name}` ({len(wrong)} of {len(ids)})", ""]
    by_pattern = {}
    for i in wrong:
        g, q = gold[i]["label"], p1[i]["label"]
        key = PATTERNS[(g, q)]
        if r1[i].get("error") or r1[i].get("parse_reason"):
            key = "No usable answer (failed call or unreadable answer): the fallback label neutral was written."
        by_pattern.setdefault(key, []).append(i)
    out["first_run"]["errors_by_pattern"] = {k: len(v) for k, v in by_pattern.items()}
    for pattern, members in sorted(by_pattern.items(), key=lambda kv: -len(kv[1])):
        lines += [f"### {pattern} ({len(members)})", ""]
        for i in members:
            c = cases[i]
            passage = " ".join(c["reference"]["text"][:300].split())
            lines += [f"- **`{i}`**: passage {c['reference']['language']}, claim {c['claim']['language']}; "
                      f"gold {NAMES[gold[i]['label']]}, predicted {NAMES[p1[i]['label']]}",
                      f"  - Claim: {c['claim']['text']}",
                      f"  - Passage (first 300 characters): {passage}"]
        lines.append("")
    args.errors.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "analysis.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items()}, indent=1, ensure_ascii=False)[:4000])


if __name__ == "__main__":
    main()
