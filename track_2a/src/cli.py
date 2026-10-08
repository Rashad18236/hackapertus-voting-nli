"""Read requests from a JSONL file and write one response per request.

Usage (the official entrypoint contract):

    python -m src.cli --input /data/cases.jsonl --output /output/predictions.jsonl

Each request has exactly one of `booklet` (task A) or `reference` (task B).
Task B: one model call with the reference passage, label only.
Task A: PLACEHOLDER, not implemented yet; always answers neutral, no model call.

No case is ever dropped. If a request is malformed, the model call fails or
the answer cannot be parsed, we still write a valid response with the
fallback label (1, neutral) and count the failure. A summary of all failures
goes to stderr at the end. Exit code is 0 whenever the input could be read.
"""

import argparse
import json
import logging
import sys
import time
from collections import Counter
from pathlib import Path

from src import env, llm, nli

FALLBACK_LABEL = 1  # neutral; used whenever we cannot produce a real answer
TASK_A_PLACEHOLDER = True  # task A is not implemented yet

log = logging.getLogger("cli")


def response(case_id, label, input_tokens=0, output_tokens=0, start=None):
    """A response in the official format. Evidence is empty for now (task B evidence is not scored)."""
    elapsed = round((time.perf_counter() - start) * 1000) if start is not None else 0
    return {
        "id": case_id,
        "label": label,
        "label_name": nli.LABEL_NAMES[label],
        "evidence": [],
        "metrics": {"input_tokens": input_tokens, "output_tokens": output_tokens, "inference_time_ms": elapsed},
    }


def task_of(case):
    """'A', 'B', or None if the request does not have exactly one source."""
    has_booklet, has_reference = "booklet" in case, "reference" in case
    if has_booklet == has_reference:
        return None
    return "A" if has_booklet else "B"


def predict(case):
    """Return (response, status, raw). status is 'ok' or a failure kind; raw keeps details for analysis."""
    start = time.perf_counter()  # timed around the whole case, not only the model call
    case_id = case["id"]
    task = task_of(case)
    raw = {"id": case_id, "task": task}

    if task is None:
        return response(case_id, FALLBACK_LABEL, start=start), "invalid request (needs exactly one of booklet/reference)", raw
    if task == "A":
        # PLACEHOLDER: task A (booklet PDF) is not implemented yet. No model call, fixed label.
        return response(case_id, FALLBACK_LABEL, start=start), "task A placeholder", raw

    try:
        reference_text = case["reference"]["text"]
        claim_text = case["claim"]["text"]
    except (KeyError, TypeError):
        return response(case_id, FALLBACK_LABEL, start=start), "invalid request (missing reference.text or claim.text)", raw

    raw["prompt_version"] = nli.PROMPT_VERSION_B
    try:
        result = llm.chat(nli.build_messages_b(reference_text, claim_text), max_tokens=32)
    except llm.LLMError as e:
        raw["error"] = str(e)
        return response(case_id, FALLBACK_LABEL, start=start), "model call failed", raw

    raw["answer"] = result.text
    label, reason = nli.parse_label(result.text)
    status = "ok"
    if label is None:
        raw["parse_reason"] = reason
        label, status = FALLBACK_LABEL, "unparseable answer"
    return response(case_id, label, result.input_tokens, result.output_tokens, start), status, raw


def main():
    parser = argparse.ArgumentParser(description="Swiss voting booklet NLI: one response per request.")
    parser.add_argument("--input", type=Path, required=True, help="JSONL file with one request per line")
    parser.add_argument("--output", type=Path, required=True, help="JSONL file for the responses")
    parser.add_argument("--raw", type=Path, help="development only: also write raw model answers here")
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        parser.error("Input and output must be different files.")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s", stream=sys.stderr)

    env.load_env_file()
    lines = args.input.read_text(encoding="utf-8").splitlines()
    failures = Counter()
    responses, raws = [], []
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            case = json.loads(line)
            case_id = case["id"]
        except (json.JSONDecodeError, KeyError, TypeError):
            # Without an id there is nothing we can answer; count it so it is visible.
            failures["unreadable line or missing id (no response possible)"] += 1
            log.error("line %d: unreadable JSON or missing id; skipped", number)
            continue
        try:
            resp, status, raw = predict(case)
        except Exception as e:  # never let one case stop the run
            resp, status, raw = response(case_id, FALLBACK_LABEL), f"unexpected error ({type(e).__name__})", {"id": case_id}
        if status != "ok":
            failures[status] += 1
        log.info("[%d/%d] %s -> %s%s", number, len(lines), case_id, resp["label_name"],
                 "" if status == "ok" else f" (fallback: {status})")
        responses.append(resp)
        raws.append(raw)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        for resp in responses:
            f.write(json.dumps(resp, ensure_ascii=False) + "\n")
    if args.raw:
        args.raw.parent.mkdir(parents=True, exist_ok=True)
        with args.raw.open("w", encoding="utf-8") as f:
            for raw in raws:
                f.write(json.dumps(raw, ensure_ascii=False) + "\n")

    log.info("Wrote %d responses to %s", len(responses), args.output)
    if failures:
        log.warning("Fallback or skipped cases: %s", ", ".join(f"{k}: {v}" for k, v in failures.most_common()))
    else:
        log.info("No failures.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
