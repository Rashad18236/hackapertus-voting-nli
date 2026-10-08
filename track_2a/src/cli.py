"""Read requests from a JSONL file and write one response per request.

Usage (the official entrypoint contract):

    python -m src.cli --input /data/cases.jsonl --output /output/predictions.jsonl

Each request has exactly one of `booklet` (task A) or `reference` (task B).
Task B: one model call with the reference passage, label only.
Task A: one model call with the booklet text, the vote name and the claim; the
answer names up to five pages, whose text becomes the evidence. --context-a
chooses what booklet text the model sees (CONTEXTS_A): the whole booklet
("fulldoc", the default and reference baseline) or only the passages most
similar to the claim ("embed-e5-small", see src/context.py).
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

from src import context, env, llm, nli, parse

FALLBACK_LABEL = 1  # neutral; used whenever we cannot produce a real answer
MAX_TOKENS_A = 64  # answer budget for task A ({"pages": [...], "label": n})
JSON_MODE_A = False  # ask the endpoint for a JSON object in task A (response_format)

# Task A context variants: name -> prompt version. Every variant's name appears in
# the raw answers, so each run in docs/results.md says which one it used.
CONTEXTS_A = {
    "fulldoc": "A-v3-fulldoc",          # whole booklet, page by page
    "embed-e5-small": "A-v3-excerpts",  # top context.TOP_K chunks by multilingual-e5-small similarity
}
DEFAULT_CONTEXT_A = "fulldoc"  # the measured baseline; switch only after a variant beats it on dev

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


def predict_a(case, data_dir, start, raw, max_tokens_a=MAX_TOKENS_A, json_mode_a=JSON_MODE_A,
              context_a=DEFAULT_CONTEXT_A):
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

    prompt_version = CONTEXTS_A[context_a]
    raw["context_a"], raw["prompt_version"] = context_a, prompt_version
    if context_a == "fulldoc":
        booklet_text = parse.booklet_prompt_text(pages)
    else:
        try:
            chunks = context.select_chunks(pages, claim_text)
        except Exception as e:  # e.g. model files missing; must not stop the run
            raw["error"] = f"context selection failed ({type(e).__name__}: {e})"
            return response(case_id, FALLBACK_LABEL, start=start), "context selection failed"
        raw["context_pages"] = [n for n, _ in chunks]
        booklet_text = context.excerpts_prompt_text(chunks)
    try:
        result = llm.chat(nli.build_messages_a(booklet_text, vote, claim_text, prompt_version), max_tokens=max_tokens_a,
                          json_mode=json_mode_a)
    except llm.LLMError as e:
        raw["error"] = str(e)
        return response(case_id, FALLBACK_LABEL, start=start), "model call failed"

    raw["answer"], raw["attempts"], raw["output_tokens"] = result.text, result.attempts, result.output_tokens
    label, page_numbers, reason = nli.parse_label_and_pages(result.text)
    if label is None:
        raw["parse_reason"] = reason
        return response(case_id, FALLBACK_LABEL, result.input_tokens, result.output_tokens, start), "unparseable answer"
    evidence = parse.evidence_items(pages, page_numbers) if label in (0, 2) else []
    status = "ok" if label == 1 or evidence else "no valid pages for label 0/2"
    return response(case_id, label, result.input_tokens, result.output_tokens, start, evidence), status


def predict(case, prompt_b=nli.DEFAULT_PROMPT_B, data_dir=".", max_tokens_a=MAX_TOKENS_A, json_mode_a=JSON_MODE_A,
            context_a=DEFAULT_CONTEXT_A):
    """Return (response, status, raw). status is 'ok' or a failure kind; raw keeps details for analysis."""
    start = time.perf_counter()  # timed around the whole case, not only the model call
    case_id = case["id"]
    task = task_of(case)
    raw = {"id": case_id, "task": task}

    if task is None:
        return response(case_id, FALLBACK_LABEL, start=start), "invalid request (needs exactly one of booklet/reference)", raw
    if task == "A":
        resp, status = predict_a(case, data_dir, start, raw, max_tokens_a, json_mode_a, context_a)
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
    parser.add_argument("--max-tokens-a", type=int, default=MAX_TOKENS_A,
                        help="development only: answer token budget for task A")
    parser.add_argument("--json-mode-a", action="store_true", default=JSON_MODE_A,
                        help="development only: request a JSON object (response_format) for task A")
    parser.add_argument("--context-a", default=DEFAULT_CONTEXT_A, choices=sorted(CONTEXTS_A),
                        help="task A context: whole booklet or embedding-selected excerpts")
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
            resp, status, raw = predict(case, args.prompt_b, args.input.resolve().parent, args.max_tokens_a,
                                          args.json_mode_a, args.context_a)
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
