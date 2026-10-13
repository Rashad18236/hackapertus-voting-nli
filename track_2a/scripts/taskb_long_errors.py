"""Session 12, step 3: task B errors on long references, per arm of one interleaved run. No model calls.

Run from track_2a/:

    python3 scripts/taskb_long_errors.py --run docs/runs/<run> --cases output/devB/cases.jsonl \\
        --expected output/devB/expected-labels.jsonl --arms today B-R H B-BM25 [--json out.json]

Per arm: wrong answers on references over 3,000 characters (the ones T's rule cuts) and on the others, the neutral
cases called contradiction among them (T's main error on val), same-language and cross-language separately, and the
fixes and breaks against the first arm. Only ids and counts are written.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import taskb_context  # noqa: E402


def load(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--cases", type=Path, required=True)
    ap.add_argument("--expected", type=Path, required=True)
    ap.add_argument("--arms", nargs="+", required=True)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()
    cases = {c["id"]: c for c in load(args.cases)}
    gold = {e["id"]: e["label"] for e in load(args.expected) if e["id"] in cases}
    long = {i: taskb_context.is_long(cases[i]["reference"]["text"], "cut4-t") for i in gold}
    cross = {i: cases[i]["claim"]["language"] != cases[i]["reference"]["language"] for i in gold}
    preds = {a: {p["id"]: p["label"] for p in load(args.run / a / "predictions.jsonl")} for a in args.arms}
    out = {}
    base = args.arms[0]
    for a in args.arms:
        p = preds[a]
        row = {}
        for name, sel in (("long", [i for i in gold if long[i]]), ("short", [i for i in gold if not long[i]])):
            wrong = [i for i in sel if p.get(i) != gold[i]]
            n_to_c = [i for i in sel if gold[i] == 1 and p.get(i) == 2]
            row[name] = {"cases": len(sel), "wrong": len(wrong),
                         "neutral_called_contradiction": len(n_to_c),
                         "neutral_called_contradiction_same_language": sum(not cross[i] for i in n_to_c),
                         "neutral_called_contradiction_cross_language": sum(cross[i] for i in n_to_c),
                         "wrong_ids": sorted(wrong)}
        if a != base:
            row["fixes_vs_" + base] = sorted(i for i in gold if p.get(i) == gold[i] and preds[base].get(i) != gold[i])
            row["breaks_vs_" + base] = sorted(i for i in gold if p.get(i) != gold[i] and preds[base].get(i) == gold[i])
        out[a] = row
        print(f"{a}: long {row['long']['wrong']} wrong of {row['long']['cases']} "
              f"(neutral -> contradiction {row['long']['neutral_called_contradiction']}: "
              f"same {row['long']['neutral_called_contradiction_same_language']}, "
              f"cross {row['long']['neutral_called_contradiction_cross_language']}); short {row['short']['wrong']} wrong"
              + (f"; fixes {len(row['fixes_vs_' + base])} / breaks {len(row['breaks_vs_' + base])}" if a != base else ""))
    if args.json:
        args.json.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
