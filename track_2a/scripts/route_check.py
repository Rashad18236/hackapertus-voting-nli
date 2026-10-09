"""Measure the section-route variant offline (no model calls): parser, router, and what the routed part holds.

Run from track_2a/ (dev booklets in output/booklets_dev, see scripts/fetch_dev_booklets.py):

    EMBED_MODEL_DIR=models/multilingual-e5-small python3 scripts/route_check.py --out <folder>

Reports, for the dev split only:

1. Booklets: how many parse completely (every vote passes the checks of
   src/booklet.py), by language and year, and every problem found.
2. Claims: how many the router assigns a part (src/claim_router.py), every
   unrouted claim in full, and every case that falls back to embed-e5-small
   (no route, vote not found, or the part is empty for that vote), in full.
3. For the 201 cases with a gold passage (labels 0 and 2), on the paragraphs
   section-route would send:
   - hit: at least one sent paragraph matches the gold passage under the
     starter's evidence rule (re-implemented in scripts/evidence_loss.py:
     normalised, at most 5,000 characters, partial ratio >= 90). A paragraph
     matches when it lies (almost) entirely inside the gold passage. This is
     session 4's "hit rate" and, since the cited paragraphs are the evidence,
     also the evidence ceiling;
   - coverage: the share of the gold passage's 200-character windows found
     in the sent text, among those found anywhere in the booklet (mean, and
     the share of cases with at least 0.9);
   - pages: the routed part's pages hold every gold page (pages found as in
     session 5: 200-character windows of the gold passage). Strict: the gold
     passage starts with the vote's title, which also matches title pages
     next to the part;
   - inside: the share of sent paragraphs that match the gold passage;
   - characters sent (paragraph text as shown to the model).
   Split by part and by language (claim language vs booklet language).
   Every routed case without a hit is listed in full.

Writes summary.json and per_case.jsonl to --out.
"""

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import evidence_loss as el  # noqa: E402
from src import booklet, claim_router, parse  # noqa: E402
from src.contexts import section_route  # noqa: E402


def load(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def coverage(gold_norm, sent_texts, pages):
    """Share of the gold passage's 200-character windows found in the sent text, among those found anywhere
    in the booklet (some booklet pages have no extractable text, and the gold passage starts with the vote's
    title, which appears on other pages too)."""
    sent = el.norm("\n".join(sent_texts))
    booklet_text = [el.norm(t) for t in pages.values()]
    found = held = 0
    for w in el.windows(gold_norm):
        if any(t and el.fuzz.partial_ratio(w, t, score_cutoff=el.MIN_RATIO) >= el.MIN_RATIO for t in booklet_text):
            found += 1
            held += el.fuzz.partial_ratio(w, sent, score_cutoff=el.MIN_RATIO) >= el.MIN_RATIO
    return round(held / found, 3) if found else None


def booklet_report(booklets_dir):
    rows, problems = [], []
    for f in sorted(booklets_dir.glob("*.pdf")):
        bk = booklet.parse(parse.load_pages(f))
        votes = bk.votes if bk else []
        complete = bool(votes) and all(v.ok for v in votes)
        rows.append({"booklet": f.stem, "year": f.stem[:4], "language": f.stem[-2:], "votes": len(votes),
                     "votes_ok": sum(v.ok for v in votes), "complete": complete})
        if not votes:
            problems.append(f"{f.stem}: no contents entries found")
        problems += [f"{f.stem}, vote {i + 1}: {'; '.join(v.problems)}" for i, v in enumerate(votes) if not v.ok]
    return rows, problems


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cases", type=Path, default=ROOT / "output" / "devA")
    ap.add_argument("--booklets", type=Path, default=ROOT / "output" / "booklets_dev")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    rows, problems = booklet_report(args.booklets)
    cases = load(args.cases / "cases.jsonl")
    gold = {g["id"]: g for g in load(args.cases / "expected-labels.jsonl")}

    per_case, unrouted, fallbacks, misses, fallback_reasons = [], [], [], [], Counter()
    for case in cases:
        claim, vote = case["claim"]["text"], case["vote"]
        pages = parse.load_pages(args.booklets / Path(case["booklet"]["path"]).name)
        part = claim_router.route(claim)
        found = booklet.find_vote(booklet.parse(pages), vote)
        routed = section_route.route(pages, vote, claim)
        reason = None
        if part is None:
            unrouted.append({"id": case["id"], "language": case["claim"]["language"], "claim": claim})
            reason = "no route"
        elif found is None:
            reason = "vote not found in the booklet"
        elif not found.ok:
            reason = "vote's structure not found"
        elif routed is None:
            reason = f"part '{part}' empty for this vote"
        if reason:
            fallback_reasons[reason] += 1
            fallbacks.append({"id": case["id"], "reason": reason, "booklet": case["booklet"]["path"], "vote": vote,
                              "claim": claim})
        row = {"id": case["id"], "part": part, "routed": routed is not None,
               "claim_language": case["claim"]["language"], "booklet_language": case["booklet"]["language"],
               "cross": case["claim"]["language"] != case["booklet"]["language"], "gold_label": gold[case["id"]]["label"]}
        if routed is not None:
            _, paragraphs = routed
            row["chars_sent"] = sum(len(section_route.display(t)) for _, t in paragraphs)
            row["paragraphs_sent"] = len(paragraphs)
            row["part_pages"] = found.parts[part]
            row["trimmed"] = sum(len(section_route.display(t)) for _, t in booklet.part_paragraphs(pages, found, part)) \
                > section_route.MAX_CHARS
        g = gold[case["id"]]
        if g["label"] in (0, 2) and g.get("reference"):
            gold_norm = el.norm(g["reference"])
            _, gold_pages, _, _ = el.gold_pages(pages, gold_norm)
            row["gold_pages"] = gold_pages
            if routed is not None:
                _, paragraphs = routed
                inside = [el.item_matches(t, gold_norm) for _, t in paragraphs]
                row["hit"] = any(inside)
                row["inside_share"] = sum(inside) / len(inside)
                row["pages_hold_gold"] = bool(gold_pages) and set(gold_pages) <= set(found.parts[part])
                row["coverage"] = coverage(gold_norm, [t for _, t in paragraphs], pages)
                if not row["hit"]:
                    misses.append({"id": case["id"], "part": part, "booklet": case["booklet"]["path"], "vote": vote,
                                   "claim": claim, "part_pages": found.parts[part], "gold_pages": gold_pages,
                                   "gold_start": g["reference"][:300]})
        per_case.append(row)

    ev = [r for r in per_case if "gold_pages" in r]
    routed_ev = [r for r in ev if r["routed"]]

    def stats(subset):
        if not subset:
            return None
        covered = [r["coverage"] for r in subset if r["coverage"] is not None]
        return {"cases": len(subset), "hit": round(sum(r["hit"] for r in subset) / len(subset), 3),
                "coverage_mean": round(statistics.mean(covered), 3),
                "coverage_at_least_0.9": round(sum(c >= 0.9 for c in covered) / len(covered), 3),
                "pages_hold_gold": round(sum(r["pages_hold_gold"] for r in subset) / len(subset), 3),
                "inside_share": round(statistics.mean(r["inside_share"] for r in subset), 3),
                "mean_chars_sent": round(statistics.mean(r["chars_sent"] for r in subset)),
                "trimmed": sum(r["trimmed"] for r in subset)}

    by_part = {p: stats([r for r in routed_ev if r["part"] == p]) for p in claim_router.PARTS}
    by_lang = {"same-language": stats([r for r in routed_ev if not r["cross"]]),
               "cross-language": stats([r for r in routed_ev if r["cross"]])}
    by_booklet_lang = {lang: stats([r for r in routed_ev if r["booklet_language"] == lang]) for lang in ("de", "fr", "it")}
    by_year = defaultdict(lambda: [0, 0])
    for r in rows:
        by_year[(r["language"], r["year"])][0] += 1
        by_year[(r["language"], r["year"])][1] += r["complete"]
    summary = {
        "booklets": len(rows), "booklets_complete": sum(r["complete"] for r in rows),
        "votes": sum(r["votes"] for r in rows), "votes_ok": sum(r["votes_ok"] for r in rows),
        "booklets_by_language_year": {f"{lang} {year}": f"{ok}/{n}" for (lang, year), (n, ok) in sorted(by_year.items())},
        "booklet_problems": problems,
        "claims": len(cases), "claims_routed": len(cases) - len(unrouted),
        "routes": dict(Counter(r["part"] for r in per_case)),
        "cases_routed": sum(r["routed"] for r in per_case), "fallback_reasons": dict(fallback_reasons),
        "unrouted_claims": unrouted, "fallback_cases": fallbacks, "routed_evidence_misses": misses,
        "evidence_cases": len(ev), "evidence_cases_routed": len(routed_ev),
        "routed_evidence": stats(routed_ev), "by_part": by_part, "by_language": by_lang,
        "by_booklet_language": by_booklet_lang,
        "mean_chars_sent_all_routed": round(statistics.mean(r["chars_sent"] for r in per_case if r["routed"])),
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (args.out / "per_case.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in per_case),
                                             encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("per_case",)}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
