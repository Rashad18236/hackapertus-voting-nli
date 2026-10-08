"""Why was a task A answer wrong: did the search miss the gold passage, or did the model misread it?

Run from track_2a/ after `scripts/retrieval_check.py --fill-cache` (no model calls):

    EMBED_MODEL_DIR=models/multilingual-e5-small python3 scripts/search_or_reading.py \\
        --run docs/runs/<comparison>/embed-e5-small --cases output/devA --out <folder>

For every case of an embed-e5-small arm, the chunks the model saw are rebuilt
with the variant's own code (they are deterministic; the script checks that
their pages equal the pages recorded in raw_answers.jsonl). Then, for every
wrong answer (a failed call is counted apart):

- gold entailment or contradiction: a *search miss* if no chunk sent matches
  the gold passage (the hit rule of scripts/retrieval_check.py), otherwise a
  *reading error* (the passage was there, the label is still wrong);
- gold neutral: there is no gold passage to find, so every wrong answer is a
  reading error (the model found support or contradiction the source does not give).

Counts are split by gold label and by same-language / cross-language (claim
language against booklet language). Writes summary.json and per_case.jsonl.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import retrieval_check as rc  # noqa: E402
from src import parse  # noqa: E402
from src.contexts import embed_e5_small  # noqa: E402

LABEL = {0: "entailment", 1: "neutral", 2: "contradiction"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True, help="an embed-e5-small arm folder")
    ap.add_argument("--cases", type=Path, required=True, help="folder with cases.jsonl and expected-labels.jsonl")
    ap.add_argument("--booklets", type=Path, default=ROOT / "output" / "booklets_dev")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    rc.load_cache()
    load = lambda p: {json.loads(l)["id"]: json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()}  # noqa: E731
    cases, gold = load(args.cases / "cases.jsonl"), load(args.cases / "expected-labels.jsonl")
    preds, raws = load(args.run / "predictions.jsonl"), load(args.run / "raw_answers.jsonl")
    scorer = rc.Scorer()

    rows, page_mismatch = [], 0
    for cid, case in cases.items():
        pages = parse.load_pages(args.booklets / Path(case["booklet"]["path"]).name)
        chunks = embed_e5_small.select_chunks(pages, case["claim"]["text"])
        sent_pages = sorted({p for p, _ in chunks})
        if raws[cid].get("context_pages") is not None and raws[cid]["context_pages"] != sent_pages:
            page_mismatch += 1
        g = gold[cid]["label"]
        row = {"id": cid, "gold": LABEL[g], "pred": LABEL[preds[cid]["label"]], "cross": rc.cross(case),
               "failed_call": bool(raws[cid].get("error")), "sent_pages": sent_pages}
        if g in (0, 2):
            passage = rc.normalise(gold[cid]["reference"])
            row["hit"] = any(scorer.match(cid, passage, t) for _, t in chunks)
            row["gold_page_sent"] = any(scorer.page_ok(cid, passage, pages[p]) for p in sent_pages)
        row["correct"] = preds[cid]["label"] == g
        if row["failed_call"]:
            row["kind"] = "failed call"
        elif row["correct"]:
            row["kind"] = "correct"
        elif g == 1:
            row["kind"] = "reading error (gold neutral)"
        else:
            row["kind"] = "reading error" if row["hit"] else "search miss"
        rows.append(row)

    def counts(subset):
        c = Counter(r["kind"] for r in subset)
        return {k: c.get(k, 0) for k in ("correct", "search miss", "reading error", "reading error (gold neutral)", "failed call")}

    summary = {"cases": len(rows), "pages_differ_from_run": page_mismatch, "all": counts(rows), "by_gold": {}, "by_language": {},
               "by_gold_and_language": {}}
    for lab in LABEL.values():
        summary["by_gold"][lab] = counts([r for r in rows if r["gold"] == lab])
    for name, flag in (("same-language", False), ("cross-language", True)):
        summary["by_language"][name] = counts([r for r in rows if r["cross"] == flag])
        for lab in ("entailment", "contradiction"):
            summary["by_gold_and_language"][f"{lab}, {name}"] = counts([r for r in rows if r["gold"] == lab and r["cross"] == flag])
    gold_rows = [r for r in rows if "hit" in r]
    summary["hit_rate"] = {
        "all gold E/C cases": sum(r["hit"] for r in gold_rows) / len(gold_rows),
        "correct answers": sum(r["hit"] for r in gold_rows if r["kind"] == "correct") / max(1, sum(r["kind"] == "correct" for r in gold_rows)),
        "wrong answers": sum(r["hit"] for r in gold_rows if r["kind"] in ("search miss", "reading error"))
        / max(1, sum(r["kind"] in ("search miss", "reading error") for r in gold_rows)),
    }
    wrong_ec = [r for r in gold_rows if r["kind"] in ("search miss", "reading error")]
    summary["wrong_gold_ec_by_pred"] = dict(Counter(f"{r['kind']}: gold {r['gold']} -> {r['pred']}" for r in wrong_ec))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    (args.out / "per_case.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
