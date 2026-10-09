"""How much faster would section-route's long parts embed with length-sorted batches? (no model calls)

Run from track_2a/ (dev booklets; e5 files as in the Dockerfile):

    EMBED_MODEL_DIR=models/multilingual-e5-small python3 scripts/embed_batching_check.py [--cases ID ...]

For each case (default: the four slowest routed cases of session 6's E5, all law parts with 385 to 636
paragraphs), the part's paragraphs are embedded twice with the pipeline's own E5Embedder
(src/contexts/embed_e5_small.py, batches of 32, each padded to its longest text):

  as is     in page order, as section_route.most_similar does now;
  sorted    sorted by length first, so each batch holds texts of similar length, then put back in order.

It reports both times, the largest difference between the two sets of vectors, and whether the 8
paragraphs section-route would keep are the same. Nothing in src/ is changed.
"""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import booklet, claim_router, parse  # noqa: E402
from src.contexts import retrieval, section_route  # noqa: E402

SLOWEST = ["v1.1-row-500-A", "v1.1-row-782-A", "v1.1-row-580-A", "v1.1-row-904-A"]


def main():
    import numpy as np
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cases", nargs="*", default=SLOWEST)
    ap.add_argument("--booklets", type=Path, default=ROOT / "output" / "booklets_dev")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()
    cases = {c["id"]: c for c in map(json.loads, (ROOT / "data" / "dev" / "cases.jsonl").read_text().splitlines())}
    model = retrieval.embedder("e5-small")
    model.embed(["passage: warm-up"])
    results = []
    for case_id in args.cases:
        case = cases[case_id]
        pages = parse.load_pages(args.booklets / Path(case["booklet"]["path"]).name)
        part = claim_router.route(case["claim"]["text"])
        vote = booklet.find_vote(booklet.parse(pages), case["vote"])
        texts = [f"passage: {section_route.display(t)}" for _, t in booklet.part_paragraphs(pages, vote, part)]
        t = time.perf_counter()
        as_is = model.embed(texts)
        t_as_is = time.perf_counter() - t
        order = sorted(range(len(texts)), key=lambda i: len(texts[i]))
        t = time.perf_counter()
        part_sorted = model.embed([texts[i] for i in order])
        t_sorted = time.perf_counter() - t
        back = np.empty_like(part_sorted)
        back[order] = part_sorted
        query = retrieval.query_vector("e5-small", case["claim"]["text"])
        top = lambda v: sorted(sorted(range(len(texts)), key=lambda i: -(v @ query)[i])[:8])  # noqa: E731
        r = {"case": case_id, "part": part, "paragraphs": len(texts), "as_is_s": round(t_as_is, 2),
             "sorted_s": round(t_sorted, 2), "speedup": round(t_as_is / t_sorted, 2),
             "max_abs_difference": float(np.abs(as_is - back).max()), "same_top8": top(as_is) == top(back)}
        results.append(r)
        print(r, flush=True)
    if args.json:
        args.json.write_text(json.dumps(results, indent=1) + "\n")


if __name__ == "__main__":
    main()
