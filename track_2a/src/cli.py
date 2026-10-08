"""Read requests from a JSONL file and write one response per request.

Usage (the official entrypoint contract):

    python -m src.cli --input /data/cases.jsonl --output /output/predictions.jsonl

Each request has exactly one of `booklet` (task A) or `reference` (task B).
Task B: one model call with the reference passage, label only.
Task A: one model call with the whole booklet (page by page), the vote name and
the claim; the answer names up to five pages, whose text becomes the evidence.
Booklet paths are relative to the input file's folder (/data in the container).

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

from src import env, llm, nli, parse

FALLBACK_LABEL = 1  # neutral; used whenever we cannot produce a real answer

log = logging.getLogger("cli")


def response(case_id, label, input_tokens=0, output_tokens=0, start=None, evidence=None):
    """A response in the official format. Task B evidence is always empty (not scored)."""
    elapsed = round((time.perf_counter() - start) * 1000) if start is not None else 0
    return {
        "id": case_id,
        "label": label,
        "label_name": nli.LABEL_NAMES[label],
        "evidence": evidence or [],
        "metrics": {"input_tokens": input_tokens, "output_tokens": output_tokens, "inference_time_ms": elapsed},
    }


def task_of(case):
    """'A', 'B', or None if the request does not have exactly one source."""
    has_booklet, has_reference = "booklet" in case, "reference" in case
    if has_booklet == has_reference:
        return None
    return "A" if has_booklet else "B"


def predict_a(case, data_dir, start, raw):
    """Task A: whole booklet in one call. Returns (response, status)."""
    case_id = case["id"]
    try:
        pdf_path = Path(data_dir) / case["booklet"]["path"]
        vote, claim_text = case["vote"], case["claim"]["text"]
    except (KeyError, TypeError):
        return response(case_id, FALLBACK_LABEL, start=start), "invalid request (missing booklet.path, vote or claim.text)"
    if not pdf_path.is_file():
        return response(case_id, FALLBACK_LABEL, start=start), "booklet not found"
    try:
        pages = parse.load_pages(pdf_path)
    except Exception as e:  # a broken PDF must not stop the run
        raw["error"] = f"PDF parsing failed ({type(e).__name__})"
        return response(case_id, FALLBACK_LABEL, start=start), "booklet could not be parsed"

    raw["prompt_version"] = nli.PROMPT_VERSION_A
    try:
        result = llm.chat(nli.build_messages_a(parse.booklet_prompt_text(pages), vote, claim_text), max_tokens=64)
    except llm.LLMError as e:
        raw["error"] = str(e)
        return response(case_id, FALLBACK_LABEL, start=start), "model call failed"

    raw["answer"], raw["attempts"] = result.text, result.attempts
    label, page_numbers, reason = nli.parse_label_and_pages(result.text)
    if label is None:
        raw["parse_reason"] = reason
        return response(case_id, FALLBACK_LABEL, result.input_tokens, result.output_tokens, start), "unparseable answer"
    evidence = parse.evidence_items(pages, page_numbers) if label in (0, 2) else []
    status = "ok" if label == 1 or evidence else "no valid pages for label 0/2"
    return response(case_id, label, result.input_tokens, result.output_tokens, start, evidence), status


def predict(case, prompt_b=nli.DEFAULT_PROMPT_B, data_dir="."):
    """Return (response, status, raw). status is 'ok' or a failure kind; raw keeps details for analysis."""
    start = time.perf_counter()  # timed around the whole case, not only the model call
    case_id = case["id"]
    task = task_of(case)
    raw = {"id": case_id, "task": task}

    if task is None:
        return response(case_id, FALLBACK_LABEL, start=start), "invalid request (needs exactly one of booklet/reference)", raw
    if task == "A":
        resp, status = predict_a(case, data_dir, start, raw)
        return resp, status, raw

    try:
        reference_text = case["reference"]["text"]
        claim_text = case["claim"]["text"]
    except (KeyError, TypeError):
        return response(case_id, FALLBACK_LABEL, start=start), "invalid request (missing reference.text or claim.text)", raw

    raw["prompt_version"] = prompt_b
    try:
        result = llm.chat(nli.build_messages_b(reference_text, claim_text, prompt_b), max_tokens=32)
    except llm.LLMError as e:
        raw["error"] = str(e)
        return response(case_id, FALLBACK_LABEL, start=start), "model call failed", raw

    raw["answer"], raw["attempts"] = result.text, result.attempts
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
    parser.add_argument("--prompt-b", default=nli.DEFAULT_PROMPT_B, choices=sorted(nli.PROMPTS_B),
                        help="development only: task B prompt version")
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        parser.error("Input and output must be different files.")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s", stream=sys.stderr)
    logging.getLogger("pypdf").setLevel(logging.ERROR)  # font warnings are noise here

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
            resp, status, raw = predict(case, args.prompt_b, args.input.resolve().parent)
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
