"""Re-score a saved task A run with the evidence setting "cited-then-retrieved" (no model calls).

Run from track_2a/ after `scripts/retrieval_check.py --fill-cache`:

    EMBED_MODEL_DIR=models/multilingual-e5-small python3 scripts/pad_evidence.py \\
        --run docs/runs/<comparison>/<arm> --cases output/devA --out <folder> [--all-labels]

The pages the model was shown come from the run's raw_answers.jsonl
(`context_pages`); the cited items are the run's own evidence. Evidence is
rebuilt with src/evidence.py for answers with label 0 or 2. With --all-labels,
label-1 answers get padded evidence too (cited pages from the raw answer,
then the retrieved pages); that is for information only, the pipeline never
does it. Failed calls keep no evidence. Labels, tokens and times are copied
unchanged, so only the evidence score can move. Writes predictions.jsonl.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import retrieval_check as rc  # noqa: E402
from src import evidence, nli, parse  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--cases", type=Path, required=True, help="folder with cases.jsonl")
    ap.add_argument("--booklets", type=Path, default=ROOT / "output" / "booklets_dev")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--all-labels", action="store_true", help="also pad label-1 answers (information only)")
    args = ap.parse_args()

    rc.load_cache()
    load = lambda p: [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]  # noqa: E731
    cases = {c["id"]: c for c in load(args.cases / "cases.jsonl")}
    raws = {r["id"]: r for r in load(args.run / "raw_answers.jsonl")}
    out, changed = [], 0
    for pred in load(args.run / "predictions.jsonl"):
        raw, case = raws[pred["id"]], cases[pred["id"]]
        new = dict(pred)
        if not raw.get("error") and raw.get("context_pages") is not None:
            pages = parse.load_pages(args.booklets / Path(case["booklet"]["path"]).name)
            shown = {p: pages[p] for p in raw["context_pages"]}
            if pred["label"] in (0, 2):
                new["evidence"] = evidence.items("cited-then-retrieved", pred["evidence"], shown, case["claim"]["text"])
            elif args.all_labels:
                _, cited_pages, _ = nli.parse_label_and_pages(raw.get("answer", ""))
                cited = parse.evidence_items(shown, cited_pages or [])
                new["evidence"] = evidence.items("cited-then-retrieved", cited, shown, case["claim"]["text"])
        changed += new["evidence"] != pred["evidence"]
        out.append(new)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "predictions.jsonl").write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in out), encoding="utf-8")
    print(f"{len(out)} predictions, evidence changed in {changed}; written to {args.out / 'predictions.jsonl'}")


if __name__ == "__main__":
    main()
