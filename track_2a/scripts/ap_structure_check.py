"""AP-structure against the Python parser on every booklet of the coverage set (session 11, step 3a). Model calls:
one per booklet (src/ap_parse.py), paced by LLM_MIN_INTERVAL.

Run from track_2a/ (.env for the endpoint; booklets as for scripts/parser_coverage.py):

    LLM_MIN_INTERVAL=1 python3 scripts/ap_structure_check.py --booklets /home/user/booklets_coverage \\
        --coverage docs/runs/<step 1 folder>/coverage_after.json --out docs/runs/<folder>

Per booklet, Apertus reads the contents pages (the first six, as the parser does) and lists each vote with the start
pages of its summary, detailed section, arguments and law text. Compared with the parser:

- votes that pass the Python parser on a date without a cross-language disagreement: the share of votes where all of
  Apertus's pages equal the parser's, and the share per field (the parser's pages: its contents entry; the older
  layout has no per-part contents entries, so its votes are reported apart, compared on the law page only);
- votes the Python parser fails: whether Apertus's entry passes the same heading checks (src/ap_parse.py
  booklet_from_entries -> booklet._parse_vote) and which parts it makes valid;
- tokens per booklet (input and output) and the backend of every call.

Votes are matched by their order in the booklet (Apertus's entries sorted by their summary page). Nothing of the
booklets' text is written (no titles): numbers, field names and the backend only.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import ap_parse, booklet, env, parse  # noqa: E402

FIELDS = ("summary", "detail", "arguments", "law")
SEALED = {"2020-02-09", "2022-02-13", "2022-05-15"}


def parser_fields(vote):
    """The parser's start pages of a vote, from its contents entry (current layout) or its parts (older layout)."""
    e = vote.entry
    if "block" in e:
        law = vote.parts.get("law") or []
        return {"law": law[0] if law else None}, "older"
    return {"summary": e["summary"][0] if "summary" in e else None, "detail": e.get("detail"),
            "arguments": e.get("arguments"), "law": e.get("law")}, "current"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--booklets", type=Path, required=True)
    ap.add_argument("--coverage", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--cache", default="/tmp/booklet-cache-coverage")
    args = ap.parse_args()
    env.load_env_file()
    coverage = json.loads(args.coverage.read_text(encoding="utf-8"))
    disagree = {d for d, found in coverage["cross_language"].items() if found}
    rows, compared, failed_votes = [], [], []
    for pdf in sorted(args.booklets.glob("*.pdf")):
        date = pdf.name[:10].replace("_", "-")
        if date in SEALED:
            continue
        pages = parse.load_pages(pdf, cache_dir=args.cache)
        parsed = booklet.parse(pages)
        entries, call = ap_parse.structure(pages)
        endpoint = call.get("endpoint") or {}
        row = {"booklet": pdf.name, "input_tokens": call.get("input_tokens", 0),
               "output_tokens": call.get("output_tokens", 0), "error": call.get("error"),
               "parse_reason": call.get("parse_reason"), "backend": endpoint.get("system_fingerprint"),
               "votes_parser": len(parsed.votes) if parsed else 0, "votes_apertus": len(entries or [])}
        ordered = sorted((e for e in entries or [] if isinstance(e.get("summary"), int)), key=lambda e: e["summary"])
        ap_booklet = ap_parse.booklet_from_entries(pages, entries)
        for i, vote in enumerate(parsed.votes if parsed else []):
            mine, layout = parser_fields(vote)
            theirs = ordered[i] if i < len(ordered) else None
            if vote.ok and date not in disagree:
                same = {f: (theirs is not None and theirs.get(f) == v) for f, v in mine.items()}
                compared.append({"booklet": pdf.name, "vote": i + 1, "layout": layout, "same": same,
                                 "all_same": all(same.values()), "matched": theirs is not None})
            elif not vote.ok:
                checked = ap_booklet.votes[i] if ap_booklet is not None and i < len(ap_booklet.votes) else None
                failed_votes.append({"booklet": pdf.name, "vote": i + 1, "layout": layout,
                                     "parser_valid": sorted(vote.valid),
                                     "apertus_ok": bool(checked and checked.ok),
                                     "apertus_valid": sorted(checked.valid) if checked else []})
        rows.append(row)
        print(f"{pdf.name}: {row['votes_apertus']} votes from Apertus, {row['votes_parser']} from the parser, "
              f"{row['input_tokens']} + {row['output_tokens']} tokens", flush=True)

    def share(items, key):
        return round(sum(1 for x in items if key(x)) / len(items), 3) if items else None

    current = [c for c in compared if c["layout"] == "current"]
    older = [c for c in compared if c["layout"] == "older"]
    summary = {
        "booklets": len(rows), "calls_failed": sum(1 for r in rows if r["error"]),
        "answers_unreadable": sum(1 for r in rows if r["parse_reason"]),
        "votes_compared_current_layout": len(current),
        "all_pages_equal_current_layout": share(current, lambda c: c["all_same"]),
        "per_field_equal_current_layout": {f: share(current, lambda c, f=f: c["same"].get(f)) for f in FIELDS},
        "votes_compared_older_layout": len(older),
        "law_page_equal_older_layout": share(older, lambda c: c["same"].get("law")),
        "votes_parser_fails": len(failed_votes),
        "parser_fails_apertus_passes_all_checks": sum(1 for f in failed_votes if f["apertus_ok"]),
        "parser_fails_apertus_adds_valid_parts": sum(1 for f in failed_votes
                                                    if set(f["apertus_valid"]) - set(f["parser_valid"])),
        "vote_count_equal": share(rows, lambda r: r["votes_apertus"] == r["votes_parser"]),
        "tokens_per_booklet": {"input": round(sum(r["input_tokens"] for r in rows) / len(rows), 1),
                               "output": round(sum(r["output_tokens"] for r in rows) / len(rows), 1)},
        "backends": dict(Counter(r["backend"] for r in rows)),
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "ap_structure_check.json").write_text(json.dumps(
        {"summary": summary, "booklets": rows, "compared": compared, "parser_fails": failed_votes},
        indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
