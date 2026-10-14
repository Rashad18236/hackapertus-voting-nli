"""Session 13, step 4: where the final run's errors come from (routing or reading), and what kind of reading error
Apertus says each one is. OFFLINE analysis only: never part of the pipeline; one Apertus call per error with --label.

Run from track_2a/ (EMBED_MODEL_DIR set as for the CLI):

    python3 scripts/error_types.py --task A --run docs/runs/<final>/task-A --cases data/val/cases.jsonl \\
        --expected data/val/expected-labels.jsonl --data-dir output/data_dev --out FILE.json [--label]

Every case whose label differs from the gold label is an error. Task A: the case is prepared again exactly as the
CLI prepares it (src/cli.py prepare, no model call); a gold entailment or contradiction whose gold passage is not
in the text Apertus read (rapidfuzz partial ratio >= 90 after the starter's normalisation, as the evidence rule) is a
routing error, every other error a reading error (a gold neutral has no passage to find). A case that cannot be
prepared without a model call (the fallback's translation) is judged on the pages it was sent. Task B has no
routing: every error is a reading error, judged on the reference as sent (selector T).

With --label, Apertus names the main kind of each reading error (prompt ERR-type-v1, json_schema, temperature 0,
through src/llm.py like every call): the claim, the text as sent, the label given and the gold label. The counts
are reported; the answers never feed back into the pipeline.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from rapidfuzz import fuzz  # noqa: E402

import evidence_loss as el  # noqa: E402
from src import cli, context, env, llm, nli, parse, taskb_context  # noqa: E402

TYPES = ["number_or_date", "actor", "direction_or_negation", "scope", "paraphrase", "other_ballot_or_topic", "other"]
PROMPT = """You help analyse the mistakes of a fact checker. It compared a CLAIM with a REFERENCE TEXT from an official Swiss federal voting booklet and gave a label: 0 (entailment: the text supports the claim), 1 (neutral: the text does not settle the claim) or 2 (contradiction: the text states something that cannot be true together with the claim). The given label is wrong; the correct label is stated. The text and the claim may be in different languages.

Name the main reason for the mistake, as one of:
"number_or_date": claim and text differ in a number, share, amount or date, or agree on one that was misread;
"actor": they differ in who does, decides, pays or says something;
"direction_or_negation": they differ in direction (more or less, for or against, accepted or rejected), or one negates the other;
"scope": the claim is broader or narrower than the text (a condition, an exception, a part instead of the whole);
"paraphrase": the text says what the claim says, in other words;
"other_ballot_or_topic": the text is about another ballot or another subject than the claim;
"other": none of these.

Answer with one JSON object and nothing else:
{"type": "number_or_date"}"""
SCHEMA = {"type": "object", "properties": {"type": {"type": "string", "enum": TYPES}}, "required": ["type"],
          "additionalProperties": False}


def load(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def sent_text_a(case, data_dir, raw):
    """(how the case was prepared, the text Apertus read)."""
    prepared = cli.prepare(case, data_dir, cli.Settings())
    if prepared.kind == "A-paragraphs" and prepared.routed is not None:
        if [[p, len(t)] for p, t in prepared.routed[1]] == raw.get("paragraphs_sent"):
            return f"route:{prepared.routed[0]}", "\n".join(f"[{i}] {t}" for i, (_, t) in
                                                            enumerate(prepared.routed[1], start=1))
    pages = parse.load_pages(Path(data_dir) / case["booklet"]["path"])
    shown = raw.get("context_pages") or []
    return "fallback (pages sent)", "\n\n".join(pages.get(p, "") for p in shown)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--task", choices=["A", "B"], required=True)
    parser.add_argument("--run", required=True)
    parser.add_argument("--cases", required=True)
    parser.add_argument("--expected", required=True)
    parser.add_argument("--data-dir", default="output/data_dev")
    parser.add_argument("--label", action="store_true", help="ask Apertus for each reading error's kind")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    if args.label:
        env.load_env_file(ROOT / ".env")
    cases = {c["id"]: c for c in load(args.cases)}
    gold = {g["id"]: g for g in load(args.expected)}
    preds = {p["id"]: p for p in load(Path(args.run) / "predictions.jsonl")}
    raws = {r["id"]: r for r in load(Path(args.run) / "raw_answers.jsonl")}
    rows = []
    for cid, pred in preds.items():
        g = gold[cid]["label"]
        if pred["label"] == g:
            continue
        case = cases[cid]
        if args.task == "A":
            how, text = sent_text_a(case, args.data_dir, raws.get(cid, {}))
        else:
            reference, claim = case["reference"]["text"], case["claim"]["text"]
            how, text = "reference as sent", taskb_context.cut_text(reference, claim, "cut4-t", cli.same_language_b(case))
        kind = "reading"
        if args.task == "A" and g in (0, 2):
            found = fuzz.partial_ratio(el.norm(gold[cid]["reference"]), el.norm(text), score_cutoff=el.MIN_RATIO)
            kind = "reading" if found >= el.MIN_RATIO else "routing"
        row = {"id": cid, "gold": g, "given": pred["label"], "error": kind, "prepared": how,
               "same_language": case["claim"].get("language") == (case.get("booklet") or case.get("reference"))["language"]}
        if args.label and kind == "reading":
            messages = [{"role": "system", "content": PROMPT},
                        {"role": "user", "content": f"REFERENCE TEXT:\n{text}\n\nCLAIM:\n{case['claim']['text']}\n\n"
                                                    f"GIVEN LABEL: {pred['label']}\nCORRECT LABEL: {g}"}]
            try:
                result = llm.chat(messages, max_tokens=32, json_schema=SCHEMA)
                label, _ = nli.parse_word(result.text, "type", {t: t for t in TYPES})
                row.update(type=label, input_tokens=result.input_tokens, output_tokens=result.output_tokens)
            except llm.LLMError as e:
                row.update(type=None, error_call=str(e))
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    summary = {"errors": len(rows), "by_error": dict(Counter(r["error"] for r in rows)),
               "by_gold_given": dict(Counter(f"{r['gold']}->{r['given']}" for r in rows))}
    if args.label:
        summary["reading_types"] = dict(Counter(r.get("type") for r in rows if r["error"] == "reading"))
        summary["calls"] = sum(1 for r in rows if "input_tokens" in r)
    Path(args.out).write_text(json.dumps({"task": args.task, "run": args.run, "prompt": "ERR-type-v1",
                                          "summary": summary, "rows": rows}, indent=1, ensure_ascii=False) + "\n",
                              encoding="utf-8")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
