"""Do two versions of the e5 embedding give the same vectors and the same selections? (session 8, no model calls)

Run from track_2a/ (dev and val booklets in output/booklets_dev; e5 files in models/multilingual-e5-small):

    python3 scripts/embed_equivalence.py save --out OLD.npz          # with the code before a change
    python3 scripts/embed_equivalence.py compare --old OLD.npz [--json RESULT.json]   # with the code after it

Uses the pipeline's own code: embed_e5_small.chunk_pages and E5Embedder (src/contexts/embed_e5_small.py).
For every booklet of the dev and val task A cases (45 PDFs; 44 of them are the dev booklets): the
"passage: " vectors of all its chunks, as embed-e5-small embeds the whole booklet. For each of the 880 task
A cases (300 dev, 580 val): the claim's "query: " vector and the 8 chunks embed-e5-small selects
(select_chunks' ranking: highest cosine first, the 8 best in chunk order).

compare reports, per booklet, the largest absolute difference between the saved and the new vectors (the
gate allows at most 1e-6), the largest difference between query vectors, and every case whose 8 chunks
differ. Exit code 1 if any vector differs by more than 1e-6 or any selection differs.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("EMBED_MODEL_DIR", str(ROOT / "models" / "multilingual-e5-small"))

from src import parse  # noqa: E402
from src.contexts import embed_e5_small  # noqa: E402

CASES = (ROOT / "data" / "dev" / "cases.jsonl", ROOT / "data" / "val" / "cases.jsonl")
LIMIT = 1e-6


def task_a_cases():
    cases = []
    for path in CASES:
        cases += [c for c in map(json.loads, path.read_text(encoding="utf-8").splitlines()) if "booklet" in c]
    return cases


def compute(booklets_dir):
    import numpy as np
    embedder = embed_e5_small.E5Embedder()
    cases = task_a_cases()
    names = sorted({Path(c["booklet"]["path"]).name for c in cases})
    vectors, seconds = {}, {}
    for name in names:
        pages = parse.load_pages(Path(booklets_dir) / name)
        texts = [f"passage: {text}" for _, text in embed_e5_small.chunk_pages(pages)]
        t = time.perf_counter()
        vectors[name] = embedder.embed(texts)
        seconds[name] = round(time.perf_counter() - t, 2)
        print(f"{name}: {len(texts)} chunks, {seconds[name]} s", flush=True)
    queries = embedder.embed([f"query: {c['claim']['text']}" for c in cases])
    selections = {}
    for c, q in zip(cases, queries):
        scores = vectors[Path(c["booklet"]["path"]).name] @ q
        best = sorted(range(len(scores)), key=lambda i: -scores[i])[:embed_e5_small.TOP_K]
        selections[c["id"]] = sorted(best)
    return names, vectors, np.asarray(queries), [c["id"] for c in cases], selections, seconds


def main():
    import numpy as np
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    s = sub.add_parser("save")
    s.add_argument("--out", required=True)
    c = sub.add_parser("compare")
    c.add_argument("--old", required=True)
    c.add_argument("--json")
    for p in (s, c):
        p.add_argument("--booklets", default=str(ROOT / "output" / "booklets_dev"))
    args = ap.parse_args()

    names, vectors, queries, ids, selections, seconds = compute(args.booklets)
    if args.command == "save":
        np.savez_compressed(args.out, names=np.array(names), ids=np.array(ids), queries=queries,
                            selections=json.dumps(selections), seconds=json.dumps(seconds),
                            **{f"v_{n}": v for n, v in vectors.items()})
        print(f"saved {len(names)} booklets, {len(ids)} cases to {args.out}")
        return 0
    old = np.load(args.old)
    old_sel, old_sec = json.loads(str(old["selections"])), json.loads(str(old["seconds"]))
    per_booklet = {n: float(np.abs(old[f"v_{n}"] - vectors[n]).max()) if old[f"v_{n}"].shape == vectors[n].shape
                   else float("inf") for n in names}
    query_diff = float(np.abs(old["queries"] - queries).max())
    changed = sorted(i for i in ids if old_sel[i] != selections[i])
    worst = max(per_booklet.values())
    result = {"booklets": len(names), "cases": len(ids), "max_abs_difference": worst,
              "max_abs_difference_queries": query_diff, "selections_differ": len(changed), "changed_cases": changed,
              "seconds_old_total": round(sum(old_sec.values()), 1), "seconds_new_total": round(sum(seconds.values()), 1),
              "per_booklet": {n: {"max_abs_difference": per_booklet[n], "seconds_old": old_sec[n],
                                  "seconds_new": seconds[n]} for n in names}}
    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    passed = worst <= LIMIT and query_diff <= LIMIT and not changed
    print(json.dumps({k: v for k, v in result.items() if k != "per_booklet"}, indent=1))
    print("extra gate B:", "pass" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
