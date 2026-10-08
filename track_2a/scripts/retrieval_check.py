"""Measure task A context selection offline: no model endpoint, no tokens.

Run from track_2a/ (after scripts/fetch_dev_booklets.py, with the model in models/):

    EMBED_MODEL_DIR=models/multilingual-e5-small python3 scripts/retrieval_check.py

For every dev task A case with a gold passage (labels 0 and 2), select chunks
as the pipeline does (src/context.py) and report:

- hit@k: share of cases where at least one selected chunk lies inside the gold
  passage (rapidfuzz partial_ratio of chunk vs gold >= 90). The gold passages
  are whole sections, longer than a chunk.
- evidence ceiling: share of cases where at least one selected page's text
  would pass the evidence check (partial_ratio of gold vs page text >= 90).
  This is the best evidence score a model could reach by citing selected pages.
  The same number for all pages is the full-document ceiling.
- mean characters sent: selected excerpts vs whole booklet, a proxy for input tokens.

Normalisation follows the starter's description (case, whitespace, line-break
hyphenation); this is our re-implementation, so the official scorer decides.
"""

import argparse
import json
import re
import sys
from pathlib import Path

from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import context, parse  # noqa: E402

THRESHOLD = 90


def passes(a, b):
    """partial_ratio(a, b) >= THRESHOLD; score_cutoff lets rapidfuzz stop early on long texts."""
    return fuzz.partial_ratio(a, b, score_cutoff=THRESHOLD) >= THRESHOLD


def normalise(text):
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)  # join words hyphenated at a line break
    return re.sub(r"\s+", " ", text).strip().lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--booklets", type=Path, default=ROOT / "output" / "booklets_dev")
    ap.add_argument("--top-k", type=int, default=context.TOP_K)
    ap.add_argument("--output", type=Path, help="optional JSONL with per-case results")
    args = ap.parse_args()

    gold = {}
    for line in (ROOT / "data" / "dev" / "expected-labels.jsonl").read_text(encoding="utf-8").splitlines():
        g = json.loads(line)
        if g["id"].endswith("-A") and g["label"] in (0, 2) and g.get("reference"):
            gold[g["id"]] = g["reference"]
    cases = [json.loads(line) for line in (ROOT / "data" / "dev" / "cases.jsonl").read_text(encoding="utf-8").splitlines()]
    cases = [c for c in cases if c["id"] in gold]

    rows = []
    for i, case in enumerate(cases, start=1):
        pages = parse.load_pages(args.booklets / Path(case["booklet"]["path"]).name)
        chunks = context.select_chunks(pages, case["claim"]["text"], top_k=args.top_k)
        g = normalise(gold[case["id"]])
        selected_pages = sorted({n for n, _ in chunks})
        selected_page_ok = any(passes(g, normalise(pages[n])) for n in selected_pages)
        rows.append({
            "id": case["id"],
            "hit": any(passes(normalise(text), g) for _, text in chunks),
            "selected_page_ok": selected_page_ok,
            "any_page_ok": selected_page_ok or any(passes(g, normalise(pages[n])) for n in pages if n not in selected_pages),
            "selected_pages": selected_pages,
            "chars_selected": len(context.excerpts_prompt_text(chunks)),
            "chars_full": len(parse.booklet_prompt_text(pages)),
        })
        if i % 20 == 0:
            print(f"{i}/{len(cases)}", file=sys.stderr)

    n = len(rows)
    share = lambda key: sum(r[key] for r in rows) / n  # noqa: E731
    print(f"cases with a gold passage: {n}, top_k {args.top_k}, chunk {context.CHUNK_CHARS} chars")
    print(f"hit@{args.top_k} (a selected chunk lies in the gold passage): {share('hit'):.3f}")
    print(f"evidence ceiling, selected pages: {share('selected_page_ok'):.3f}")
    print(f"evidence ceiling, all pages (full document): {share('any_page_ok'):.3f}")
    print(f"mean chars sent: selected {sum(r['chars_selected'] for r in rows) / n:.0f}, "
          f"full {sum(r['chars_full'] for r in rows) / n:.0f}")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


if __name__ == "__main__":
    main()
