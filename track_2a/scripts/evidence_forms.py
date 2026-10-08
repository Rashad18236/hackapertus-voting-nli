"""Re-score a saved embed-e5-small run with another evidence item form for the same cited pages (no model calls).

Run from track_2a/ (after `scripts/retrieval_check.py --fill-cache`):

    EMBED_MODEL_DIR=models/multilingual-e5-small python3 scripts/evidence_forms.py \\
        --run docs/runs/<comparison>/embed-e5-small --cases output/devA --out <folder> --form b

The pages stay exactly the pages the answer cited (its evidence pages); no
page is changed or added. Only the text of each item changes:

  a  the whole page, split at 5,000 characters (the pipeline today);
  b  the chunks of that page that were sent to Apertus, joined, cut at 5,000 characters;
  c  those chunks plus the neighbouring chunk on each side on the same page, joined, cut at 5,000.

The chunks are rebuilt with embed-e5-small's own code (deterministic; the
script stops if their pages differ from the pages the run recorded). Labels,
tokens and times are copied unchanged. Writes predictions.jsonl.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import evidence_loss as el  # noqa: E402
import retrieval_check as rc  # noqa: E402
from src import parse  # noqa: E402
from src.contexts import embed_e5_small  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--cases", type=Path, required=True)
    ap.add_argument("--booklets", type=Path, default=ROOT / "output" / "booklets_dev")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--form", choices=("a", "b", "c"), required=True)
    args = ap.parse_args()

    rc.load_cache()
    load = lambda p: [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]  # noqa: E731
    cases = {c["id"]: c for c in load(args.cases / "cases.jsonl")}
    raws = {r["id"]: r for r in load(args.run / "raw_answers.jsonl")}
    out, changed = [], 0
    for pred in load(args.run / "predictions.jsonl"):
        new = dict(pred)
        if pred["evidence"]:
            case = cases[pred["id"]]
            pages = parse.load_pages(args.booklets / Path(case["booklet"]["path"]).name)
            sent_chunks = embed_e5_small.select_chunks(pages, case["claim"]["text"])
            if sorted({p for p, _ in sent_chunks}) != raws[pred["id"]].get("context_pages"):
                sys.exit(f"{pred['id']}: rebuilt chunks differ from the run's pages")
            cited_pages = list(dict.fromkeys(it["page"] for it in pred["evidence"]))
            new["evidence"] = el.evidence_for(args.form, pages, cited_pages, sent_chunks)
        changed += new["evidence"] != pred["evidence"]
        out.append(new)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "predictions.jsonl").write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in out), encoding="utf-8")
    print(f"form {args.form}: {len(out)} predictions, evidence changed in {changed}")


if __name__ == "__main__":
    main()
