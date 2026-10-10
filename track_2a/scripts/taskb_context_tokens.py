"""Offline input tokens per task B case for each task B context (session 9, phase C). No model calls.

Run from track_2a/:

    EMBED_MODEL_DIR=models/multilingual-e5-small python3 scripts/taskb_context_tokens.py \\
        --tokenizer <folder with the Apertus tokenizer.json> --cases output/devB/cases.jsonl --out <file.json>

For every case, the request that src/cli.py would send with --context-b full, cut and para is built (the
same functions, so B-cut runs the local e5 model) and its two messages are counted with the Apertus v1
tokenizer, plus the 19 tokens the endpoint's chat template adds (docs/taskb_confirmation.md). The real
counts come from the endpoint (usage.prompt_tokens) in the interleaved run; this is the estimate before it.
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import cli, nli, taskb_context  # noqa: E402

TEMPLATE_TOKENS = 19


def messages_for(case, mode, settings):
    reference, claim = case["reference"]["text"], case["claim"]["text"]
    if mode == "para":
        return nli.build_messages_a_paragraphs(taskb_context.PART_LINE, taskb_context.para_texts(reference, claim),
                                               case.get("vote", ""), claim)
    text = taskb_context.cut_text(reference, claim) if mode == "cut" else reference
    return nli.build_messages_b(text, claim, settings.prompt_b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokenizer", required=True)
    ap.add_argument("--cases", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(str(Path(args.tokenizer) / "tokenizer.json"))
    settings = cli.Settings()
    cases = [json.loads(line) for line in Path(args.cases).read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = []
    for case in cases:
        row = {"id": case["id"], "chars": len(case["reference"]["text"]),
               "long": taskb_context.is_long(case["reference"]["text"])}
        for mode in taskb_context.MODES:
            msgs = messages_for(case, mode, settings)
            row[mode] = TEMPLATE_TOKENS + sum(len(tok.encode(m["content"], add_special_tokens=False).ids) for m in msgs)
        rows.append(row)
    summary = {"cases": len(rows), "long_cases": sum(r["long"] for r in rows), "template_tokens": TEMPLATE_TOKENS}
    for subset, chosen in (("all", rows), ("long", [r for r in rows if r["long"]]),
                           ("short", [r for r in rows if not r["long"]])):
        if not chosen:
            continue
        summary[subset] = {mode: round(statistics.mean(r[mode] for r in chosen), 1) for mode in taskb_context.MODES}
        full = summary[subset]["full"]
        summary[subset]["saving_vs_full"] = {mode: round(1 - summary[subset][mode] / full, 4)
                                             for mode in ("cut", "para")}
    Path(args.out).write_text(json.dumps({"summary": summary, "cases": rows}, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
