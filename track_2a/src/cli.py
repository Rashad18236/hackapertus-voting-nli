"""Read requests from a JSONL file and write one response per request.

Usage (the official entrypoint contract):

    python -m src.cli --input /data/cases.jsonl --output /output/predictions.jsonl

Each request has exactly one of `booklet` (task A) or `reference` (task B).
Task B: one model call with the reference passage, label only.
Task A: one model call with booklet text (the whole booklet, the vote's
section, or the passages most similar to the claim; see src/context.py), the
vote name and the claim; the answer names up to five pages, whose text becomes
the evidence. A routing variant ("section-route") instead sends one part of the
vote as numbered paragraphs; the answer names up to three paragraphs, whose
verbatim text becomes the evidence.
Booklet paths are relative to the input file's folder (/data in the container).

No case is ever dropped. If a request is malformed, the model call fails or
the answer cannot be parsed, we still write a valid response with the
fallback label (1, neutral) and count the failure. A summary of all failures
goes to stderr at the end. Exit code is 0 whenever the input could be read.

Input and output (session 8):
- The input is read as bytes and decoded line by line, so one byte that is not
  UTF-8 spoils only its own line (it becomes U+FFFD; the line is answered if it
  is still readable JSON with an id). A UTF-8 byte order mark at the start is
  ignored. Lines end at \\n, \\r\\n or \\r.
- An id that appears on several lines is answered once, from its first line;
  later lines with that id are logged and skipped (the scorer counts an id with
  two responses as invalid).
- Each response is written to the output file and flushed as soon as it is
  ready (the raw answers with --raw likewise), so a run that is stopped (time
  limit, out of memory) keeps every finished case as a complete line. A blank
  input gives an empty output file.
"""

import argparse
import codecs
import contextlib
import json
import logging
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from src import context, env, evidence, llm, nli, parse, taskb_context

FALLBACK_LABEL = 1  # neutral; used whenever we cannot produce a real answer


@dataclass
class Settings:
    """Pipeline settings. The defaults are what judges get; flags exist for experiments."""
    prompt_b: str = nli.DEFAULT_PROMPT_B
    schema_b: bool = False      # response_format json_schema for task B: forces {"label": 0|1|2} (task B cheap fixes)
    max_tokens_b: int = 32      # answer budget for task B
    max_tokens_a: int = 128     # answer budget for task A ({"pages": [...], "label": n})
    json_mode_a: bool = False   # response_format json_object for task A (tried in session 2, not kept)
    schema_a: bool = True       # response_format json_schema for task A: forces {"pages", "label"} (session 3, E1)
    context_a: str = "section-route"  # which booklet text task A sends: see context.MODES (session 7: won the
                                      # paired runs on dev, 0.953 vs embed-e5-small 0.834, and on val, 0.956 vs 0.865;
                                      # cases it cannot route run as embed-e5-small)
    context_b: str = "cut"       # task B context: full, cut (B-cut) or para (B-para); see taskb_context. Session 9,
                                 # phase C: B-cut kept Macro-F1 (dev 0.967 vs 0.967, val 0.961 vs 0.957) with 37-38 %
                                 # fewer input tokens; references of at most 8,000 characters are sent unchanged
    evidence_halves_a: bool = True   # section-route evidence: add halves of cited paragraphs up to 5 items (session 9, A2:
                                     # dev evidence 0.9055 -> 0.9254, val 0.9461 -> 0.9559, labels and requests unchanged)
    evidence_a: str = "cited-pieces"  # task A evidence items: see evidence.MODES (session 6: E4's answers re-scored,
                                      # 0.542 vs 0.373 for whole cited pages, labels unchanged)
    label_rule_a: bool = True    # L1 (session 9, phase D): the routed prompt plus one sentence on contradictions
                                 # (A-v4-section-route-L1); passed its rule: dev 0.980 vs 0.966, val 0.961 vs 0.950,
                                 # neutral recall 1.000 on both. --no-label-rule-a sends A-v4-section-route
    section_top_k_a: int = 0     # E1 (session 9, information only): if > 0, a routed case keeps only its k paragraphs
                                 # most similar to the claim (e5), in their order; 0 keeps section-route as it is
    second_look_a: bool = False  # L2 (session 9, phase D): a second call after a neutral answer, see second_look()
    second_look_threshold: float = 0.845  # L2 only: the claim's highest e5 similarity to a sent paragraph must reach
                                          # this (phase B, B6: on E5's 110 neutral answers it flags 10 of the 11 wrong
                                          # ones and 11 of the 99 right ones; the best difference of the two shares)


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


def note_call(raw, call):
    """Record a model call's requests (1 plus retries), HTTP 429 answers and endpoint identity (src/llm.py) in raw.
    call is an llm.LLMResult or an llm.LLMError; both carry these three fields."""
    raw["attempts"], raw["http_429"], raw["endpoint"] = call.attempts, call.http_429, call.endpoint
    if getattr(call, "fallbacks", None):
        raw["llm_fallbacks"] = call.fallbacks  # session 9: response_format dropped or model name replaced


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

    raw["context"] = settings.context_a
    # Routing variants (section-route): parse the booklet, route the claim, build the paragraph prompt.
    # Any error in these steps makes the case run as the variant's fallback, exactly like "no route";
    # it never costs the case its model call.
    routed = messages = None
    try:
        routed = context.route(pages, vote, claim_text, settings.context_a)
        if routed is not None and settings.section_top_k_a > 0:  # E1: cut to the k most similar paragraphs
            part, paragraphs = routed
            routed = part, context.VARIANTS[settings.context_a].most_similar(paragraphs, claim_text,
                                                                             settings.section_top_k_a)
        if routed is not None:
            messages = paragraph_messages(routed, vote, claim_text, settings)
    except Exception as e:
        routed = None
        raw["route_error"] = f"{type(e).__name__}: {e}"
        log.warning("%s: routing failed (%s); running as %s", case_id, raw["route_error"],
                    context.fallback(settings.context_a))
    if routed is not None:
        return predict_a_paragraphs(case_id, routed, messages, start, raw, settings, len(pages), vote, claim_text)
    try:
        cross_language = case["claim"].get("language") != case["booklet"].get("language")
        mode = context.fallback(settings.context_a)
        booklet_text, shown = context.select(pages, vote, claim_text, mode, cross_language)
    except Exception as e:  # e.g. embedding model files missing; must not stop the run
        raw["error"] = f"context selection failed ({type(e).__name__}: {e})"
        return response(case_id, FALLBACK_LABEL, start=start), "context selection failed"
    if mode != settings.context_a:
        raw["fallback"] = mode  # the variant could not route this case
    prompt_version = context.prompt_version(mode)  # each variant names its prompt
    raw["prompt_version"] = prompt_version
    raw["pages_sent"], raw["pages_total"], raw["context_pages"] = len(shown), len(pages), sorted(shown)
    try:
        result = llm.chat(nli.build_messages_a(booklet_text, vote, claim_text, prompt_version),
                          max_tokens=settings.max_tokens_a, json_mode=settings.json_mode_a,
                          json_schema=nli.ANSWER_SCHEMA_A if settings.schema_a else None)
    except llm.LLMError as e:
        raw["error"] = str(e)
        note_call(raw, e)
        return response(case_id, FALLBACK_LABEL, start=start), "model call failed"

    note_call(raw, result)
    raw["answer"], raw["output_tokens"] = result.text, result.output_tokens
    label, page_numbers, reason = nli.parse_label_and_pages(result.text)
    if label is None:
        raw["parse_reason"] = reason
        return response(case_id, FALLBACK_LABEL, result.input_tokens, result.output_tokens, start), "unparseable answer"
    # Evidence comes from the pages that were sent; a page number outside them is ignored.
    cited = parse.evidence_items(shown, page_numbers) if label in (0, 2) else []
    status = "ok" if label == 1 or cited else "no valid pages for label 0/2"
    items = evidence.items(settings.evidence_a, cited, shown, claim_text, page_numbers) if label in (0, 2) else []
    return response(case_id, label, result.input_tokens, result.output_tokens, start, items), status


def paragraph_messages(routed, vote, claim_text, settings):
    """The prompt for a routed case: the PART line, the numbered paragraphs as shown, VOTE and CLAIM."""
    variant = context.VARIANTS[settings.context_a]
    part, paragraphs = routed
    return nli.build_messages_a_paragraphs(variant.PART_LINES[part], [variant.display(t) for _, t in paragraphs],
                                           vote, claim_text, paragraph_prompt_version(settings))


def paragraph_prompt_version(settings):
    version = context.VARIANTS[settings.context_a].PROMPT_VERSION
    return version + "-L1" if settings.label_rule_a else version


def predict_a_paragraphs(case_id, routed, messages, start, raw, settings, pages_total, vote="", claim_text=""):
    """Task A for a routed case: one part of the vote as numbered paragraphs; the answer cites paragraphs,
    whose verbatim text and page become the evidence. Returns (response, status)."""
    variant = context.VARIANTS[settings.context_a]
    part, paragraphs = routed
    raw["prompt_version"], raw["route"] = paragraph_prompt_version(settings), part
    raw["paragraphs_sent"] = [[page, len(text)] for page, text in paragraphs]
    raw["pages_total"], raw["context_pages"] = pages_total, sorted({page for page, _ in paragraphs})
    try:
        result = llm.chat(messages, max_tokens=settings.max_tokens_a,
                          json_schema=nli.ANSWER_SCHEMA_A_PARAGRAPHS if settings.schema_a else None)
    except llm.LLMError as e:
        raw["error"] = str(e)
        note_call(raw, e)
        return response(case_id, FALLBACK_LABEL, start=start), "model call failed"

    note_call(raw, result)
    raw["answer"], raw["output_tokens"] = result.text, result.output_tokens
    label, numbers, reason = nli.parse_label_and_pages(result.text, key="paragraphs")
    if label is None:
        raw["parse_reason"] = reason
        return response(case_id, FALLBACK_LABEL, result.input_tokens, result.output_tokens, start), "unparseable answer"
    input_tokens, output_tokens = result.input_tokens, result.output_tokens
    if label == 1 and settings.second_look_a:
        second = second_look(routed, vote, claim_text, raw, settings)
        if second is not None:
            result2, label2, numbers2, shown2 = second
            input_tokens, output_tokens = input_tokens + result2.input_tokens, output_tokens + result2.output_tokens
            if label2 in (0, 2):  # only an entailment or contradiction replaces the first neutral answer
                label, numbers, paragraphs = label2, numbers2, shown2
    items = variant.evidence_items(paragraphs, numbers, halves=settings.evidence_halves_a) if label in (0, 2) else []
    status = "ok" if label == 1 or items else "no valid paragraphs for label 0/2"
    return response(case_id, label, input_tokens, output_tokens, start, items), status


def second_look(routed, vote, claim_text, raw, settings):
    """L2 (session 9, phase D; off by default): after a neutral answer on a routed case, if the claim's highest e5
    similarity to a sent paragraph reaches settings.second_look_threshold, ask once more with the three most
    similar paragraphs (in their order) and prompt A-v4-second-look, which asks for 0, then 2, then 1.

    Returns (result, label, paragraph numbers, the three paragraphs) of the second call, or None when there is no
    second call or it fails or cannot be read (the first answer stays). Recorded in raw["second_look"]."""
    variant = context.VARIANTS[settings.context_a]
    part, paragraphs = routed
    try:
        scores = variant.similarities(paragraphs, claim_text)
    except Exception as e:  # e.g. no e5 files: the first answer stays
        raw["second_look"] = {"error": f"{type(e).__name__}: {e}"}
        return None
    best = float(max(scores))
    raw["second_look"] = {"similarity": round(best, 4), "asked": best >= settings.second_look_threshold}
    if best < settings.second_look_threshold:
        return None
    top = sorted(sorted(range(len(paragraphs)), key=lambda i: -scores[i])[:3])
    shown = [paragraphs[i] for i in top]
    messages = nli.build_messages_a_paragraphs(variant.PART_LINES[part], [variant.display(t) for _, t in shown],
                                               vote, claim_text, "A-v4-second-look")
    try:
        result = llm.chat(messages, max_tokens=settings.max_tokens_a,
                          json_schema=nli.ANSWER_SCHEMA_A_PARAGRAPHS if settings.schema_a else None)
    except llm.LLMError as e:
        raw["second_look"].update(error=str(e), attempts=e.attempts)
        return None
    label, numbers, reason = nli.parse_label_and_pages(result.text, key="paragraphs")
    raw["second_look"].update(answer=result.text, input_tokens=result.input_tokens,
                              output_tokens=result.output_tokens, attempts=result.attempts,
                              endpoint=result.endpoint, paragraphs=[[p, len(t)] for p, t in shown])
    if label is None:
        raw["second_look"]["parse_reason"] = reason
        return result, None, [], shown
    return result, label, numbers, shown


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
    messages, max_tokens, schema = None, settings.max_tokens_b, nli.ANSWER_SCHEMA_B if settings.schema_b else None
    if settings.context_b != "full":  # session 9, phase C: cut or numbered long passages (off by default)
        raw["context_b"] = settings.context_b
        try:
            if settings.context_b == "para":
                texts = taskb_context.para_texts(reference_text, claim_text)
                raw["prompt_version"], raw["paragraphs_sent"] = "A-v4-section-route", len(texts)
                messages = nli.build_messages_a_paragraphs(taskb_context.PART_LINE, texts, case.get("vote", ""),
                                                           claim_text)
                max_tokens, schema = settings.max_tokens_a, nli.ANSWER_SCHEMA_A_PARAGRAPHS
            else:
                text = taskb_context.cut_text(reference_text, claim_text)
                raw["chars_sent"] = len(text)
                messages = nli.build_messages_b(text, claim_text, settings.prompt_b)
        except Exception as e:  # e.g. no e5 files: the whole reference, as by default
            raw["context_b_error"] = f"{type(e).__name__}: {e}"
            messages, max_tokens = None, settings.max_tokens_b
            schema = nli.ANSWER_SCHEMA_B if settings.schema_b else None
            raw["prompt_version"] = settings.prompt_b
    try:
        result = llm.chat(messages or nli.build_messages_b(reference_text, claim_text, settings.prompt_b),
                          max_tokens=max_tokens, json_schema=schema)
    except llm.LLMError as e:
        raw["error"] = str(e)
        note_call(raw, e)
        return response(case_id, FALLBACK_LABEL, start=start), "model call failed", raw

    note_call(raw, result)
    raw["answer"] = result.text
    label, reason = nli.parse_label(result.text)
    status = "ok"
    if label is None:
        raw["parse_reason"] = reason
        label, status = FALLBACK_LABEL, "unparseable answer"
    return response(case_id, label, result.input_tokens, result.output_tokens, start), status, raw


def read_lines(path):
    """The input file's lines as text: read as bytes, a UTF-8 byte order mark at the start dropped, split at
    \\n, \\r\\n or \\r, and each line decoded on its own with errors="replace"."""
    data = Path(path).read_bytes()
    if data.startswith(codecs.BOM_UTF8):
        data = data[len(codecs.BOM_UTF8):]
    return [line.decode("utf-8", errors="replace") for line in data.splitlines()]


def write_line(f, obj):
    """Write one JSON line to a file opened in binary mode and flush it, so it reaches the file at once."""
    f.write((json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8"))
    f.flush()


def main():
    parser = argparse.ArgumentParser(description="Swiss voting booklet NLI: one response per request.")
    parser.add_argument("--input", type=Path, required=True, help="JSONL file with one request per line")
    parser.add_argument("--output", type=Path, required=True, help="JSONL file for the responses")
    parser.add_argument("--raw", type=Path, help="development only: also write raw model answers here")
    defaults = Settings()
    parser.add_argument("--prompt-b", default=defaults.prompt_b, choices=sorted(nli.PROMPTS_B),
                        help="development only: task B prompt version")
    parser.add_argument("--schema-b", action="store_true", default=defaults.schema_b,
                        help="development only: force the task B answer schema (response_format json_schema)")
    parser.add_argument("--max-tokens-b", type=int, default=defaults.max_tokens_b,
                        help="development only: answer token budget for task B")
    parser.add_argument("--max-tokens-a", type=int, default=defaults.max_tokens_a,
                        help="development only: answer token budget for task A")
    parser.add_argument("--json-mode-a", action="store_true", default=defaults.json_mode_a,
                        help="development only: request a JSON object (response_format) for task A")
    parser.add_argument("--schema-a", action="store_true", default=defaults.schema_a,
                        help="development only: force the task A answer schema (response_format json_schema)")
    parser.add_argument("--context-a", default=defaults.context_a, choices=context.MODES,
                        help="development only: which booklet text task A sends")
    parser.add_argument("--context-b", default=defaults.context_b, choices=taskb_context.MODES,
                        help="development only: task B context (session 9, phase C)")
    parser.add_argument("--evidence-halves-a", action=argparse.BooleanOptionalAction, default=defaults.evidence_halves_a,
                        help="development only: section-route evidence adds halves of cited paragraphs (session 9, A2)")
    parser.add_argument("--label-rule-a", action=argparse.BooleanOptionalAction, default=defaults.label_rule_a,
                        help="development only: L1, the routed prompt plus a sentence on contradictions (session 9, D)")
    parser.add_argument("--section-top-k-a", type=int, default=defaults.section_top_k_a,
                        help="development only: E1, keep the k paragraphs most similar to the claim (0: all)")
    parser.add_argument("--second-look-a", action=argparse.BooleanOptionalAction, default=defaults.second_look_a,
                        help="development only: L2, a second call after a neutral answer (session 9, D)")
    parser.add_argument("--second-look-threshold", type=float, default=defaults.second_look_threshold,
                        help="development only: L2's similarity threshold")
    parser.add_argument("--evidence-a", default=defaults.evidence_a, choices=evidence.MODES,
                        help="development only: which task A evidence items to return")
    args = parser.parse_args()
    settings = Settings(prompt_b=args.prompt_b, schema_b=args.schema_b, max_tokens_b=args.max_tokens_b,
                        max_tokens_a=args.max_tokens_a, json_mode_a=args.json_mode_a,
                        schema_a=args.schema_a, context_a=args.context_a,
                        evidence_a=args.evidence_a, evidence_halves_a=args.evidence_halves_a,
                        context_b=args.context_b, label_rule_a=args.label_rule_a, second_look_a=args.second_look_a,
                        second_look_threshold=args.second_look_threshold, section_top_k_a=args.section_top_k_a)
    if args.input.resolve() == args.output.resolve():
        parser.error("Input and output must be different files.")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s", stream=sys.stderr)
    logging.getLogger("pypdf").setLevel(logging.ERROR)  # font warnings are noise here

    env.load_env_file()
    lines = read_lines(args.input)
    failures = Counter()
    routing_failed = 0  # cases whose routing raised and that ran as the fallback variant (answered normally)
    answered = set()  # ids already answered (as JSON text, so any id value can be compared)
    written = 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.raw:
        args.raw.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("wb") as out, (args.raw.open("wb") if args.raw else contextlib.nullcontext()) as raw_out:
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
            key = json.dumps(case_id, sort_keys=True)
            if key in answered:
                failures["duplicate id (answered once, from its first line)"] += 1
                log.warning("line %d: id %s was already answered; skipped", number, key)
                continue
            answered.add(key)
            try:
                resp, status, raw = predict(case, args.input.resolve().parent, settings)
            except Exception as e:  # never let one case stop the run
                resp, status, raw = response(case_id, FALLBACK_LABEL), f"unexpected error ({type(e).__name__})", {"id": case_id}
            if status != "ok":
                failures[status] += 1
            routing_failed += "route_error" in raw
            log.info("[%d/%d] %s -> %s%s", number, len(lines), case_id, resp["label_name"],
                     "" if status == "ok" else f" (fallback: {status})")
            write_line(out, resp)
            if raw_out is not None:
                write_line(raw_out, raw)
            written += 1

    log.info("Wrote %d responses to %s", written, args.output)
    if routing_failed:
        log.warning("Routing failed and the case ran as the fallback variant: %d", routing_failed)
    if failures:
        log.warning("Fallback or skipped cases: %s", ", ".join(f"{k}: {v}" for k, v in failures.most_common()))
    else:
        log.info("No failures.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
