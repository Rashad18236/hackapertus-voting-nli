"""Break task B's input tokens into their parts (task B confirmation stage).

Run from track_2a/:

    python3 scripts/taskb_tokens.py --tokenizer <folder with Apertus tokenizer.json> \\
        --run docs/runs/<task B run> [--measure-endpoint] --out <folder>

For each case of the run, the request that src/cli.py sends for task B
(nli.build_messages_b with the run's prompt version) is split into:

  (a) fixed instructions: the system prompt, plus the fixed labels of the user
      message ("REFERENCE TEXT:", "CLAIM:" and the line breaks around them);
  (b) examples in the prompt (none in v3-topic-first);
  (c) the passage (the reference text);
  (d) the claim, plus the vote name if the prompt sends it (task B does not);
  (e) what the endpoint adds on its own (the chat template: role markers,
      start and end tokens, any default text).

(a) to (d) are counted locally with the Apertus tokenizer given by --tokenizer
(the endpoint's own tokenizer is not public: Apertus v1.5 is gated, so the
ungated Apertus v1 tokenizer is used and the gap is measured). (e) is measured
on the endpoint with --measure-endpoint, which sends tiny requests through
src/llm.py (max_tokens 1) and reads usage.prompt_tokens:
  - one user message of one word;
  - one system message and one user message of one word each (the shape of
    a task B request).
(e) = prompt_tokens minus the locally counted tokens of the words.

The run's recorded input_tokens (usage.prompt_tokens of each case) is the
true count; the script reports how far a+b+c+d+e is from it. It also reports
the passage length in characters and tokens, and the mean output tokens.
Writes summary.json and per_case.jsonl.
"""

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import env, llm, nli  # noqa: E402


def load(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def p95(values):
    ordered = sorted(values)
    return ordered[math.ceil(0.95 * len(ordered)) - 1]


def stats(values):
    return {"mean": round(statistics.mean(values), 1), "p95": p95(values), "min": min(values),
            "median": statistics.median(values), "max": max(values)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tokenizer", type=Path, required=True, help="folder with tokenizer.json")
    ap.add_argument("--run", type=Path, required=True, help="a task B run folder (predictions.jsonl, raw_answers.jsonl)")
    ap.add_argument("--cases", type=Path, default=ROOT / "output" / "devB" / "cases.jsonl")
    ap.add_argument("--measure-endpoint", action="store_true", help="send the tiny requests that measure (e)")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(str(args.tokenizer / "tokenizer.json"))
    count = lambda text: len(tok.encode(text, add_special_tokens=False).ids)  # noqa: E731

    cases = {c["id"]: c for c in load(args.cases)}
    preds = {p["id"]: p for p in load(args.run / "predictions.jsonl")}
    raws = {r["id"]: r for r in load(args.run / "raw_answers.jsonl")}

    overhead = {}
    if args.measure_endpoint:
        env.load_env_file()
        one = llm.chat([{"role": "user", "content": "Hello"}], max_tokens=1)
        two = llm.chat([{"role": "system", "content": "Hello"}, {"role": "user", "content": "Hello"}], max_tokens=1)
        overhead = {"one_user_message_prompt_tokens": one.input_tokens,
                    "one_user_message_overhead": one.input_tokens - count("Hello"),
                    "system_and_user_prompt_tokens": two.input_tokens,
                    "system_and_user_overhead": two.input_tokens - 2 * count("Hello")}
    e = overhead.get("system_and_user_overhead")

    rows = []
    for case_id, case in cases.items():
        pred, raw = preds.get(case_id), raws.get(case_id, {})
        if pred is None or raw.get("error"):
            continue  # a failed call has no usage to compare with
        version = raw.get("prompt_version", nli.DEFAULT_PROMPT_B)
        system, user = (m["content"] for m in nli.build_messages_b(case["reference"]["text"], case["claim"]["text"],
                                                                   version))
        passage, claim = case["reference"]["text"], case["claim"]["text"]
        labels = user.replace(passage, "", 1).replace(claim, "", 1)  # "REFERENCE TEXT:\n" + "\n\nCLAIM:\n"
        assert labels == "REFERENCE TEXT:\n\n\nCLAIM:\n", labels
        row = {"id": case_id, "a_system": count(system), "a_labels": count("REFERENCE TEXT:\n") + count("\n\nCLAIM:\n"),
               "b_examples": 0, "c_passage": count(passage), "d_claim_and_vote": count(claim),
               "passage_chars": len(passage), "true_prompt_tokens": pred["metrics"]["input_tokens"],
               "output_tokens": pred["metrics"]["output_tokens"], "user_message_whole": count(user)}
        row["a_fixed"] = row["a_system"] + row["a_labels"]
        if e is not None:
            row["e_endpoint"] = e
            row["our_count"] = row["a_fixed"] + row["b_examples"] + row["c_passage"] + row["d_claim_and_vote"] + e
            row["our_minus_true"] = row["our_count"] - row["true_prompt_tokens"]
        rows.append(row)

    summary = {
        "run": str(args.run), "cases_with_usage": len(rows), "tokenizer": str(args.tokenizer),
        "prompt_version": raws[rows[0]["id"]].get("prompt_version") if rows else None,
        "a_fixed_instructions": stats([r["a_fixed"] for r in rows]),
        "a_of_which_system_prompt": stats([r["a_system"] for r in rows]),
        "a_of_which_user_labels": stats([r["a_labels"] for r in rows]),
        "b_examples": stats([r["b_examples"] for r in rows]),
        "c_passage": stats([r["c_passage"] for r in rows]),
        "d_claim_and_vote": stats([r["d_claim_and_vote"] for r in rows]),
        "e_endpoint": overhead,
        "true_prompt_tokens": stats([r["true_prompt_tokens"] for r in rows]),
        "passage_chars": stats([r["passage_chars"] for r in rows]),
        "output_tokens": stats([r["output_tokens"] for r in rows]),
    }
    if e is not None:
        diffs = [r["our_minus_true"] for r in rows]
        summary["our_count"] = stats([r["our_count"] for r in rows])
        summary["our_minus_true"] = {"mean": round(statistics.mean(diffs), 2),
                                     "mean_absolute": round(statistics.mean(abs(d) for d in diffs), 2),
                                     "mean_relative_percent": round(100 * statistics.mean(
                                         r["our_minus_true"] / r["true_prompt_tokens"] for r in rows), 2),
                                     "min": min(diffs), "max": max(diffs),
                                     "exact": sum(1 for d in diffs if d == 0)}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    (args.out / "per_case.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
