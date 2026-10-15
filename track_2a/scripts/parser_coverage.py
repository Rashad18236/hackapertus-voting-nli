"""Parser coverage on a folder of booklets, with a cross-language check (session 11, step 1). No model calls.

Run from track_2a/ (booklets downloaded by scripts/fetch_unseen_booklets.py --since 2016, outside the repository):

    python3 scripts/parser_coverage.py --booklets /home/user/booklets_coverage --out docs/runs/<folder>/coverage.json

Per booklet (<date>_<lang>.pdf): pages, the votes in the contents, the votes that pass every check (Vote.ok),
per vote the parts it has with their first and last page, and every problem text the parser names.

Per voting date, the cross-language check: the de, fr and it booklets of one date print the same votes with the
same parts, so they must agree on (1) the number of votes, (2) per vote, the parts that have pages, and (3) per
part, its start page within one page. A disagreement is a parser gap in at least one language, found without any
label: the three booklets check each other.

Nothing of the booklets' text is written (no titles, no page text): only numbers, part names and the parser's own
problem messages, so the output can be committed.
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import booklet, parse  # noqa: E402

LANGS = ("de", "fr", "it")
SEALED = {"2020-02-09", "2022-02-13", "2022-05-15"}  # never run, parsed or opened (session 11)


def cause(problem):
    """A problem message with its page numbers removed: the cause shared by booklets."""
    text = re.sub(r"\[\(.*\)\]", "[...]", problem)
    return re.sub(r"\d+", "N", text)


def check_booklet(args):
    pdf, cache_dir = args
    try:
        pages = parse.load_pages(Path(pdf), cache_dir=cache_dir)
    except Exception as e:  # the PDF cannot be read: every case of this booklet would get no text at all
        return {"booklet": Path(pdf).name, "pages": 0, "contents": False, "votes": [], "votes_ok": 0,
                "read_error": f"{type(e).__name__}: {cause(str(e))[:80]}"}
    parsed = booklet.parse(pages)
    votes = []
    for vote in (parsed.votes if parsed else []):
        parts = {k: [min(v), max(v)] for k, v in vote.parts.items() if v}
        votes.append({"ok": vote.ok, "parts": parts, "problems": list(vote.problems),
                      "usable_parts": sorted(usable_parts(pages, vote))})
    return {"booklet": Path(pdf).name, "pages": len(pages), "contents": parsed is not None,
            "votes": votes, "votes_ok": sum(v["ok"] for v in votes)}


def usable_parts(pages, vote):
    """Parts a routed claim could use: a part with pages and at least one paragraph (as section-route sends)."""
    return {k for k in booklet.PARTS if vote.parts.get(k) and booklet.part_paragraphs(pages, vote, k)}


def cross_language(results):
    """Per date: problems found by comparing its de, fr and it booklets."""
    by_date = defaultdict(dict)
    for r in results:
        date, lang = r["booklet"][:10].replace("_", "-"), r["booklet"][11:13]
        by_date[date][lang] = r
    out = {}
    for date, langs in sorted(by_date.items()):
        found = []
        if set(langs) != set(LANGS):
            found.append(f"languages present: {sorted(langs)}")
        counts = {lang: len(r["votes"]) for lang, r in langs.items()}
        if len(set(counts.values())) > 1:
            found.append(f"number of votes differs: {counts}")
        else:
            for i in range(next(iter(counts.values()), 0)):
                parts = {lang: set(r["votes"][i]["parts"]) for lang, r in langs.items()}
                if len({frozenset(p) for p in parts.values()}) > 1:
                    found.append(f"vote {i + 1}: parts differ: " + "; ".join(
                        f"{lang} {sorted(p)}" for lang, p in sorted(parts.items())))
                    continue
                for part in sorted(next(iter(parts.values()))):
                    starts = {lang: r["votes"][i]["parts"][part][0] for lang, r in langs.items()}
                    if max(starts.values()) - min(starts.values()) > 1:
                        found.append(f"vote {i + 1}: {part} starts differ: {starts}")
        out[date] = found
    return out


def tables(results, checks):
    """Counts by year and language, and the distinct causes with the booklets they affect."""
    by = defaultdict(lambda: Counter())
    for r in results:
        key = (r["booklet"][:4], r["booklet"][11:13])
        c = by[key]
        c["booklets"] += 1
        c["booklets complete"] += int(bool(r["votes"]) and r["votes_ok"] == len(r["votes"]))
        c["votes"] += len(r["votes"])
        c["votes ok"] += r["votes_ok"]
        c["votes with a usable part"] += sum(1 for v in r["votes"] if v["usable_parts"])
    causes = defaultdict(set)
    for r in results:
        if r.get("read_error"):
            causes["PDF text not readable: " + r["read_error"].split(":")[0]].add(r["booklet"])
        elif not r["contents"]:
            causes["no contents entry found"].add(r["booklet"])
        for v in r["votes"]:
            for p in v["problems"]:
                causes[cause(p)].add(r["booklet"])
    cross = defaultdict(set)
    for date, found in checks.items():
        for f in found:
            cross[cause(re.sub(r"\{.*\}", "{...}", f))].add(date)
    return ({f"{y} {lang}": dict(c) for (y, lang), c in sorted(by.items())},
            {k: sorted(v) for k, v in sorted(causes.items(), key=lambda kv: -len(kv[1]))},
            {k: sorted(v) for k, v in sorted(cross.items(), key=lambda kv: -len(kv[1]))})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--booklets", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--cache", default="/tmp/booklet-cache-coverage")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--include-sealed", action="store_true",
                    help="session 16 only: the sealed dates, opened once for the final run, are checked too")
    args = ap.parse_args()
    pdfs = sorted(p for p in args.booklets.glob("*.pdf")
                  if args.include_sealed or p.name[:10].replace("_", "-") not in SEALED)
    with ProcessPoolExecutor(args.workers) as pool:
        results = list(pool.map(check_booklet, [(str(p), args.cache) for p in pdfs]))
    checks = cross_language(results)
    by_year, causes, cross = tables(results, checks)
    total = Counter()
    for c in by_year.values():
        total.update(c)
    summary = {"booklets": len(results), "dates": len(checks), **dict(total),
               "dates with a cross-language disagreement": sum(1 for f in checks.values() if f)}
    out = {"summary": summary, "by_year_language": by_year, "causes": causes, "cross_language_causes": cross,
           "cross_language": checks, "booklets": results}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1))
    for k, v in causes.items():
        print(f"{len(v):3d} booklets  {k}")
    for k, v in cross.items():
        print(f"{len(v):3d} dates     {k}")


if __name__ == "__main__":
    main()
