"""Build the generated parts of docs/baseline_review.md.

Run from track_2a/:  python3 scripts/baseline_review.py
Reads the dev split, docs/self_checks.md and the baseline run in docs/runs/.
The written analysis (error patterns, surprises) is added by hand between the
ANALYSIS markers and is kept when the script is rerun.
"""

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
RUN = "baseline-v0"
NAMES = {0: "entailment", 1: "neutral", 2: "contradiction", None: "none (failure)"}
REF_CHARS = 700
SEED = 42
START, END = "<!-- ANALYSIS START -->", "<!-- ANALYSIS END -->"


def load(path):
    return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]


def quote_block(text):
    return "\n".join("> " + line if line.strip() else ">" for line in text.splitlines())


def shorten(text, n=REF_CHARS):
    return text if len(text) <= n else text[:n].rstrip() + f" [...] ({len(text)} characters in total)"


def main():
    inputs = {r["id"]: r for r in load(ROOT / "data/dev_inputs.jsonl")}
    gold = {g["id"]: g for g in load(ROOT / "data/dev_gold.jsonl")}
    preds = {p["id"]: p for p in load(DOCS / f"runs/{RUN}_dev_predictions.jsonl")}
    raws = {r["id"]: r for r in load(DOCS / f"runs/{RUN}_dev_raw_answers.jsonl")}
    rng = random.Random(SEED)

    out = ["# Baseline review (beginner task, dev split)", "",
           f"Run `{RUN}`, prompt `v1-json`. Numbers: `docs/results.md`. "
           "Generated parts by `scripts/baseline_review.py`; analysis written by hand.", ""]

    out += ["## 1. Self-checks", ""]
    out += (DOCS / "self_checks.md").read_text(encoding="utf-8").split("\n", 3)[3].strip().splitlines()
    out += [""]

    old = (DOCS / "baseline_review.md").read_text(encoding="utf-8") if (DOCS / "baseline_review.md").exists() else ""
    analysis = old[old.index(START):old.index(END) + len(END)] if START in old else f"{START}\n\n{END}"
    out += [analysis, ""]

    out += ["## 4. Twenty random dev rows", "",
            f"Drawn with seed {SEED}. References are cut after {REF_CHARS} characters; "
            "the full text is in `data/dev_inputs.jsonl`.", ""]
    for case_id in sorted(rng.sample(sorted(inputs), 20)):
        g = gold[case_id]
        out += [f"### {case_id}: gold {g['label']} ({g['label_name']}), "
                f"claim {g['claim_language']}, reference {g['reference_language']}", "",
                f"**Claim:** {inputs[case_id]['claim']['text']}", "", "**Reference:**", "",
                quote_block(shorten(inputs[case_id]["reference"]["text"])), ""]

    wrong = sorted(i for i in preds if preds[i].get("label") != gold[i]["label"])
    right = sorted(i for i in preds if preds[i].get("label") == gold[i]["label"])
    chosen = sorted(rng.sample(wrong, min(5, len(wrong))) + rng.sample(right, min(5, len(right))))
    out += ["## 5. Ten baseline predictions next to gold", "",
            f"Five drawn from the wrong predictions and five from the right ones (seed {SEED}). "
            "The dataset has no gold evidence, so only the model's evidence is shown.", "",
            "| id | langs | gold | predicted | evidence kept | model's raw answer |", "|---|---|---|---|---|---|"]
    for i in chosen:
        g, p, raw = gold[i], preds[i], raws[i]
        kept = "yes" if p.get("evidence") else "no" + (f" ({raw.get('parse_reason')})" if raw.get("parse_reason") else "")
        answer = (raw.get("answer") or raw.get("error") or "").replace("|", "\\|").replace("\n", " ")
        mark = "" if p.get("label") == g["label"] else " **wrong**"
        out.append(f"| {i} | {g['claim_language']}->{g['reference_language']} | {g['label']} {g['label_name']} | "
                   f"{NAMES[p.get('label')]}{mark} | {kept} | {answer[:400]} |")
    out += ["", "Claims of these ten cases:", ""]
    out += [f"- **{i}**: {inputs[i]['claim']['text']}" for i in chosen]
    out += [""]

    (DOCS / "baseline_review.md").write_text("\n".join(out), encoding="utf-8")
    print("Wrote docs/baseline_review.md")


if __name__ == "__main__":
    main()
