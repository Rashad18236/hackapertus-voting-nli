"""What Apertus did in its parsing roles in one arm of a run (session 11, step 3). No model calls.

Run from track_2a/:

    python3 scripts/ap_summary.py --arm docs/runs/<run>/AP-all [--out <file.json>]

From the arm's raw answers (src/cli.ap_route records every parsing call): how many claim and contents calls were
made, their tokens (input and output, apart from the answer calls'), unreadable or failed parsing answers, how
often Apertus's part equals the rules' part where the rules name one, how often it says "none", how often its
contents reading placed the case's vote (and passed the heading checks), and the path each case took.
"""

import argparse
import json
from collections import Counter
from pathlib import Path


def summarise(arm):
    rows = [json.loads(line) for line in (Path(arm) / "raw_answers.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()]
    n = len(rows)
    calls = Counter()
    ap_in = ap_out = 0
    problems = Counter()
    agree = disagree = rules_none_ap_part = ap_none = 0
    confusion = Counter()
    vote_found = structure_asked = 0
    paths = Counter()
    for r in rows:
        for c in r.get("ap_calls", []):
            calls[c.get("version")] += 1
            if c.get("error"):
                problems["failed call"] += 1
            if c.get("parse_reason"):
                problems[c["parse_reason"]] += 1
        ap_in += (r.get("ap_tokens") or [0, 0])[0]
        ap_out += (r.get("ap_tokens") or [0, 0])[1]
        part = r.get("ap_part")
        if part:
            rules, apertus = part.get("rules"), part.get("apertus")
            confusion[f"{rules} -> {apertus}"] += 1
            if apertus is None:
                ap_none += 1
            if rules is not None:
                agree += rules == apertus
                disagree += rules != apertus
            elif apertus is not None:
                rules_none_ap_part += 1
        if r.get("ap_structure") is not None:
            structure_asked += 1
            vote_found += bool(r["ap_structure"].get("vote_found"))
        paths[r.get("route") or r.get("context") or "?"] += 1
    return {"cases": n, "calls": dict(calls), "parsing_problems": dict(problems),
            "parsing_tokens_per_case": {"input": round(ap_in / n, 1) if n else 0, "output": round(ap_out / n, 1) if n else 0},
            "part": {"asked": sum(confusion.values()), "rules_named_a_part": agree + disagree,
                     "apertus_equal_to_rules": agree, "apertus_different": disagree,
                     "share_equal": round(agree / (agree + disagree), 3) if agree + disagree else None,
                     "rules_none_apertus_part": rules_none_ap_part, "apertus_none": ap_none,
                     "rules_to_apertus": dict(confusion.most_common())},
            "structure": {"cases_asked": structure_asked, "vote_found_and_checked": vote_found},
            "paths": dict(paths.most_common())}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    result = summarise(args.arm)
    text = json.dumps(result, indent=1)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
