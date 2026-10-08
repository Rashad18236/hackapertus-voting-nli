"""Read requests from a JSONL file and write one response per request.

Usage (the official entrypoint contract):

    python -m src.cli --input /data/cases.jsonl --output /output/predictions.jsonl

Each request has exactly one of `booklet` (task A) or `reference` (task B).
Task B: one model call with the reference passage, label only.
Task A: one model call with booklet text (the whole booklet, the vote's
section, or the passages most similar to the claim; see src/context.py), the
vote name and the claim; the answer names up to five pages, whose text becomes
the evidence.
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
from dataclasses import dataclass
from pathlib import Path

from src import context, env, evidence, llm, nli, parse

FALLBACK_LABEL = 1  # neutral; used whenever we cannot produce a real answer


@dataclass
class Settings:
    """Pipeline settings. The defaults are what judges get; flags exist for experiments."""
    prompt_b: str = nli.DEFAULT_PROMPT_B
    max_tokens_a: int = 128     # answer budget for task A ({"pages": [...], "label": n})
    json_mode_a: bool = False   # response_format json_object for task A (tried in session 2, not kept)
    schema_a: bool = True       # response_format json_schema for task A: forces {"pages", "label"} (session 3, E1)
    context_a: str = "embed-e5-small"  # which booklet text task A sends: see context.MODES (session 4: won E3,
                                       # 0.721 vs vote-section 0.561, and held in E4 against vote-section-embed-e5-small-k12)
    evidence_a: str = "cited"   # task A evidence items: see evidence.MODES (session 4)


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


def predict_a(case, data_dir, start, raw, settings):
    """Task A: booklet pages (all, or the selected context) in one call. Returns (response, status)."""
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

    prompt_version = context.prompt_version(settings.context_a)  # each variant names its prompt
    raw["prompt_version"], raw["context"] = prompt_version, settings.context_a
    try:
        cross_language = case["claim"].get("language") != case["booklet"].get("language")
        booklet_text, shown = context.select(pages, vote, claim_text, settings.context_a, cross_language)
    except Exception as e:  # e.g. embedding model files missing; must not stop the run
        raw["error"] = f"context selection failed ({type(e).__name__}: {e})"
        return response(case_id, FALLBACK_LABEL, start=start), "context selection failed"
    raw["pages_sent"], raw["pages_total"], raw["context_pages"] = len(shown), len(pages), sorted(shown)
    try:
        result = llm.chat(nli.build_messages_a(booklet_text, vote, claim_text, prompt_version),
                          max_tokens=settings.max_tokens_a, json_mode=settings.json_mode_a,
                          json_schema=nli.ANSWER_SCHEMA_A if settings.schema_a else None)
    except llm.LLMError as e:
        raw["error"] = str(e)
        return response(case_id, FALLBACK_LABEL, start=start), "model call failed"

    raw["answer"], raw["attempts"], raw["output_tokens"] = result.text, result.attempts, result.output_tokens
    label, page_numbers, reason = nli.parse_label_and_pages(result.text)
    if label is None:
        raw["parse_reason"] = reason
        return response(case_id, FALLBACK_LABEL, result.input_tokens, result.output_tokens, start), "unparseable answer"
    # Evidence comes from the pages that were sent; a page number outside them is ignored.
    cited = parse.evidence_items(shown, page_numbers) if label in (0, 2) else []
    status = "ok" if label == 1 or cited else "no valid pages for label 0/2"
    items = evidence.items(settings.evidence_a, cited, shown, claim_text) if label in (0, 2) else []
    return response(case_id, label, result.input_tokens, result.output_tokens, start, items), status


def predict(case, data_dir=".", settings=None):
    """Return (response, status, raw). status is 'ok' or a failure kind; raw keeps details for analysis."""
    settings = settings or Settings()
    start = time.perf_counter()  # timed around the whole case, not only the model call
    case_id = case["id"]
    task = task_of(case)
    raw = {"id": case_id, "task": task}

    if task is None:
        return response(case_id, FALLBACK_LABEL, start=start), "invalid request (needs exactly one of booklet/reference)", raw
    if task == "A":
        resp, status = predict_a(case, data_dir, start, raw, settings)
        return resp, status, raw

    try:
        reference_text = case["reference"]["text"]
        claim_text = case["claim"]["text"]
    except (KeyError, TypeError):
        return response(case_id, FALLBACK_LABEL, start=start), "invalid request (missing reference.text or claim.text)", raw

    raw["prompt_version"] = settings.prompt_b
    try:
        result = llm.chat(nli.build_messages_b(reference_text, claim_text, settings.prompt_b), max_tokens=32)
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
    defaults = Settings()
    parser.add_argument("--prompt-b", default=defaults.prompt_b, choices=sorted(nli.PROMPTS_B),
                        help="development only: task B prompt version")
    parser.add_argument("--max-tokens-a", type=int, default=defaults.max_tokens_a,
                        help="development only: answer token budget for task A")
    parser.add_argument("--json-mode-a", action="store_true", default=defaults.json_mode_a,
                        help="development only: request a JSON object (response_format) for task A")
    parser.add_argument("--schema-a", action="store_true", default=defaults.schema_a,
                        help="development only: force the task A answer schema (response_format json_schema)")
    parser.add_argument("--context-a", default=defaults.context_a, choices=context.MODES,
                        help="development only: which booklet text task A sends")
    parser.add_argument("--evidence-a", default=defaults.evidence_a, choices=evidence.MODES,
                        help="development only: which task A evidence items to return")
    args = parser.parse_args()
    settings = Settings(prompt_b=args.prompt_b, max_tokens_a=args.max_tokens_a, json_mode_a=args.json_mode_a,
                        schema_a=args.schema_a, context_a=args.context_a,
                        evidence_a=args.evidence_a)
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
            resp, status, raw = predict(case, args.input.resolve().parent, settings)
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
