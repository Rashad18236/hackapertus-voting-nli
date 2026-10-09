"""Check every task A evidence item of a saved run against the booklet page it names (no model calls).

Run from track_2a/ (booklets from scripts/fetch_dev_booklets.py):

    python3 scripts/check_evidence.py --run docs/runs/<comparison>/<arm> [--run ...] \\
        --cases data/dev/cases.jsonl --booklets output/booklets_dev [--json OUT]

Rules, per response (the contract, docs/official_contract.md, and the team's evidence rules):

1. verbatim: each item's text, normalised as the starter's scorer normalises (NFKC, soft hyphens
   dropped, words hyphenated across a line break joined, whitespace collapsed, lower case), is a
   substring of the normalised text of the page the item names. An item that fails this but is a
   substring once only whitespace and case are normalised (no hyphen joining) is reported
   separately as "verbatim only without hyphen joining": still copied from the page, but cut where
   the scorer's normalisation joins a hyphenated word. For an item that breaks the rule, the report
   says whether it is a substring once the lines src/booklet.py drops from paragraphs (lone hyphens
   and section signs, page numbers, running headers) are removed from the page too, and gives its
   partial ratio against the page.
2. page: an int >= 1 that exists in the booklet.
3. length: at most 5,000 characters.
4. count: at most five items.
5. neutral: a label-1 answer has no evidence.
Also counted, as warnings: a label 0 or 2 answer without evidence (the contract asks for at least one
item; the starter's scorer then finds nothing), and the same text twice in one response.

Exits 1 if any rule is broken. The normalisation re-implements the starter's evaluate.py (commit
559b598), as scripts/evidence_loss.py does; the starter has no licence, so its code is not copied.
"""

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rapidfuzz import fuzz  # noqa: E402

from src import booklet, parse  # noqa: E402

MAX_CHARS = 5000
MAX_ITEMS = 5
RULES = ("verbatim", "page", "length", "count", "neutral")


def norm(text):
    """The starter's normalisation (re-implemented)."""
    text = unicodedata.normalize("NFKC", text).replace("\u00ad", "")
    text = re.sub(r"(\w) ?-\s*\n\s*(\w)", r"\1\2", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def loose(text):
    """Whitespace and case only (no hyphen joining)."""
    text = unicodedata.normalize("NFKC", text).replace("\u00ad", "")
    return re.sub(r"\s+", " ", text).strip().lower()


def check_run(run_dir, cases, booklets):
    preds = [json.loads(line) for line in (run_dir / "predictions.jsonl").read_text(encoding="utf-8").splitlines()
             if line.strip()]
    violations = {rule: [] for rule in RULES}
    notes = {"verbatim only without hyphen joining": [], "label 0/2 without evidence": [], "duplicate item": []}
    stats = Counter()
    page_cache = {}
    for pred in preds:
        case = cases.get(pred["id"])
        if not case or "booklet" not in case:
            continue
        stats["task A responses"] += 1
        evidence, label = pred.get("evidence") or [], pred.get("label")
        stats[f"label {label}"] += 1
        if label == 1 and evidence:
            violations["neutral"].append(f"{pred['id']}: {len(evidence)} items on a neutral answer")
        if label in (0, 2) and not evidence:
            notes["label 0/2 without evidence"].append(pred["id"])
        if len(evidence) > MAX_ITEMS:
            violations["count"].append(f"{pred['id']}: {len(evidence)} items")
        texts = [item.get("text") for item in evidence]
        if len(set(texts)) < len(texts):
            notes["duplicate item"].append(pred["id"])
        name = Path(case["booklet"]["path"]).name
        if name not in page_cache:
            page_cache[name] = parse.load_pages(booklets / name)
        pages = page_cache[name]
        for i, item in enumerate(evidence, start=1):
            stats["items"] += 1
            text, page = item.get("text") or "", item.get("page")
            where = f"{pred['id']} item {i} (page {page})"
            if len(text) > MAX_CHARS:
                violations["length"].append(f"{where}: {len(text)} characters")
            if not (isinstance(page, int) and not isinstance(page, bool) and page in pages):
                violations["page"].append(f"{where}: page not in the booklet ({len(pages)} pages)")
                continue
            if norm(text) and norm(text) in norm(pages[page]):
                stats["items verbatim"] += 1
            elif loose(text) and loose(text) in loose(pages[page]):
                notes["verbatim only without hyphen joining"].append(where)
                stats["items verbatim without hyphen joining"] += 1
            else:
                elsewhere = [p for p, t in pages.items() if p != page and norm(text) in norm(t)]
                cleaned = norm("\n".join(booklet._clean_lines(pages[page])))
                why = ("a substring once the lines the parser drops are removed" if norm(text) in cleaned
                       else "not a substring even then")
                ratio = fuzz.partial_ratio(norm(text), norm(pages[page]))
                violations["verbatim"].append(f"{where}: not a contiguous part of its page; {why}; partial ratio "
                                              f"{ratio:.1f}" + (f"; found on page(s) {elsewhere}" if elsewhere else "")
                                              + f"; text starts {text[:60]!r}")
    return {"run": str(run_dir), "stats": dict(stats), "violations": violations, "notes": notes}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, action="append", required=True, help="a run folder with predictions.jsonl")
    ap.add_argument("--cases", type=Path, default=ROOT / "data" / "dev" / "cases.jsonl")
    ap.add_argument("--booklets", type=Path, default=ROOT / "output" / "booklets_dev")
    ap.add_argument("--json", type=Path, help="write the full report here")
    args = ap.parse_args()
    cases = {c["id"]: c for c in map(json.loads, args.cases.read_text(encoding="utf-8").splitlines())}
    reports = [check_run(run, cases, args.booklets) for run in args.run]
    broken = 0
    for r in reports:
        print(f"== {r['run']}")
        print("   " + ", ".join(f"{k}: {v}" for k, v in sorted(r["stats"].items())))
        for rule in RULES:
            found = r["violations"][rule]
            broken += len(found)
            print(f"   {rule}: {'PASS' if not found else f'{len(found)} violations'}")
            for line in found:
                print(f"      {line}")
        for note, found in r["notes"].items():
            if found:
                print(f"   (note) {note}: {len(found)}: {', '.join(found[:20])}{' ...' if len(found) > 20 else ''}")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(reports, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    sys.exit(1 if broken else 0)


if __name__ == "__main__":
    main()
