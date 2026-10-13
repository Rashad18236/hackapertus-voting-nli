"""AP-claim's rewritten statement as the search text of a cut part (session 11, step 3b). No model calls.

Run from track_2a/ after step 3 run 1 (its AP-all arm asked Apertus for every claim's part and statement):

    EMBED_MODEL_DIR=models/multilingual-e5-small python3 scripts/ap_claim_search.py \\
        --run docs/runs/<run 1 dev folder> --cases output/devA/cases.jsonl \\
        --expected output/devA/expected-labels.jsonl --data-dir output/data_dev \\
        [--run <probe folder> --cases ... --expected ... --data-dir ...] --out <file.json>

Cases looked at: routed today (the rules name a part and the parser finds it), the part longer than section-route's
MAX_CHARS, so cut to the TOP_K paragraphs most similar to the search text, and cross-language (claim and booklet in
different languages). For each, the 8 paragraphs are chosen twice: with the claim (today) and with Apertus's
statement (the claim without its opening, in the booklet's language). Two measures:

- as written: is the first paragraph cited in today's correct answer among the 8 chosen with the statement? (It is
  among today's 8 by construction, so this measure can only stay equal or fall; reported for completeness.)
- gold: for entailment and contradiction cases, is a paragraph matching the gold passage (the scorer's rule:
  partial ratio >= 90 after normalising) among the 8? Cases gained (only with the statement) and lost (only with
  the claim); the net gain decides whether run 4 is worth its calls (decisions file).

Nothing of the booklets' or the claims' text is written: case ids and counts only.
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from src import booklet, parse  # noqa: E402
from src.contexts import section_route  # noqa: E402

FIRST_CITED = re.compile(r'"paragraphs"\s*:\s*\[\s*(\d+)')


def load(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def first_cited(answer):
    try:
        cited = json.loads(answer).get("paragraphs") or []
        return int(cited[0]) if cited else None
    except (ValueError, TypeError, AttributeError, IndexError):
        m = FIRST_CITED.search(answer or "")
        return int(m.group(1)) if m else None


def one_run(run, cases_file, expected_file, data_dir):
    import evidence_loss as el
    cases = {c["id"]: c for c in load(cases_file)}
    expected = {e["id"]: e for e in load(expected_file)}
    today = {r["id"]: r for r in load(Path(run) / "today" / "raw_answers.jsonl")}
    today_pred = {p["id"]: p for p in load(Path(run) / "today" / "predictions.jsonl")}
    ap = {r["id"]: r for r in load(Path(run) / "AP-all" / "raw_answers.jsonl")}
    rows = []
    for cid, case in cases.items():
        if case["claim"]["language"] == case["booklet"]["language"]:
            continue
        statement = ((ap.get(cid) or {}).get("ap_part") or {}).get("statement")
        pages = parse.load_pages(Path(data_dir) / case["booklet"]["path"])
        routed = section_route.route(pages, case["vote"], case["claim"]["text"])
        if routed is None:
            continue
        part, chosen = routed
        found = section_route.find(section_route.parsed_booklet(pages), case["vote"])
        whole = booklet.part_paragraphs(pages, found, part)
        if sum(len(section_route.display(t)) for _, t in whole) <= section_route.MAX_CHARS:
            continue  # not cut: the search text changes nothing
        row = {"id": cid, "part": part, "label": expected[cid]["label"], "statement": statement is not None}
        if statement:
            with_statement = section_route.most_similar(whole, statement)
        else:
            with_statement = chosen  # no statement: the case would keep today's search
        if expected[cid]["label"] in (0, 2):
            gold = el.norm(expected[cid]["reference"])
            row["gold_in_claim_8"] = any(el.item_matches(t, gold) for _, t in chosen)
            row["gold_in_statement_8"] = any(el.item_matches(t, gold) for _, t in with_statement)
        correct = today_pred.get(cid, {}).get("label") == expected[cid]["label"]
        n = first_cited((today.get(cid) or {}).get("answer"))
        if correct and n and today.get(cid, {}).get("route") == part and 1 <= n <= len(chosen):
            row["first_cited_in_statement_8"] = chosen[n - 1] in with_statement
        rows.append(row)
    return rows


def summarise(rows):
    gold = [r for r in rows if "gold_in_claim_8" in r]
    written = [r for r in rows if "first_cited_in_statement_8" in r]
    gained = [r["id"] for r in gold if r["gold_in_statement_8"] and not r["gold_in_claim_8"]]
    lost = [r["id"] for r in gold if r["gold_in_claim_8"] and not r["gold_in_statement_8"]]
    return {"cut_cross_language_cases": len(rows), "with_statement": sum(r["statement"] for r in rows),
            "as_written": {"correct_answers_with_a_cited_paragraph": len(written),
                           "first_cited_among_claim_8": len(written),
                           "first_cited_among_statement_8": sum(r["first_cited_in_statement_8"] for r in written)},
            "gold": {"cases": len(gold), "gold_among_claim_8": sum(r["gold_in_claim_8"] for r in gold),
                     "gold_among_statement_8": sum(r["gold_in_statement_8"] for r in gold),
                     "gained": gained, "lost": lost, "net_gain": len(gained) - len(lost)}}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", action="append", required=True)
    ap.add_argument("--cases", action="append", required=True)
    ap.add_argument("--expected", action="append", required=True)
    ap.add_argument("--data-dir", action="append", required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    result, everything = {}, []
    for run, cases, expected, data_dir in zip(args.run, args.cases, args.expected, args.data_dir):
        rows = one_run(run, cases, expected, data_dir)
        everything += rows
        result[Path(run).name] = summarise(rows) | {"rows": rows}
    result["all"] = summarise(everything)
    args.out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(result["all"], indent=1))


if __name__ == "__main__":
    main()
