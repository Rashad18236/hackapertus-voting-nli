"""Measure task A context selection offline: no model endpoint, no tokens.

Run from track_2a/ (after scripts/fetch_dev_booklets.py, with the models in models/):

    EMBED_MODEL_DIR=models/multilingual-e5-small GRANITE_MODEL_DIR=models/granite-embedding-97m-multilingual-r2 \\
        python3 scripts/retrieval_check.py [--variant NAME] [--grid OUT.md] [--per-case OUT.jsonl]

For every dev task A case with a gold passage (labels 0 and 2), select the
context as the pipeline does (src/context.py) and report:

- hit rate: share of cases where at least one sent chunk (or page, when whole
  pages are sent) matches the gold passage (rapidfuzz partial_ratio >= 90 after
  normalising; the shorter text must lie almost exactly inside the longer).
- evidence ceiling: share of cases where at least one sent page would pass the
  evidence check (partial_ratio of gold vs page text >= 90): the best evidence
  score a model could reach by citing the pages it was shown.
- both split by same-language and cross-language (claim vs booklet language);
- mean characters sent, and their share of the booklet's characters;
- CPU seconds spent embedding (process CPU time, all threads): per booklet,
  and for the first case of a booklet and vote with an empty cache.

--variant NAME   one registered variant (default embed-e5-small).
--grid OUT.md    every setting of: 2 models x scope (booklet, section) x top_k
                 (4, 8, 12) x neighbours (0, 1) x cross-language rule (same,
                 double, section); writes a table and the chosen setting.

Embeddings are cached on disk in output/embed_cache/ (git-ignored), with the
CPU seconds each took, so changing top_k, neighbours or the cross-language
rule re-embeds nothing. embed-e5-small keeps its own whole-booklet embedding
(src/contexts/embed_e5_small.py), so its numbers stay as recorded.

Normalisation follows the starter's description (case, whitespace, line-break
hyphenation); this is our re-implementation, so the official scorer decides.
"""

import argparse
import hashlib
import itertools
import json
import pickle
import re
import sys
import time
from pathlib import Path

from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import context, parse  # noqa: E402
from src.contexts import embed_e5_small, retrieval, vote_section  # noqa: E402

THRESHOLD = 90
CACHE = ROOT / "output" / "embed_cache"
TARGETS = {"hit": 0.90, "hit_cross": 0.85, "ceiling": 0.80, "share": 0.10}


def passes(a, b):
    """partial_ratio(a, b) >= THRESHOLD; score_cutoff lets rapidfuzz stop early on long texts."""
    return fuzz.partial_ratio(a, b, score_cutoff=THRESHOLD) >= THRESHOLD


def normalise(text):
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)  # join words hyphenated at a line break
    return re.sub(r"\s+", " ", text).strip().lower()


# ---------------------------------------------------------------- data and cache

def load_cases(booklets):
    """Dev task A cases with a gold passage: [(case, gold passage, pages)]."""
    gold = {}
    for line in (ROOT / "data" / "dev" / "expected-labels.jsonl").read_text(encoding="utf-8").splitlines():
        g = json.loads(line)
        if g["id"].endswith("-A") and g["label"] in (0, 2) and g.get("reference"):
            gold[g["id"]] = g
    out = []
    for line in (ROOT / "data" / "dev" / "cases.jsonl").read_text(encoding="utf-8").splitlines():
        case = json.loads(line)
        if case["id"] in gold:
            out.append((case, gold[case["id"]], parse.load_pages(booklets / Path(case["booklet"]["path"]).name)))
    return out


def cross(case):
    return case["claim"].get("language") != case["booklet"].get("language")


def load_cache():
    """Fill the in-memory caches of embed_e5_small and retrieval from disk; return the booklet CPU table."""
    booklet_cpu = {}
    if (CACHE / "e5-small_booklets.pkl").is_file():
        for key, (chunks, vectors, cpu) in pickle.loads((CACHE / "e5-small_booklets.pkl").read_bytes()).items():
            embed_e5_small._chunk_cache[key] = (chunks, vectors)
            booklet_cpu[key] = cpu
    for model in retrieval.MODELS:
        if (CACHE / f"{model}_pages.pkl").is_file():
            for sha, value in pickle.loads((CACHE / f"{model}_pages.pkl").read_bytes()).items():
                retrieval._page_cache[(model, sha)] = value
        if (CACHE / f"{model}_queries.pkl").is_file():
            for text, vector in pickle.loads((CACHE / f"{model}_queries.pkl").read_bytes()).items():
                retrieval._query_cache[(model, text)] = vector
    return booklet_cpu


def save_cache(booklet_cpu):
    CACHE.mkdir(parents=True, exist_ok=True)
    booklets = {k: (c, v, booklet_cpu[k]) for k, (c, v) in embed_e5_small._chunk_cache.items() if k in booklet_cpu}
    (CACHE / "e5-small_booklets.pkl").write_bytes(pickle.dumps(booklets))
    for model in retrieval.MODELS:
        pages = {sha: v for (m, sha), v in retrieval._page_cache.items() if m == model}
        queries = {t: v for (m, t), v in retrieval._query_cache.items() if m == model}
        (CACHE / f"{model}_pages.pkl").write_bytes(pickle.dumps(pages))
        (CACHE / f"{model}_queries.pkl").write_bytes(pickle.dumps(queries))


def e5_booklet(pages, booklet_cpu):
    """embed-e5-small's own whole-booklet chunks and vectors (exactly as the variant computes them)."""
    key = hashlib.sha256(parse.booklet_prompt_text(pages).encode("utf-8")).hexdigest()
    if key not in embed_e5_small._chunk_cache:
        start = time.process_time()
        embed_e5_small.select_chunks(pages, "warm-up", top_k=1)  # embeds the booklet once, then caches it
        booklet_cpu[key] = time.process_time() - start
    chunks, vectors = embed_e5_small._chunk_cache[key]
    return chunks, vectors, booklet_cpu[key]


def page_sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- one selection, scored

class Scorer:
    """Remembers which chunks and pages match the gold passage, so the grid compares cheaply."""

    def __init__(self):
        self.memo = {}

    def match(self, case_id, gold, text):
        key = (case_id, hashlib.sha1(text.encode("utf-8")).hexdigest())
        if key not in self.memo:
            self.memo[key] = passes(normalise(text), gold)
        return self.memo[key]

    def page_ok(self, case_id, gold, page_text):
        key = (case_id, "page", hashlib.sha1(page_text.encode("utf-8")).hexdigest())
        if key not in self.memo:
            self.memo[key] = passes(gold, normalise(page_text))
        return self.memo[key]


def score_selection(scorer, case, gold_text, pages, pieces, shown, prompt_text):
    """pieces: the texts sent (chunks or pages); shown: {page: full text} the evidence may cite."""
    g = normalise(gold_text)
    return {
        "id": case["id"], "cross": cross(case),
        "hit": any(scorer.match(case["id"], g, t) for t in pieces),
        "ceiling": any(scorer.page_ok(case["id"], g, shown[p]) for p in shown),
        "chars": len(prompt_text), "share": len(prompt_text) / len(parse.booklet_prompt_text(pages)),
        "pages_sent": sorted(shown),
    }


def grid_select(case, pages, model, scope, k, neighbours, rule, booklet_cpu):
    """One grid setting for one case: (pieces, shown, prompt_text). Uses only cached embeddings."""
    if cross(case) and rule == "section":
        section = {p: pages[p] for p in vote_section.section_pages(pages, case["vote"])}
        return list(section.values()), section, parse.booklet_prompt_text(section)
    if cross(case) and rule == "double":
        k = 2 * k
    if model == "e5-small" and scope == "booklet":  # embed-e5-small's own embedding
        chunks, vectors, _ = e5_booklet(pages, booklet_cpu)
        query = retrieval.query_vector("e5-small", case["claim"]["text"])
        keep = retrieval.rank(vectors, query, k, neighbours)
        selected = [chunks[i] for i in keep]
        return ([t for _, t in selected], {p: pages[p] for p, _ in selected},
                embed_e5_small.excerpts_prompt_text(selected))
    text, shown = retrieval.select(pages, case["vote"], case["claim"]["text"], model=model, scope=scope, k=k,
                                   neighbours=neighbours, cross_rule="same")
    pieces = [part.split("\n", 1)[1] for part in text.split("\n\n=== PAGE ")] if text else []
    return pieces, shown, text


# ---------------------------------------------------------------- CPU cost

def cpu_costs(cases, model, scope, booklet_cpu):
    """(mean CPU s per booklet, mean CPU s for the first case of a booklet and vote, mean CPU s per query)."""
    booklets, pairs = {}, {}
    for case, _, pages in cases:
        booklets.setdefault(case["booklet"]["path"], pages)
        pairs.setdefault((case["booklet"]["path"], case["vote"]), pages)

    def pages_cost(pages, numbers):
        return sum(retrieval.page_chunks(model, pages[p])[2] for p in numbers)

    if model == "e5-small" and scope == "booklet":
        per_booklet = [e5_booklet(p, booklet_cpu)[2] for p in booklets.values()]
        per_first = [e5_booklet(pages, booklet_cpu)[2] for (b, v), pages in pairs.items()]
    elif scope == "booklet":
        per_booklet = [pages_cost(p, sorted(p)) for p in booklets.values()]
        per_first = [pages_cost(pages, sorted(pages)) for pages in pairs.values()]
    else:
        union = {}
        for (b, v), pages in pairs.items():
            union.setdefault(b, set()).update(vote_section.section_pages(pages, v))
        per_booklet = [pages_cost(booklets[b], sorted(numbers)) for b, numbers in union.items()]
        per_first = [pages_cost(pages, vote_section.section_pages(pages, v)) for (b, v), pages in pairs.items()]
    return sum(per_booklet) / len(per_booklet), sum(per_first) / len(per_first)


def query_cpu(cases, model):
    """CPU seconds to embed one claim, measured on 20 claims (outside the cache)."""
    claims = [c["claim"]["text"] for c, _, _ in cases[:20]]
    emb, prefix = retrieval.embedder(model), retrieval.MODELS[model][1]
    start = time.process_time()
    for t in claims:
        emb.embed([prefix + t])
    return (time.process_time() - start) / len(claims)


# ---------------------------------------------------------------- summaries

def summarise(rows):
    def rate(key, subset):
        return sum(r[key] for r in subset) / len(subset) if subset else float("nan")
    same, crossed = [r for r in rows if not r["cross"]], [r for r in rows if r["cross"]]
    return {
        "n": len(rows), "n_same": len(same), "n_cross": len(crossed),
        "hit": rate("hit", rows), "hit_same": rate("hit", same), "hit_cross": rate("hit", crossed),
        "ceiling": rate("ceiling", rows), "ceiling_same": rate("ceiling", same), "ceiling_cross": rate("ceiling", crossed),
        "chars": sum(r["chars"] for r in rows) / len(rows), "share": sum(r["share"] for r in rows) / len(rows),
    }


def meets(s):
    return (s["hit"] >= TARGETS["hit"] and s["hit_cross"] >= TARGETS["hit_cross"]
            and s["ceiling"] >= TARGETS["ceiling"] and s["share"] <= TARGETS["share"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--booklets", type=Path, default=ROOT / "output" / "booklets_dev")
    ap.add_argument("--variant", default="embed-e5-small", choices=context.MODES)
    ap.add_argument("--grid", type=Path, help="run the whole grid and write a markdown table here")
    ap.add_argument("--fill-cache", action="store_true", help="embed everything the grid needs, then stop")
    ap.add_argument("--per-case", type=Path, help="optional JSONL with per-case results (variant mode)")
    args = ap.parse_args()

    cases = load_cases(args.booklets)
    booklet_cpu = load_cache()
    scorer = Scorer()

    if args.fill_cache:
        embed_e5_small._get_embedder()  # load both models before any timing starts
        for model in retrieval.MODELS:
            retrieval.embedder(model)
        start = time.time()
        for i, (case, _, pages) in enumerate(cases, start=1):
            e5_booklet(pages, booklet_cpu)
            for model in retrieval.MODELS:
                retrieval.query_vector(model, case["claim"]["text"])
                numbers = sorted(pages) if model == "granite-97m-r2" else vote_section.section_pages(pages, case["vote"])
                for p in numbers:
                    retrieval.page_chunks(model, pages[p])
            if i % 20 == 0:
                print(f"{i}/{len(cases)} cases, {time.time() - start:.0f} s", file=sys.stderr, flush=True)
                save_cache(booklet_cpu)
        save_cache(booklet_cpu)
        print(f"cache filled in {time.time() - start:.0f} s wall")
        return

    if not args.grid:
        rows = []
        for case, gold, pages in cases:
            text, shown = context.select(pages, case["vote"], case["claim"]["text"], args.variant, cross(case))
            if args.variant == "embed-e5-small":
                pieces = [t for _, t in embed_e5_small.select_chunks(pages, case["claim"]["text"])]
            elif text:
                pieces = [part.split("\n", 1)[1] for part in text.split("\n\n=== PAGE ")]
            else:
                pieces = []
            rows.append(score_selection(scorer, case, gold["reference"], pages, pieces, shown, text))
        s = summarise(rows)
        print(f"variant {args.variant}: cases with a gold passage {s['n']} (same language {s['n_same']}, cross {s['n_cross']})")
        print(f"hit rate {s['hit']:.3f} (same {s['hit_same']:.3f}, cross {s['hit_cross']:.3f})")
        print(f"evidence ceiling {s['ceiling']:.3f} (same {s['ceiling_same']:.3f}, cross {s['ceiling_cross']:.3f})")
        print(f"mean chars sent {s['chars']:.0f} ({s['share']:.1%} of the booklet)")
        if args.per_case:
            args.per_case.parent.mkdir(parents=True, exist_ok=True)
            args.per_case.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        save_cache(booklet_cpu)
        return

    settings = list(itertools.product(("e5-small", "granite-97m-r2"), ("booklet", "section"), (4, 8, 12), (0, 1),
                                      ("same", "double", "section")))
    costs = {(m, sc): cpu_costs(cases, m, sc, booklet_cpu) for m in retrieval.MODELS for sc in ("booklet", "section")}
    qcpu = {m: query_cpu(cases, m) for m in retrieval.MODELS}
    results = []
    for model, scope, k, n, rule in settings:
        rows = []
        for case, gold, pages in cases:
            pieces, shown, text = grid_select(case, pages, model, scope, k, n, rule, booklet_cpu)
            rows.append(score_selection(scorer, case, gold["reference"], pages, pieces, shown, text))
        s = summarise(rows)
        s.update(model=model, scope=scope, k=k, neighbours=n, rule=rule, cpu_booklet=costs[(model, scope)][0],
                 cpu_first=costs[(model, scope)][1], cpu_query=qcpu[model], meets=meets(s))
        results.append(s)
        print(f"{model} {scope} k{k} n{n} {rule}: hit {s['hit']:.3f} (cross {s['hit_cross']:.3f}), "
              f"ceiling {s['ceiling']:.3f}, share {s['share']:.1%}{' MEETS' if s['meets'] else ''}", flush=True)

    ok = [s for s in results if s["meets"]]
    if ok:
        chosen = min(ok, key=lambda s: (s["chars"], s["cpu_first"]))
        verdict = "meets all targets; the cheapest such setting (fewest characters sent, then least CPU)"
    else:
        under = [s for s in results if s["share"] <= TARGETS["share"]]
        chosen = max(under, key=lambda s: (s["hit"], -s["chars"]))
        verdict = "MISSED THE TARGETS: no setting meets all of them; this is the best hit rate under 10 % of characters"
    write_grid(args.grid, results, chosen, verdict, len(cases))
    (args.grid.with_suffix(".json")).write_text(json.dumps({"results": results, "chosen": chosen, "verdict": verdict},
                                                           indent=1) + "\n", encoding="utf-8")
    save_cache(booklet_cpu)
    print("chosen:", chosen["model"], chosen["scope"], f"k{chosen['k']}", f"n{chosen['neighbours']}", chosen["rule"], "-", verdict)


def write_grid(path, results, chosen, verdict, n):
    lines = [f"Cases with a gold passage: {n}. Targets: hit rate >= {TARGETS['hit']} overall and >= {TARGETS['hit_cross']} "
             f"cross-language, evidence ceiling >= {TARGETS['ceiling']}, at most {TARGETS['share']:.0%} of booklet characters.", "",
             "| Model | Scope | k | Neighbours | Cross rule | Hit (same / cross) | Ceiling (same / cross) | Mean chars | Share | "
             "CPU s per booklet | CPU s first case of booklet and vote | CPU s per claim | Meets targets |",
             "|" + "---|" * 13]
    for s in results:
        lines.append(f"| {s['model']} | {s['scope']} | {s['k']} | {s['neighbours']} | {s['rule']} "
                     f"| {s['hit']:.3f} ({s['hit_same']:.3f} / {s['hit_cross']:.3f}) "
                     f"| {s['ceiling']:.3f} ({s['ceiling_same']:.3f} / {s['ceiling_cross']:.3f}) | {s['chars']:,.0f} "
                     f"| {s['share']:.1%} | {s['cpu_booklet']:.1f} | {s['cpu_first']:.1f} | {s['cpu_query']:.3f} "
                     f"| {'yes' if s['meets'] else 'no'} |")
    lines += ["", f"Chosen: {chosen['model']}, scope {chosen['scope']}, k {chosen['k']}, neighbours {chosen['neighbours']}, "
              f"cross rule {chosen['rule']}: {verdict}."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
