"""Task B selectors against B-cut4 on the long dev references (session 11, step 6a). No model calls.

Run from track_2a/ (e5 and its 8-bit export in models/multilingual-e5-small):

    EMBED_MODEL_DIR=models/multilingual-e5-small python3 scripts/taskb_selectors.py --cases output/devB/cases.jsonl \\
        --out <file.json>

For every task B case whose reference is over 3,000 characters (the cases B-cut4 cuts), each selector picks 4
paragraphs (src/taskb_context.py): E (B-cut4 as it is), Q (e5 quantised to 8 bits), T (e5 on the first 300
characters of each paragraph), L (shared character 4-grams and numbers, no model), H (L for a claim in the
reference's language, else T). Reported per selector: how many of E's 4 paragraphs it also picks (mean, and the
share of cases with all 4), and its CPU seconds per cut case in one process, model loading included (each selector
in a fresh process). The local time per case of the image comes from scripts/local_time.py.
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MODES = ("cut4", "cut4-q", "cut4-t", "cut4-l", "cut4-h")


def picks(mode, cases_file):
    from src import taskb_context
    cases = [json.loads(line) for line in Path(cases_file).read_text(encoding="utf-8").splitlines() if line.strip()]
    long_cases = [c for c in cases if taskb_context.is_long(c["reference"]["text"], "cut4")]
    start = time.perf_counter()
    out = {}
    for c in long_cases:
        same = c["claim"]["language"] == c["reference"]["language"]
        _, paragraphs = taskb_context.cut_paragraphs(c["reference"]["text"], c["claim"]["text"], mode, same)
        out[c["id"]] = paragraphs
    return out, time.perf_counter() - start


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cases", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--mode", choices=MODES)
    args = ap.parse_args()
    if args.mode:  # the child: one selector in a fresh process
        chosen, seconds = picks(args.mode, args.cases)
        print(json.dumps({"mode": args.mode, "seconds": seconds, "chosen": chosen}, ensure_ascii=False))
        return
    results = {}
    for mode in MODES:
        out = subprocess.run([sys.executable, __file__, "--cases", str(args.cases), "--out", str(args.out),
                              "--mode", mode], capture_output=True, text=True, check=True)
        results[mode] = json.loads(out.stdout.strip().splitlines()[-1])
    reference = results["cut4"]["chosen"]
    n = len(reference)
    summary = {"cases_cut": n}
    for mode in MODES:
        chosen = results[mode]["chosen"]
        overlap = [len(set(chosen[i]) & set(reference[i])) for i in reference]
        summary[mode] = {"mean_overlap_with_E": round(sum(overlap) / n, 3) if n else None,
                         "all_4_equal": round(sum(1 for o in overlap if o == len(reference_i)) / n, 3)
                         if n and (reference_i := next(iter(reference.values()))) is not None else None,
                         "cpu_seconds_per_cut_case": round(results[mode]["seconds"] / n, 4) if n else None,
                         "cpu_seconds_total": round(results[mode]["seconds"], 2)}
        summary[mode]["all_4_equal"] = round(sum(1 for i in reference if set(chosen[i]) == set(reference[i])) / n, 3)
        print(mode, summary[mode], flush=True)
    args.out.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
