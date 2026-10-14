"""Session 13, step 2, B3 offline: how many long task B references get other paragraphs when selector T embeds each
paragraph as "<first line of the reference>: <paragraph>" (mode cut4-tf) instead of the paragraph alone (cut4-t,
today's default). No endpoint calls; e5 runs locally.

Run from track_2a/ (EMBED_MODEL_DIR set as for the CLI):

    python3 scripts/taskb_b3_picks.py --cases output/devB/cases.jsonl output/valB/cases.jsonl --out FILE.json

A reference counts as long when today's rule cuts it (over 3,000 characters and more than 4 paragraphs); a pick
changes when the set of 4 kept paragraphs differs.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import taskb_context  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--cases", nargs="+", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    result = {"rule": "B3 is an arm if at least 10 % of long references change a pick (session 13 instruction)",
              "sets": {}}
    total_long = total_changed = 0
    for path in args.cases:
        long_cases = changed = 0
        ids = []
        for line in open(path, encoding="utf-8"):
            case = json.loads(line)
            reference, claim = case["reference"]["text"], case["claim"]["text"]
            first, paragraphs = taskb_context.split(reference)
            if not (taskb_context.is_long(reference, "cut4-t") and len(paragraphs) > taskb_context.CUT4_TOP_K):
                continue
            long_cases += 1
            today = taskb_context.cut_paragraphs(reference, claim, "cut4-t")[1]
            b3 = taskb_context.cut_paragraphs(reference, claim, "cut4-tf")[1]
            if set(today) != set(b3):
                changed += 1
                ids.append(case["id"])
        result["sets"][path] = {"long_references": long_cases, "pick_changed": changed,
                                "share": round(changed / long_cases, 4) if long_cases else None, "ids": ids}
        total_long, total_changed = total_long + long_cases, total_changed + changed
        print(f"{path}: {changed} of {long_cases} long references change a pick", flush=True)
    result["total"] = {"long_references": total_long, "pick_changed": total_changed,
                       "share": round(total_changed / total_long, 4) if total_long else None}
    result["b3_is_an_arm"] = bool(total_long) and total_changed / total_long >= 0.10
    Path(args.out).write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(result["total"]), "B3 is an arm:", result["b3_is_an_arm"])


if __name__ == "__main__":
    main()
