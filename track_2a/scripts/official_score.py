"""REF SCORE: our estimate of the organisers' score (docs/official_scoring.md), with fixed reference "best" values.

    Score = 0.4 x S_B + 0.6 x S_A
    S_A = 0.50 Macro-F1 + 0.20 Evidence + 0.15 T + 0.15 K
    S_B = 0.70 Macro-F1                 + 0.15 T + 0.15 K
    K = best tokens per case / own tokens per case;  T = best local time per case / own local time per case

The other teams' best values are unknown, so the reference values below were fixed at the start of session 10,
before any measurement; ratios are capped at 1. Tokens per case = input + output tokens (the stricter reading).
A REF SCORE only ranks our own versions; it is not the official score.

Run from track_2a/ with the numbers of a run (local time from scripts/local_time.py):

    python3 scripts/official_score.py --macro-a 0.980 --evidence-a 0.980 --tokens-a 1252 --time-a 0.30 \\
        --macro-b 0.967 --tokens-b 1240 --time-b 0.02 [--json out.json]

Either task may be left out; then only its own S is printed and the total is not.
"""

import argparse
import json
import sys

REF_TOKENS = {"A": 600.0, "B": 800.0}       # tokens per case (input + output)
REF_TIME_S = {"A": 0.05, "B": 0.005}       # local time per case, seconds
MIN_MACRO = {"A": 0.60, "B": 0.75}         # below either, the whole submission is invalid (our bar for B: 0.75)
WEIGHTS = {"A": {"macro": 0.50, "evidence": 0.20, "T": 0.15, "K": 0.15},
           "B": {"macro": 0.70, "evidence": 0.00, "T": 0.15, "K": 0.15}}


def ratio(best, own):
    """best / own, capped at 1; 0 when own is missing or not positive."""
    if own is None or own <= 0:
        return 0.0
    return min(1.0, best / own)


def task_score(task, macro, tokens, time_s, evidence=0.0):
    """The parts and S for one task ("A" or "B")."""
    w = WEIGHTS[task]
    K = ratio(REF_TOKENS[task], tokens)
    T = ratio(REF_TIME_S[task], time_s)
    evidence = evidence if task == "A" else 0.0
    S = w["macro"] * macro + w["evidence"] * evidence + w["T"] * T + w["K"] * K
    return {"task": task, "macro_f1": macro, "evidence": evidence if task == "A" else None,
            "tokens_per_case": tokens, "local_time_s": time_s, "K": round(K, 4), "T": round(T, 4),
            "S": round(S, 4), "valid": macro >= MIN_MACRO[task]}


def total(s_a, s_b):
    """Score = 0.4 S_B + 0.6 S_A; 0 when either task is below its minimum (the submission is invalid)."""
    if not (s_a["valid"] and s_b["valid"]):
        return 0.0
    return round(0.4 * s_b["S"] + 0.6 * s_a["S"], 4)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for task in ("a", "b"):
        ap.add_argument(f"--macro-{task}", type=float)
        ap.add_argument(f"--tokens-{task}", type=float, help="input + output tokens per case")
        ap.add_argument(f"--time-{task}", type=float, help="local time per case, seconds")
    ap.add_argument("--evidence-a", type=float, default=0.0)
    ap.add_argument("--json", help="also write the result as JSON")
    args = ap.parse_args()
    out = {"reference": {"tokens_per_case": REF_TOKENS, "local_time_s": REF_TIME_S}}
    if args.macro_a is not None:
        out["A"] = task_score("A", args.macro_a, args.tokens_a, args.time_a, args.evidence_a)
    if args.macro_b is not None:
        out["B"] = task_score("B", args.macro_b, args.tokens_b, args.time_b)
    if "A" in out and "B" in out:
        out["score"] = total(out["A"], out["B"])
    for task in ("A", "B"):
        if task in out:
            p = out[task]
            ev = f", evidence {p['evidence']:.3f}" if task == "A" else ""
            print(f"S_{task} = {p['S']:.4f}  (Macro-F1 {p['macro_f1']:.3f}{ev}, K {p['K']:.3f} at "
                  f"{p['tokens_per_case']} tokens, T {p['T']:.3f} at {p['local_time_s']} s{'' if p['valid'] else ', INVALID'})")
    if "score" in out:
        print(f"REF SCORE = {out['score']:.4f}")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=1)
            f.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
