"""Does a change to src/booklet.py change how a booklet is parsed? (session 8, no model calls)

Run from track_2a/:

    python3 scripts/parse_equivalence.py save --out OLD.json        # with the code before a change
    python3 scripts/parse_equivalence.py compare --old OLD.json [--json RESULT.json]   # after it

For every PDF in --booklets (default output/booklets_dev: the 45 booklets of the dev and val cases, 44 of
them dev booklets) the full parse output of src/booklet.py: per vote its title, contents entry, ok,
problems, the pages of every part, the recommendation boxes (page and verbatim text), and every paragraph
booklet.part_paragraphs gives for every part (page and verbatim text), the text section-route sends.
compare lists every booklet whose output differs and exits 1 if any does.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import booklet, parse  # noqa: E402


def parse_output(pdf):
    pages = parse.load_pages(pdf)
    parsed = booklet.parse(pages)
    if parsed is None:
        return None
    return [{"title": v.title, "entry": v.entry, "ok": v.ok, "problems": v.problems,
             "parts": {k: list(p) for k, p in v.parts.items()},
             "boxes": {k: [list(b) for b in boxes] for k, boxes in v.boxes.items()},
             "paragraphs": {k: [list(p) for p in booklet.part_paragraphs(pages, v, k)] for k in booklet.PARTS}}
            for v in parsed.votes]


def main():
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
    outputs = {pdf.name: parse_output(pdf) for pdf in sorted(Path(args.booklets).glob("*.pdf"))}
    if args.command == "save":
        Path(args.out).write_text(json.dumps(outputs, ensure_ascii=False) + "\n", encoding="utf-8")
        votes = sum(len(v or []) for v in outputs.values())
        print(f"saved the parse of {len(outputs)} booklets ({votes} votes) to {args.out}")
        return 0
    old = json.loads(Path(args.old).read_text(encoding="utf-8"))
    # JSON round trip, so tuples and lists compare alike
    new = json.loads(json.dumps(outputs, ensure_ascii=False))
    differ = sorted(n for n in set(old) | set(new) if old.get(n) != new.get(n))
    detail = {}
    for n in differ:
        a, b = old.get(n) or [], new.get(n) or []
        detail[n] = [{"vote": i, "fields": sorted(k for k in set(x) | set(y) if x.get(k) != y.get(k))}
                     for i, (x, y) in enumerate(zip(a, b)) if x != y] or [{"votes": [len(a), len(b)]}]
    result = {"booklets": len(new), "votes": sum(len(v or []) for v in new.values()),
              "votes_ok": sum(sum(x["ok"] for x in v or []) for v in new.values()),
              "booklets_differ": len(differ), "differences": detail}
    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=1, ensure_ascii=False)[:3000])
    print("parse identical" if not differ else "PARSE DIFFERS")
    return 1 if differ else 0


if __name__ == "__main__":
    sys.exit(main())
