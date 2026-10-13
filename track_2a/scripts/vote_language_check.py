"""Vote names in another language (session 10, step 8). No model calls.

Run from track_2a/ (dev and val booklets in output/booklets_dev):

    EMBED_MODEL_DIR=models/multilingual-e5-small python3 scripts/vote_language_check.py --out <file.json>

Session 12: --ranker S runs the same test with model S (STATIC_MODEL_DIR=models/static-similarity-mrl-multilingual-v1)
to set its own margin (section_route.VOTE_MARGIN_S). --out holds vote names: keep it outside the repository.

section-route finds a case's vote by matching the vote name to the booklet's contents titles (src/booklet.py
find_vote: fuzzy, same language). A vote name in another language than the booklet does not match, and the case
falls back to embed-e5-small. Step 8 adds a second try by meaning (src/contexts/section_route.py vote_by_meaning:
multilingual e5, "query: " + vote name against "passage: " + each title) that picks the closest title only if it
leads the second closest by at least a margin.

The test: for every dev and val task A case whose vote is found by its own name, the same vote's name in each
other language replaces it. The same vote in another language is the vote at the same position in the booklet of
the same date in that language (votes aligned by order of their contents entries; a date is used only if all its
booklets list the same number of votes). The name used is a dataset vote name of that vote and language when a
dev or val case has one, else that booklet's contents title. For each swapped name the script records the
position by meaning and the margin (best cosine minus second best).

Prints, for margins from 0 to 0.10, how many swapped names would be matched right, matched wrong and left
unmatched, and the smallest margin with no wrong match. Writes every swap to --out.
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import booklet, parse  # noqa: E402
from src.contexts import section_route  # noqa: E402

BOOKLETS = ROOT / "output" / "booklets_dev"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ranker", default="e5", choices=("e5", "S"),
                    help="session 12: the model that places a name by meaning (src/rankers.py); S sets VOTE_MARGIN_S")
    args = ap.parse_args()
    from src import rankers
    rankers.ACTIVE["name"] = args.ranker
    cases = []
    for name in ("dev", "val"):
        cases += [json.loads(l) for l in (ROOT / "data" / name / "cases.jsonl").read_text(encoding="utf-8").splitlines()
                  if l.strip() and '"booklet"' in l]
    parsed = {}

    def booklet_of(file_name):
        if file_name not in parsed:
            path = BOOKLETS / file_name
            parsed[file_name] = section_route.parsed_booklet(parse.load_pages(path)) if path.is_file() else None
        return parsed[file_name]

    # Position of each case's vote by its own name; vote names per (date, language, position).
    names = defaultdict(set)
    located = []
    for case in cases:
        file_name = Path(case["booklet"]["path"]).name
        b = booklet_of(file_name)
        found = booklet.find_vote(b, case["vote"])
        if found is None:
            continue
        position = b.votes.index(found)
        date, lang = file_name[:10], file_name[11:13]
        names[(date, lang, position)].add(case["vote"])
        located.append((case, date, lang, position))
    swaps, checked = [], set()
    for case, date, lang, position in located:
        own = booklet_of(f"{date}_{lang}.pdf")
        for other in ("de", "fr", "it"):
            if other == lang:
                continue
            other_booklet = booklet_of(f"{date}_{other}.pdf")
            if other_booklet is None or len(other_booklet.votes) != len(own.votes):
                continue
            candidates = sorted(names.get((date, other, position), ())) or [other_booklet.votes[position].title]
            for vote_name in candidates:
                key = (date, lang, position, vote_name)
                if key in checked:
                    continue
                checked.add(key)
                by_fuzzy = booklet.find_vote(own, vote_name)
                best, margin = section_route.vote_scores(own, vote_name)
                swaps.append({"date": date, "booklet_language": lang, "name_language": other, "position": position,
                              "votes": len(own.votes), "name": vote_name,
                              "fuzzy": None if by_fuzzy is None else own.votes.index(by_fuzzy),
                              "by_meaning": best, "margin": round(float(margin), 4)})
    Path(args.out).write_text(json.dumps(swaps, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    multi = [s for s in swaps if s["votes"] > 1]
    print(f"{len(located)} cases located by their own name; {len(swaps)} swapped names "
          f"({len(multi)} in booklets with several votes); fuzzy match on a swapped name: "
          f"{sum(1 for s in swaps if s['fuzzy'] is not None)} (wrong: {sum(1 for s in swaps if s['fuzzy'] not in (None, s['position']))})")
    wrong_margins = [s["margin"] for s in multi if s["by_meaning"] != s["position"]]
    print(f"largest margin of a wrong pick: {max(wrong_margins) if wrong_margins else None}")
    for m in [x / 100 for x in range(0, 11)]:
        right = sum(1 for s in multi if s["margin"] >= m and s["by_meaning"] == s["position"])
        wrong = sum(1 for s in multi if s["margin"] >= m and s["by_meaning"] != s["position"])
        print(f"margin {m:.2f}: right {right}, wrong {wrong}, unmatched {len(multi) - right - wrong}")


if __name__ == "__main__":
    main()
