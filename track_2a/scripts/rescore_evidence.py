"""Rebuild a saved task A run's evidence with another evidence setting (no model calls).

Run from track_2a/:

    python3 scripts/rescore_evidence.py --run docs/runs/<comparison>/<arm> --cases output/devA \\
        --evidence-a cited-pieces --out <folder>

Each saved answer is read again with the pipeline's own parser
(nli.parse_label_and_pages); the pages the model was shown come from the run's
raw_answers.jsonl (`context_pages`). Evidence is then built exactly as
src/cli.py builds it, with src/evidence.py and the chosen setting. Labels,
tokens and times are copied unchanged, so only the evidence score can move.
With `--evidence-a cited` the run's own predictions must come out unchanged;
the script stops if a label differs from the saved one. Writes
predictions.jsonl.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import evidence, nli, parse  # noqa: E402


def rebuilt(pred, raw, case, booklets, mode):
    """The prediction with its evidence rebuilt by `mode`; unchanged when the answer had no valid label."""
    if raw.get("error") or raw.get("context_pages") is None or "answer" not in raw:
        return pred
    label, page_numbers, _ = nli.parse_label_and_pages(raw["answer"])
    if label is None:
        return pred
    if label != pred["label"]:
        sys.exit(f"{pred['id']}: re-read label {label} differs from the saved label {pred['label']}")
    if label not in (0, 2):
        return pred
    pages = parse.load_pages(booklets / Path(case["booklet"]["path"]).name)
    shown = {p: pages[p] for p in raw["context_pages"]}
    cited = parse.evidence_items(shown, page_numbers)
    return dict(pred, evidence=evidence.items(mode, cited, shown, case["claim"]["text"], page_numbers))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--cases", type=Path, required=True, help="folder with cases.jsonl")
    ap.add_argument("--booklets", type=Path, default=ROOT / "output" / "booklets_dev")
    ap.add_argument("--evidence-a", choices=evidence.MODES, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    load = lambda p: [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]  # noqa: E731
    cases = {c["id"]: c for c in load(args.cases / "cases.jsonl")}
    raws = {r["id"]: r for r in load(args.run / "raw_answers.jsonl")}
    out = [rebuilt(p, raws[p["id"]], cases[p["id"]], args.booklets, args.evidence_a)
           for p in load(args.run / "predictions.jsonl")]
    changed = sum(new != old for new, old in zip(out, load(args.run / "predictions.jsonl")))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "predictions.jsonl").write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in out),
                                                encoding="utf-8")
    print(f"{args.evidence_a}: {len(out)} predictions, evidence changed in {changed}")


if __name__ == "__main__":
    main()
