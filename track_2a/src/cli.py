"""Read beginner cases from a JSONL file and write predictions as JSONL.

Usage: python -m src.cli [INPUT] [OUTPUT] [--raw RAW_ANSWERS.jsonl]

One model call per case. If a call fails or the answer cannot be parsed, the
case gets label null and a flag, and the run continues with the next case.
"""

import argparse
import json
import logging
import time
from pathlib import Path

from src import env, llm, nli

DEFAULT_INPUT = "data/sample_beginner.jsonl"
DEFAULT_OUTPUT = "output/predictions.jsonl"


def read_cases(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def predict(case):
    """Return (prediction, raw_record). raw_record keeps the model's answer for error analysis."""
    # Timed around the whole case, not only the model call.
    start = time.perf_counter()
    reference = case["reference"]["text"]
    prediction = {"id": case["id"]}
    raw = {"id": case["id"], "prompt_version": nli.PROMPT_VERSION}
    try:
        result = llm.chat(nli.build_messages(reference, case["claim"]["text"]), max_tokens=400)
    except llm.LLMError as e:
        prediction.update({"label": None, "label_name": None, "evidence": [], "error": str(e)})
        prediction["metrics"] = {"input_tokens": 0, "output_tokens": 0,
                                 "inference_time_ms": round((time.perf_counter() - start) * 1000)}
        raw.update({"answer": None, "error": str(e)})
        return prediction, raw

    parsed = nli.parse_answer(result.text, reference)
    label = parsed["label"]
    prediction.update({
        "label": label,
        "label_name": nli.LABEL_NAMES.get(label),
        "evidence": [{"text": parsed["evidence"]}] if parsed["evidence"] else [],
    })
    if parsed["parse_failure"]:
        prediction["parse_failure"] = True
    prediction["metrics"] = {
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "inference_time_ms": round((time.perf_counter() - start) * 1000),
    }
    raw.update({"answer": result.text, "parse_reason": parsed["reason"]})
    return prediction, raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", default=DEFAULT_INPUT)
    parser.add_argument("output", nargs="?", default=DEFAULT_OUTPUT)
    parser.add_argument("--raw", help="also write the raw model answers to this JSONL file")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    env.load_env_file()
    cases = read_cases(args.input)
    predictions, raws = [], []
    for i, case in enumerate(cases, start=1):
        p, raw = predict(case)
        status = p.get("error") and "CALL FAILED" or ("PARSE FAILURE" if p.get("parse_failure") else p["label_name"])
        logging.info("[%d/%d] %s -> %s (%d input tokens)", i, len(cases), p["id"], status,
                     p["metrics"]["input_tokens"])
        predictions.append(p)
        raws.append(raw)
    write_jsonl(args.output, predictions)
    if args.raw:
        write_jsonl(args.raw, raws)
    failures = sum(1 for p in predictions if p["label"] is None)
    logging.info("Wrote %d predictions to %s (%d without a label)", len(predictions), args.output, failures)


if __name__ == "__main__":
    main()
