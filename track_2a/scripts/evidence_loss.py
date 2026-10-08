"""Where is task A evidence lost, and how high could it go with cited pages only? (no model calls)

Run from track_2a/ (after `scripts/retrieval_check.py --fill-cache`):

    EMBED_MODEL_DIR=models/multilingual-e5-small python3 scripts/evidence_loss.py \\
        --run docs/runs/<comparison>/embed-e5-small --cases output/devA --out <folder>

For every dev case with gold label 0 or 2 (they have a gold passage):

1. Matching rule: the starter's evaluate.py, re-implemented (normalise text:
   NFKC, drop soft hyphens, join words hyphenated at a line break, collapse
   whitespace, lower case; an item matches when it is not empty, at most 5,000
   characters after normalising, and rapidfuzz partial_ratio(item, passage)
   >= 90; only the first five items count; pages are not checked).
   The script checks that this reproduces the run's official evidence score.
2. Gold pages: the gold passage is cut into windows of 200 characters; a page
   holds a window when partial_ratio(window, page) >= 90. The main gold page
   holds the most windows; the gold pages are the window-holding pages
   reachable from it with at most two pages in between (blank or picture
   pages). A sentence repeated far away, on a front summary page, does not
   make that page a gold page.
3. Each case falls into exactly one class, checked in this order: hit (the
   answer's evidence matched); gold page not sent; predicted neutral; gold
   page sent but not cited; cited but text did not match.
4. Wrongly cited pages (cited, not gold pages) are compared with the start
   of the vote's detailed section: the run of pages, in steps of at most two,
   that the vote-section selector keeps around the main gold page when its
   gap filling is switched off (vote_section.MAX_GAP = 0 inside this script
   only; the variant's code is not changed).
5. Evidence item forms for the same pages (see --forms in scripts/evidence_forms.py):
   (a) whole page, split at 5,000 characters; (b) the chunks of that page
   that were sent, joined; (c) those chunks plus the neighbouring chunk on
   each side on the same page. For cases where no whole page of the booklet
   matches, the script says why and whether (b) or (c) could match.

Writes per_case.jsonl and summary.json.
"""

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import retrieval_check as rc  # noqa: E402
from src import parse  # noqa: E402
from src.contexts import embed_e5_small, vote_section  # noqa: E402

MIN_RATIO = 90
MAX_CHARS = 5000
MAX_ITEMS = 5
WINDOW = 200
LABEL = {0: "entailment", 1: "neutral", 2: "contradiction"}
CLASSES = ("hit", "gold page not sent", "predicted neutral", "gold page sent but not cited", "cited but text did not match")


# ---------------------------------------------------------------- the official rule, re-implemented

def norm(text):
    text = unicodedata.normalize("NFKC", text).replace("­", "")
    text = re.sub(r"(\w) ?-\s*\n\s*(\w)", r"\1\2", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def item_matches(text, gold_norm):
    t = norm(text)
    return bool(t) and len(t) <= MAX_CHARS and fuzz.partial_ratio(t, gold_norm, score_cutoff=MIN_RATIO) >= MIN_RATIO


def evidence_found(items, gold_norm):
    return any(item_matches(it["text"], gold_norm) for it in items[:MAX_ITEMS])


# ---------------------------------------------------------------- where the gold passage is

def windows(gold_norm):
    return [gold_norm[i:i + WINDOW] for i in range(0, len(gold_norm), WINDOW) if len(gold_norm[i:i + WINDOW]) >= 60]


def gold_pages(pages, gold_norm):
    """(main gold page, sorted gold pages, {page: windows held}, share of windows found anywhere)."""
    wins = windows(gold_norm)
    normed = {p: norm(t) for p, t in pages.items()}
    held = Counter()
    found = 0
    for w in wins:
        hit_any = False
        for p, t in normed.items():
            if t and fuzz.partial_ratio(w, t, score_cutoff=MIN_RATIO) >= MIN_RATIO:
                held[p] += 1
                hit_any = True
        found += hit_any
    if not held:
        return None, [], {}, 0.0
    main = max(held, key=lambda p: (held[p], -p))
    keep, frontier = {main}, [main]
    while frontier:
        p = frontier.pop()
        for q in range(p - 3, p + 4):
            if q in held and q not in keep:
                keep.add(q)
                frontier.append(q)
    return main, sorted(keep), dict(held), found / len(wins)


def detailed_section_start(pages, vote, main):
    """First page of the vote's detailed section around `main` (selector without gap filling, steps of <= 2)."""
    saved = vote_section.MAX_GAP
    vote_section.MAX_GAP = 0
    try:
        kept = set(vote_section.section_pages(pages, vote))
    finally:
        vote_section.MAX_GAP = saved
    if main not in kept:
        return None
    start = main
    while start - 1 in kept or start - 2 in kept:
        start = start - 1 if start - 1 in kept else start - 2
    return start


# ---------------------------------------------------------------- item forms for one cited page

def sent_chunk_indices(pages, page, sent_chunks):
    """Indices (in parse._split order) of the page's chunks that were sent."""
    pieces = parse._split(pages[page].strip(), embed_e5_small.CHUNK_CHARS)
    sent = {t for p, t in sent_chunks if p == page}
    return pieces, [i for i, t in enumerate(pieces) if t in sent]


def form_items(form, pages, page, sent_chunks):
    """Evidence items for one cited page in form a, b or c (each at most 5,000 characters)."""
    if form == "a":
        return parse.evidence_items(pages, [page])
    pieces, idx = sent_chunk_indices(pages, page, sent_chunks)
    if form == "c":
        idx = sorted({j for i in idx for j in (i - 1, i, i + 1) if 0 <= j < len(pieces)})
    text = " ".join(pieces[i] for i in idx)[:MAX_CHARS]
    return [{"page": page, "text": text}] if text else []


def evidence_for(form, pages, cited_pages, sent_chunks):
    items = []
    for p in cited_pages:
        items += form_items(form, pages, p, sent_chunks)
    return items[:MAX_ITEMS]


# ---------------------------------------------------------------- main

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

    rows, mismatch = [], 0
    for cid, case in cases.items():
        if gold[cid]["label"] not in (0, 2):
            continue
        g = norm(gold[cid]["reference"])
        pages = parse.load_pages(args.booklets / Path(case["booklet"]["path"]).name)
        sent_chunks = embed_e5_small.select_chunks(pages, case["claim"]["text"])
        sent = sorted({p for p, _ in sent_chunks})
        if raws[cid].get("context_pages") != sent:
            mismatch += 1
        main_p, gp, held, found_share = gold_pages(pages, g)
        pred = preds[cid]
        cited = [it["page"] for it in pred["evidence"]]
        cited_pages = list(dict.fromkeys(cited))
        model_pages = []
        try:
            model_pages = json.loads(raws[cid].get("answer") or "{}").get("pages", [])
        except json.JSONDecodeError:
            pass
        hit = evidence_found(pred["evidence"], g)
        if hit:
            cls = "hit"
        elif not set(gp) & set(sent):
            cls = "gold page not sent"
        elif pred["label"] == 1:
            cls = "predicted neutral"
        elif not set(gp) & set(cited_pages):
            cls = "gold page sent but not cited"
        else:
            cls = "cited but text did not match"
        start = detailed_section_start(pages, case["vote"], main_p) if main_p else None
        wrong = [p for p in cited_pages if p not in gp]
        whole_page_ok = [p for p in pages if any(item_matches(it["text"], g) for it in parse.evidence_items(pages, [p]))]
        row = {"id": cid, "gold": LABEL[gold[cid]["label"]], "pred": LABEL[pred["label"]], "cross": rc.cross(case),
               "class": cls, "sent_pages": sent, "cited_pages": cited_pages, "model_pages": model_pages,
               "gold_pages": gp, "main_gold_page": main_p, "windows_found_share": round(found_share, 3),
               "detailed_section_start": start, "wrongly_cited": wrong,
               "wrongly_cited_before_section": [p for p in wrong if start is not None and p < start],
               "whole_page_matches": whole_page_ok, "gold_chars": len(g)}
        for form in ("a", "b", "c"):
            row[f"evidence_{form}"] = evidence_found(evidence_for(form, pages, cited_pages, sent_chunks), g) if pred["label"] in (0, 2) else False
            # could this form match if the model cited the right sent page? (any sent page, this form)
            row[f"sent_ceiling_{form}"] = any(evidence_found(form_items(form, pages, p, sent_chunks), g) for p in sent)
        if not whole_page_ok:
            row["no_whole_page_reason"] = reason(g, pages, gp, held, found_share)
        rows.append(row)

    summary = summarise(rows, mismatch)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "per_case.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    (args.out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1))


def reason(g, pages, gp, held, found_share):
    """Why no whole page matches the gold passage (first fitting reason)."""
    if len(g) > MAX_CHARS and len(gp) >= 2:
        return "passage over 5,000 characters, over several pages"
    if len(g) > MAX_CHARS:
        return "passage over 5,000 characters"
    if len(gp) >= 2:
        return "page break: the passage runs over several pages"
    if found_share < 0.5:
        return "PDF text differs from the gold text"
    return "other"


def summarise(rows, mismatch):
    def counts(sub):
        c = Counter(r["class"] for r in sub)
        return {k: c.get(k, 0) for k in CLASSES}
    same, crossed = [r for r in rows if not r["cross"]], [r for r in rows if r["cross"]]
    answered = [r for r in rows if r["pred"] != "neutral"]
    wrong_total = sum(len(r["wrongly_cited"]) for r in rows)
    before = sum(len(r["wrongly_cited_before_section"]) for r in rows)
    no_whole = [r for r in rows if not r["whole_page_matches"]]
    n = len(rows)
    return {
        "cases": n, "sent_pages_differ_from_run": mismatch,
        "classes": {"all": counts(rows), "same-language": counts(same), "cross-language": counts(crossed)},
        "cases_same_language": len(same), "cases_cross_language": len(crossed),
        "mean_pages_cited_label_0_2": round(sum(len(r["cited_pages"]) for r in answered) / max(1, len(answered)), 2),
        "mean_pages_in_answer_label_0_2": round(sum(len(r["model_pages"]) for r in answered) / max(1, len(answered)), 2),
        "answers_label_0_2": len(answered),
        "wrongly_cited_pages": wrong_total, "wrongly_cited_before_detailed_section": before,
        "answers_with_a_wrong_page_before_the_section": sum(1 for r in rows if r["wrongly_cited_before_section"]),
        "cases_without_section_start": sum(1 for r in rows if r["detailed_section_start"] is None),
        "evidence_score_by_form": {f: round(sum(r[f"evidence_{f}"] for r in rows) / n, 3) for f in "abc"},
        "evidence_found_by_form": {f: sum(r[f"evidence_{f}"] for r in rows) for f in "abc"},
        "ceiling_if_right_sent_page_cited": {f: round(sum(r[f"sent_ceiling_{f}"] for r in rows) / n, 3) for f in "abc"},
        "ceiling_whole_booklet_form_a": round(sum(bool(r["whole_page_matches"]) for r in rows) / n, 3),
        "no_whole_page_match": {
            "cases": len(no_whole),
            "reasons": dict(Counter(r["no_whole_page_reason"] for r in no_whole)),
            "gold_page_sent": sum(1 for r in no_whole if set(r["gold_pages"]) & set(r["sent_pages"])),
            "form_b_could_match": sum(1 for r in no_whole if r["sent_ceiling_b"]),
            "form_c_could_match": sum(1 for r in no_whole if r["sent_ceiling_c"]),
        },
    }


if __name__ == "__main__":
    main()
