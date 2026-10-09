"""Parse booklets the parser has never seen (vote dates in neither dev nor test) with src/booklet.py.

Run from track_2a/ (no model calls; the PDFs are downloaded separately, see docs/checks_no_model.md):

    python3 -I scripts/unseen_booklets.py --booklets output/booklets_unseen --out docs/runs/<folder>
    python3 -I scripts/unseen_booklets.py --booklets output/booklets_dev --proposal --out <folder>

For every PDF: pages, contents lines, votes, and per vote whether every check passed
(Vote.ok), the problems the parser names, the pages of each part, the recommendation boxes,
and how many paragraphs each part gives (booklet.part_paragraphs, what section-route sends).
It also checks that find_vote() picks each vote back by the title printed on its detail page
(the dataset's `vote` field is the official title, in the booklet's language).

--proposal applies the parser changes proposed in docs/checks_no_model.md (Part 5) at run time,
by replacing three patterns of src/booklet.py in memory. The file itself is not changed.
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import booklet, parse  # noqa: E402

# Proposed patterns (Part 5), applied only with --proposal:
# 1. 2018-2019 booklets name the council's arguments without "and Parliament": "Argumente Bundesrat",
#    "Les arguments du Conseil fédéral", "Gli argomenti del Consiglio federale".
PROPOSED_COUNCIL = (r"argumente (?:von |des )?bundesrat(?:es)?(?: und parlament)?"
                    r"|arguments? (?:du )?conseil fédéral(?: et (?:du )?parlement)?"
                    r"|gli argomenti del consiglio federale(?: e del parlamento)?")
# 2. The parliamentary debate is also called "Le deliberazioni in Parlamento" (2018-09-23).
PROPOSED_DEBATE = booklet._DEBATE + r"|deliberazion[ei](?:in|al)?parlamento"
PROPOSED_DEBATE_LISTED = booklet._DEBATE_LISTED + r"|deliberazion[ei] (?:in |al )?parlamento"
# 3. When the arguments open with the parliamentary debate, its page carries no "Argumente" heading:
#    accept the debate heading there too.
PROPOSED_ARGUMENTS_HEADING = booklet._HEADINGS["arguments"] + "|" + PROPOSED_DEBATE


def apply_proposal():
    booklet._COUNCIL = PROPOSED_COUNCIL
    booklet._DEBATE = PROPOSED_DEBATE
    booklet._DEBATE_LISTED = PROPOSED_DEBATE_LISTED
    booklet._HEADINGS["arguments"] = PROPOSED_ARGUMENTS_HEADING


_LIST_LINE = re.compile(r"\s\d{1,3}\s*$")


def detail_title(pages, vote):
    """The vote's title as printed on its detail page: the lines after the running header, before the list."""
    lines = [line.strip() for line in pages.get(vote.entry.get("detail"), "").splitlines()]
    out = []
    for line in lines[1:]:
        if not line or _LIST_LINE.search(line) or booklet.norm(line) in ("im detail", "en détail", "in dettaglio"):
            break
        out.append(line)
    return " ".join(out)


def check(pdf, cache_dir):
    start = time.perf_counter()
    pages = parse.load_pages(pdf, cache_dir=cache_dir)
    parsed = booklet.parse(pages)
    result = {"booklet": pdf.name, "pages": len(pages), "characters": sum(len(t) for t in pages.values()),
              "contents_lines": len(booklet.contents_entries(pages)),
              "votes": None if parsed is None else len(parsed.votes), "votes_ok": 0, "vote_details": []}
    for vote in (parsed.votes if parsed else []):
        title = detail_title(pages, vote)
        picked = booklet.find_vote(parsed, title) if title else None
        detail = {
            "title": booklet.norm(vote.title)[:120], "detail_page_title": title[:160], "ok": vote.ok,
            "problems": vote.problems, "entry": vote.entry,
            "parts": {k: ([min(v), max(v)] if v else []) for k, v in vote.parts.items()},
            "boxes": {k: len(v) for k, v in vote.boxes.items()},
            "paragraphs": {k: len(booklet.part_paragraphs(pages, vote, k)) for k in booklet.PARTS} if vote.ok else {},
            "find_vote_by_detail_title": None if not title else (picked is vote),
        }
        result["votes_ok"] += vote.ok
        result["vote_details"].append(detail)
    result["seconds"] = round(time.perf_counter() - start, 2)
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--booklets", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--proposal", action="store_true", help="apply the proposed patterns in memory")
    ap.add_argument("--cache", type=Path, default=Path("/tmp/booklet-cache-unseen"))
    args = ap.parse_args()
    if args.proposal:
        apply_proposal()
    results = [check(pdf, args.cache) for pdf in sorted(args.booklets.glob("*.pdf"))]
    args.out.mkdir(parents=True, exist_ok=True)
    name = "booklets_proposal.json" if args.proposal else "booklets.json"
    (args.out / name).write_text(json.dumps(results, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for r in results:
        parts_missing = sorted({k for v in r["vote_details"] if v["ok"] for k, n in v["paragraphs"].items()
                                if n == 0 and k not in ("committee", "parliament")})
        problems = sorted({p for v in r["vote_details"] for p in v["problems"]})
        print(f"{r['booklet']}: {r['pages']} pages, {r['votes']} votes, {r['votes_ok']} ok"
              f"{'; empty parts: ' + ', '.join(parts_missing) if parts_missing else ''}"
              f"{'; problems: ' + ' | '.join(problems) if problems else ''}")
    total = sum(r["votes"] or 0 for r in results)
    ok = sum(r["votes_ok"] for r in results)
    full = sum(1 for r in results if r["votes"] and r["votes_ok"] == r["votes"])
    print(f"{len(results)} booklets, {full} fully parsed; {ok} of {total} votes ok"
          f"{' (with the proposed patterns)' if args.proposal else ''}")


if __name__ == "__main__":
    main()
