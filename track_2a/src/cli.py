"""Read beginner cases from a JSONL file and write predictions as JSONL.

Usage: python -m src.cli [INPUT] [OUTPUT]
"""

import argparse
import json
import logging
import time
from pathlib import Path

from src import llm, nli

DEFAULT_INPUT = "data/sample_beginner.jsonl"
DEFAULT_OUTPUT = "output/predictions.jsonl"


def read_cases(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_predictions(path, predictions):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for p in predictions:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")


def predict(case):
    # Timed around the whole case, not only the model call.
    start = time.perf_counter()
    reference = case["reference"]["text"]
    result = llm.chat(nli.build_messages(reference, case["claim"]["text"]))
    label_name = nli.parse_label(result.text)
    evidence = []
    if label_name != "neutral":
        quote = nli.parse_evidence(result.text, reference)
        if quote:
            evidence.append({"text": quote})
    return {
        "id": case["id"],
        "label": nli.LABELS[label_name],
        "label_name": label_name,
        "evidence": evidence,
        "metrics": {
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "inference_time_ms": round((time.perf_counter() - start) * 1000),
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", default=DEFAULT_INPUT)
    parser.add_argument("output", nargs="?", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    cases = read_cases(args.input)
    predictions = []
    for case in cases:
        p = predict(case)
        logging.info("%s -> %s (%d input tokens)", p["id"], p["label_name"], p["metrics"]["input_tokens"])
        predictions.append(p)
    write_predictions(args.output, predictions)
    logging.info("Wrote %d predictions to %s", len(predictions), args.output)


if __name__ == "__main__":
    main()
