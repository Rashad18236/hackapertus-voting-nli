"""Session 12, step 1b: paragraph rankers compared without the endpoint. No model calls.

Run from track_2a/ (models in models/):

    EMBED_MODEL_DIR=models/multilingual-e5-small STATIC_MODEL_DIR=models/static-similarity-mrl-multilingual-v1 \\
        python3 scripts/ranker_check.py --out docs/runs/<folder>/ranker_check.json

Rankers (each orders a list of paragraphs by similarity to the claim):

- e5       today: multilingual-e5-small on each paragraph as shown ("passage: " / "query: ");
- S        model S (src/static_embed.py), first 256 dimensions; S-1024: all 1,024 dimensions (for the cut decision);
- BM25     Kaan's BM25 (src/contexts/bm25.py) over the paragraphs, on the claim as it is (no translation: a local
           translation model is not allowed, and this step makes no Apertus call);
- S+BM25, e5+BM25: reciprocal-rank fusion, 1 / (60 + rank) summed (bm25.RRF_K).

Three measures, on the session 11 final runs' answers (dev, val, probe; docs/runs/2026-10-13_rashad_final-s11_*):

1. task A, routed cases answered correctly with label 0 or 2 whose part was NOT cut (so Apertus saw every
   paragraph of the part): is the first paragraph the answer cites among the ranker's 8 best, and among its 4 best?
   Same-language and cross-language separately; also for parts of more than 8 paragraphs only (where "among the 8"
   is not true by construction).
2. task A, routed cases whose part WAS cut to 8 paragraphs: how many of e5's 8 the ranker also picks, and, for gold
   entailment and contradiction cases, whether a paragraph matching the gold passage (the scorer's rule) is among
   the 8 (e5's and the ranker's).
3. task B, references over 3,000 characters: how many of selector T's 4 paragraphs (e5 on each paragraph's first
   300 characters, today's default) the ranker picks on the paragraphs' whole text. Information only.

Only ids and counts are written; no booklet or claim text.
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from src import booklet, parse, taskb_context  # noqa: E402
from src.contexts import bm25, retrieval, section_route  # noqa: E402

RUNS = ROOT / "docs" / "runs"
SETS = {
    "dev": ("2026-10-13_rashad_final-s11_dev600", "output/devA", "output/devB", "output/data_dev"),
    "val": ("2026-10-13_rashad_final-s11_val1160", "data/val", "output/valB", "output/data_dev"),
    "probe": ("2026-10-13_rashad_final-s11_probe188", "output/probeA", "output/probeB", "output/data_probe"),
}
RANKERS = ("e5", "S", "S-1024", "BM25", "S+BM25", "e5+BM25")
MODEL = {"e5": "e5-small", "S": "static-s", "S-1024": "static-s-1024"}


def load(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def first_cited(answer):
    try:
        cited = json.loads(answer).get("paragraphs") or []
        return int(cited[0]) if cited else None
    except (ValueError, TypeError, AttributeError, IndexError):
        return None


_cache = {}


def model_scores(model, texts, claim):
    """Cosine similarity of the claim to each text (texts as shown), with the model's own prefixes."""
    _, query_prefix, passage_prefix = retrieval.MODELS[model]
    key = (model, tuple(texts))
    if key not in _cache:
        _cache[key] = retrieval.embedder(model).embed([passage_prefix + t for t in texts])
    return list(_cache[key] @ retrieval.query_vector(model, claim))


def bm25_scores(texts, claim):
    return bm25.bm25_scores([(0, t) for t in texts], claim)


def fused(a, b):
    return [1 / (bm25.RRF_K + x) + 1 / (bm25.RRF_K + y) for x, y in zip(bm25.ranks(a), bm25.ranks(b))]


def scores(ranker, texts, claim):
    if ranker in MODEL:
        return model_scores(MODEL[ranker], texts, claim)
    if ranker == "BM25":
        return bm25_scores(texts, claim)
    first = ranker.split("+")[0]
    return fused(model_scores(MODEL[first], texts, claim), bm25_scores(texts, claim))


def top(values, k):
    """Indices of the k best, best first (ties keep the earlier paragraph first, as sorted() does today)."""
    return sorted(range(len(values)), key=lambda i: -values[i])[:k]


def task_a(name, run, cases_dir, data_dir, el, rows_a, rows_cut):
    cases = {c["id"]: c for c in load(ROOT / cases_dir / "cases.jsonl")}
    expected = {e["id"]: e for e in load(ROOT / cases_dir / "expected-labels.jsonl")}
    raw = {r["id"]: r for r in load(RUNS / run / "task-A" / "raw_answers.jsonl")}
    pred = {p["id"]: p for p in load(RUNS / run / "task-A" / "predictions.jsonl")}
    for cid, case in cases.items():
        r = raw.get(cid) or {}
        part = r.get("route")
        if not part:
            continue
        pages = parse.load_pages(ROOT / data_dir / case["booklet"]["path"])
        found = section_route.find(section_route.parsed_booklet(pages), case["vote"])
        if found is None or part not in found.valid:
            continue
        whole = booklet.part_paragraphs(pages, found, part)
        texts = [section_route.display(t) for _, t in whole]
        claim = case["claim"]["text"]
        cross = case["claim"]["language"] != case["booklet"]["language"]
        cut = sum(len(t) for t in texts) > section_route.MAX_CHARS
        label = expected[cid]["label"]
        if not cut:
            n = first_cited(r.get("answer"))
            if pred.get(cid, {}).get("label") != label or label not in (0, 2) or not n or not 1 <= n <= len(texts):
                continue
            row = {"set": name, "id": cid, "cross": cross, "paragraphs": len(texts)}
            for ranker in RANKERS:
                order = top(scores(ranker, texts, claim), 8)
                row[ranker] = {"at8": n - 1 in order, "at4": n - 1 in order[:4]}
            rows_a.append(row)
        else:
            e5_8 = set(top(scores("e5", texts, claim), section_route.TOP_K))
            row = {"set": name, "id": cid, "cross": cross, "paragraphs": len(texts), "label": label}
            gold = el.norm(expected[cid]["reference"]) if label in (0, 2) and expected[cid].get("reference") else None
            gold_idx = {i for i, t in enumerate(texts) if gold and el.item_matches(t, gold)} if gold else None
            for ranker in RANKERS:
                chosen = set(top(scores(ranker, texts, claim), section_route.TOP_K))
                row[ranker] = {"shared_with_e5": len(chosen & e5_8)}
                if gold_idx is not None:
                    row[ranker]["gold_covered"] = bool(chosen & gold_idx)
            row["gold_in_part"] = bool(gold_idx) if gold_idx is not None else None
            rows_cut.append(row)


def task_b(name, cases_dir, rows_b):
    for case in load(ROOT / cases_dir / "cases.jsonl"):
        reference = case["reference"]["text"]
        if not taskb_context.is_long(reference, "cut4-t"):
            continue
        _, paragraphs = taskb_context.split(reference)
        if len(paragraphs) <= taskb_context.CUT4_TOP_K:
            continue
        claim = case["claim"]["text"]
        t_scores = taskb_context.selector_scores("T", paragraphs, claim)
        t4 = set(top(t_scores, taskb_context.CUT4_TOP_K))
        texts = [section_route.display(p) for p in paragraphs]
        row = {"set": name, "id": case["id"], "cross": case["claim"]["language"] != case["reference"]["language"]}
        for ranker in RANKERS:
            row[ranker] = len(t4 & set(top(scores(ranker, texts, claim), taskb_context.CUT4_TOP_K)))
        rows_b.append(row)


def share(rows, ranker, key):
    return round(sum(r[ranker][key] for r in rows) / len(rows), 4) if rows else None


def summary_a(rows):
    out = {}
    for group, sel in (("all", rows), ("same", [r for r in rows if not r["cross"]]),
                       ("cross", [r for r in rows if r["cross"]])):
        big = [r for r in sel if r["paragraphs"] > 8]
        out[group] = {"cases": len(sel), "cases_over_8_paragraphs": len(big)}
        for ranker in RANKERS:
            out[group][ranker] = {"at8": share(sel, ranker, "at8"), "at4": share(sel, ranker, "at4"),
                                  "at8_over_8": share(big, ranker, "at8"), "at4_over_8": share(big, ranker, "at4")}
    return out


def summary_cut(rows):
    out = {}
    for group, sel in (("all", rows), ("same", [r for r in rows if not r["cross"]]),
                       ("cross", [r for r in rows if r["cross"]])):
        gold = [r for r in sel if r.get("gold_in_part")]
        out[group] = {"cases": len(sel), "gold_cases_with_gold_in_part": len(gold)}
        for ranker in RANKERS:
            out[group][ranker] = {
                "mean_shared_with_e5_8": round(sum(r[ranker]["shared_with_e5"] for r in sel) / len(sel), 3) if sel else None,
                "gold_covered": sum(r[ranker]["gold_covered"] for r in gold)}
    return out


def summary_b(rows):
    out = {}
    for group, sel in (("all", rows), ("same", [r for r in rows if not r["cross"]]),
                       ("cross", [r for r in rows if r["cross"]])):
        out[group] = {"references": len(sel)}
        for ranker in RANKERS:
            out[group][ranker] = {"mean_shared_with_T4": round(sum(r[ranker] for r in sel) / len(sel), 3) if sel else None,
                                  "all_4_equal": sum(r[ranker] == min(4, taskb_context.CUT4_TOP_K) for r in sel)}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--sets", default="dev,val,probe")
    args = ap.parse_args()
    import evidence_loss as el
    rows_a, rows_cut, rows_b = [], [], []
    for name in args.sets.split(","):
        run, cases_a, cases_b, data_dir = SETS[name]
        task_a(name, run, cases_a, data_dir, el, rows_a, rows_cut)
        task_b(name, cases_b, rows_b)
        print(name, len(rows_a), len(rows_cut), len(rows_b), flush=True)
    result = {"rankers": RANKERS,
              "task_a_not_cut": {"pooled": summary_a(rows_a)} | {
                  n: summary_a([r for r in rows_a if r["set"] == n]) for n in args.sets.split(",")},
              "task_a_cut": {"pooled": summary_cut(rows_cut)} | {
                  n: summary_cut([r for r in rows_cut if r["set"] == n]) for n in args.sets.split(",")},
              "task_b_long": {"pooled": summary_b(rows_b)} | {
                  n: summary_b([r for r in rows_b if r["set"] == n]) for n in args.sets.split(",")},
              "rows": {"task_a_not_cut": rows_a, "task_a_cut": rows_cut, "task_b_long": rows_b}}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k]["pooled"] for k in ("task_a_not_cut", "task_a_cut", "task_b_long")}, indent=1))


if __name__ == "__main__":
    main()
