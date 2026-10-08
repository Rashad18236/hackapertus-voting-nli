"""Compare the two arms of a paired task A run (no model calls). Run from track_2a/ after scoring both arms.

    python3 scripts/paired_analysis.py --run docs/runs/<comparison> --arms <arm A> <arm B> [--cases output/devA]

Per arm: Macro-F1 and per-label F1 (from the starter's official_score.json),
confusion matrix, evidence score, mean input tokens, median and p95 time,
failed calls and unparseable answers; Macro-F1 and evidence split by claim
type (src/claim_router.py) and by language (claim vs booklet; booklet
language); for a routing arm, how many cases were routed or fell back.
Paired: the cases where one arm was right and the other wrong, overall and
by claim type. Evidence per case uses the starter's rule as re-implemented in
scripts/evidence_loss.py (it gives the official totals). Writes
paired_analysis.json into the run folder.
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
from src import claim_router, evaluate  # noqa: E402


def load(path):
    return {json.loads(l)["id"]: json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--arms", nargs=2, required=True)
    ap.add_argument("--cases", type=Path, default=ROOT / "output" / "devA")
    args = ap.parse_args()

    gold, cases = load(args.cases / "expected-labels.jsonl"), load(args.cases / "cases.jsonl")
    ids = list(cases)
    part = {i: claim_router.route(cases[i]["claim"]["text"]) for i in ids}
    cross = {i: cases[i]["claim"]["language"] != cases[i]["booklet"]["language"] for i in ids}
    gold_norm = {i: el.norm(g["reference"]) for i, g in gold.items() if g["label"] != 1 and g.get("reference")}
    out = {}
    preds, raws = {}, {}
    for arm in args.arms:
        p, r = load(args.run / arm / "predictions.jsonl"), load(args.run / arm / "raw_answers.jsonl")
        preds[arm], raws[arm] = p, r
        official = json.loads((args.run / arm / "official_score.json").read_text(encoding="utf-8"))["tasks"]["A"]
        found = {i: el.evidence_found(p[i]["evidence"], gold_norm[i]) for i in gold_norm}

        def macro(sub):
            return round(evaluate.label_scores([gold[i]["label"] for i in sub], [p[i]["label"] for i in sub])["macro_f1"], 3)

        def evidence(sub):
            sub = [i for i in sub if i in gold_norm]
            return f"{sum(found[i] for i in sub)}/{len(sub)}" if sub else None

        ms = sorted(p[i]["metrics"]["inference_time_ms"] for i in ids)
        tokens = [p[i]["metrics"]["input_tokens"] for i in ids]
        conf = Counter((gold[i]["label"], p[i]["label"]) for i in ids)
        out[arm] = {
            "macro_f1": round(official["macro_f1"], 3),
            "f1": {k: round(v["f1"], 3) for k, v in official["per_class"].items()},
            "evidence": round(official["evidence_score"], 3), "evidence_found": official["evidence"]["found"],
            "evidence_reimplemented": evidence(ids),
            "confusion_rows_gold_E_N_C_cols_pred_E_N_C": [[conf[(g, q)] for q in (0, 1, 2)] for g in (0, 1, 2)],
            "mean_input_tokens": round(sum(tokens) / len(tokens)), "median_ms": ms[len(ms) // 2],
            "p95_ms": ms[math.ceil(0.95 * len(ms)) - 1], "max_ms": ms[-1],
            "failed_calls": sum(1 for i in ids if r[i].get("error")),
            "unparseable": sum(1 for i in ids if r[i].get("parse_reason")),
            "label_0_2_without_evidence": sum(1 for i in ids if p[i]["label"] in (0, 2) and not p[i]["evidence"]),
            "routed": sum(1 for i in ids if r[i].get("route")), "fell_back": sum(1 for i in ids if r[i].get("fallback")),
            "by_part": {k: {"cases": len(sub), "macro_f1": macro(sub), "evidence": evidence(sub)}
                        for k in claim_router.PARTS for sub in [[i for i in ids if part[i] == k]] if sub},
            "by_language": {k: {"cases": len(sub), "macro_f1": macro(sub), "evidence": evidence(sub)}
                            for k, sub in (("same-language", [i for i in ids if not cross[i]]),
                                           ("cross-language", [i for i in ids if cross[i]]))},
            "by_booklet_language": {k: {"cases": len(sub), "macro_f1": macro(sub), "evidence": evidence(sub)}
                                    for k in ("de", "fr", "it")
                                    for sub in [[i for i in ids if cases[i]["booklet"]["language"] == k]]},
        }
    a, b = args.arms
    both = [i for i in ids if not any(raws[x][i].get("error") or raws[x][i].get("parse_reason") for x in (a, b))]

    def outcome(i):
        ra, rb = preds[a][i]["label"] == gold[i]["label"], preds[b][i]["label"] == gold[i]["label"]
        return f"{a} right, {b} wrong" if ra and not rb else f"{b} right, {a} wrong" if rb and not ra \
            else "both right" if ra else "both wrong"

    out["paired"] = {"both_answered": len(both), "counts": dict(Counter(outcome(i) for i in both)),
                     "by_part": {k: dict(Counter(outcome(i) for i in both if part[i] == k)) for k in claim_router.PARTS}}
    (args.run / "paired_analysis.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
