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
import dataclasses
import functools
import json
import logging
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from src import context, env, evidence, llm, nli, parse, pipeline, rankers, taskb_context

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
    context_b: str = "cut4-t"    # task B context (session 11, step 6, adopted: TASK B RULE): full, cut, para, cut4, cut4-q/t/l/h; session 9,
                                 # phase C: B-cut kept Macro-F1 (dev 0.967 vs 0.967, val 0.961 vs 0.957) with 37-38 %
                                 # fewer input tokens. Session 10, step 2: back to the whole reference. B-cut embeds the
                                 # paragraphs of every long reference (about 225 s of local work on 300 dev cases); with
                                 # a fast model it cannot hide behind the requests (0.47 s local time per case at 0.3 s
                                 # per request, against 0.009 s without it). REF SCORE S_B, mean over 1.0 and 0.3 s per
                                 # request: dev 0.827 (full) vs 0.821 (cut), val 0.821 vs 0.817
    evidence_halves_a: bool = True   # section-route evidence: add halves of cited paragraphs up to 5 items (session 9, A2:
                                     # dev evidence 0.9055 -> 0.9254, val 0.9461 -> 0.9559, labels and requests unchanged)
    evidence_a: str = "cited-pieces"  # task A evidence items: see evidence.MODES (session 6: E4's answers re-scored,
                                      # 0.542 vs 0.373 for whole cited pages, labels unchanged)
    label_rule_a: bool = True    # L1 (session 9, phase D): the routed prompt plus one sentence on contradictions
                                 # (A-v4-section-route-L1); passed its rule: dev 0.980 vs 0.966, val 0.961 vs 0.950,
                                 # neutral recall 1.000 on both. --no-label-rule-a sends A-v4-section-route
    section_top_k_a: int = 0     # E1 (session 9, information only): if > 0, a routed case keeps only its k paragraphs
                                 # most similar to the claim (e5), in their order; 0 keeps section-route as it is
    coupled_schema_a: bool = False  # CS (session 10, step 6): routed answers with the coupled schema (neutral cites nothing,
                                    # entailment and contradiction cite 1 to 3 paragraphs); needs anyOf at the endpoint
    second_look_cited_a: bool = False  # SL (session 10, step 6): a neutral answer that cites paragraphs gets one more call
                                       # with only those paragraphs; an entailment or contradiction there replaces it
    short_prompt_a: bool = False  # P-short (session 10, step 5): routed cases get A-v5-short, the same rules in at most
                                  # 200 fixed tokens (L1's sentence included)
    second_look_a: bool = False  # L2 (session 9, phase D): a second call after a neutral answer, see second_look()
    ap_part_a: str = "after-rules"  # session 11, step 3 (adopted, HYBRID RULE): Apertus names the claim's part: "after-rules" (only when the
                                 # rules find none; its "none" goes on to the fallback) or "all" (for every claim)
    ap_structure_a: str = "off"  # session 11, step 3 (off): Apertus reads the contents pages (one call per booklet):
                                 # "after-parser" (only when the parser gives no valid part for the vote) or "all";
                                 # its entries are used only where they pass the parser's heading checks
    fallback_a: str = "embed"    # session 11, step 2: what a case that section-route cannot route gets: "embed"
                                 # (embed-e5-small, as before), or the levels "vw" (vote-wide), "bw" (booklet-wide),
                                 # "vw+bw"; a level that does not apply leaves the case to embed-e5-small
    ranker: str = "e5"           # session 12, step 1: which local ranker keeps a long part's, the fallback's and (cut4-r) a
                                 # long task B reference's most similar pieces: see src/rankers.py ("e5" is today's code)
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


@dataclass
class Prepared:
    """A case made ready for its model call by prepare(); complete() makes the call and builds the response.

    Session 10: the organisers count local time (container time without a model request in flight), so the
    local work of a case (reading and parsing the booklet, routing, embedding, building the messages) is done
    in prepare(), which src/pipeline.py runs in a background thread while another case's request is in flight.

    kind: "done" (no model call: the response is already known, e.g. a missing booklet), "B" (task B),
    "A-pages" (task A with page context) or "A-paragraphs" (task A, a routed case). seconds: the time spent
    preparing, counted in the case's inference_time_ms."""
    case_id: object
    raw: dict
    kind: str = "done"
    done: tuple = None           # kind "done": (response, status)
    messages: list = None        # the request's messages
    chat_args: dict = field(default_factory=dict)  # llm.chat's other arguments: max_tokens, json_schema, json_mode
    vote: str = ""
    claim_text: str = ""
    shown: dict = None           # A-pages: {page: text} of the pages sent
    routed: tuple = None         # A-paragraphs: (part, [(page, verbatim text)]) as sent
    seconds: float = 0.0
    ask: tuple = None            # A-ask-part (session 11): (language, {part: routed}, fallback Prepared)


def finished(case_id, raw, resp, status):
    return Prepared(case_id, raw, done=(resp, status))


def prepare_a(case, data_dir, start, raw, settings):
    """Task A up to the model call: booklet pages, then the routed part (section-route) or the selected
    context, and the messages."""
    case_id = case["id"]
    try:
        pdf_path = Path(data_dir) / case["booklet"]["path"]
        vote, claim_text = case["vote"], case["claim"]["text"]
    except (KeyError, TypeError):
        return finished(case_id, raw, response(case_id, FALLBACK_LABEL, start=start),
                        "invalid request (missing booklet.path, vote or claim.text)")
    if not pdf_path.is_file():
        return finished(case_id, raw, response(case_id, FALLBACK_LABEL, start=start), "booklet not found")
    try:
        pages = parse.load_pages(pdf_path)
    except Exception as e:  # a broken PDF must not stop the run
        raw["error"] = f"PDF parsing failed ({type(e).__name__})"
        return finished(case_id, raw, response(case_id, FALLBACK_LABEL, start=start), "booklet could not be parsed")

    raw["context"] = settings.context_a
    # Routing variants (section-route): parse the booklet, route the claim, build the paragraph prompt.
    # Any error in these steps makes the case run as the variant's fallback, exactly like "no route";
    # it never costs the case its model call.
    routed = messages = None
    found = None
    try:
        if ap_in_prepare(settings):  # session 11, step 3 (off by default): Apertus in the parsing roles
            routed, found = ap_route(pages, vote, claim_text, case["booklet"].get("language"), raw, settings)
        else:
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
        part, paragraphs = routed
        raw["prompt_version"], raw["route"] = paragraph_prompt_version(settings), part
        raw["paragraphs_sent"] = [[page, len(text)] for page, text in paragraphs]
        raw["pages_total"], raw["context_pages"] = len(pages), sorted({page for page, _ in paragraphs})
        return Prepared(case_id, raw, kind="A-paragraphs", messages=messages, vote=vote, claim_text=claim_text,
                        routed=routed, chat_args={"max_tokens": settings.max_tokens_a,
                                                  "json_schema": paragraph_schema(settings)})
    if ask_part_after_rules(settings) and "route_error" not in raw:
        candidates = part_candidates(pages, vote, claim_text, raw, settings)
        if candidates:
            fallback_raw = {}
            fallback = fallback_prepared(case, pages, vote, claim_text, start, fallback_raw, settings, found)
            return Prepared(case_id, raw, kind="A-ask-part", vote=vote, claim_text=claim_text,
                            ask=(case["booklet"].get("language") or "", candidates, fallback))
    return fallback_prepared(case, pages, vote, claim_text, start, raw, settings, found)


def fallback_prepared(case, pages, vote, claim_text, start, raw, settings, found=None):
    """A case section-route could not route: a fallback level if one is set (step 2, off), else the variant's
    fallback (embed-e5-small)."""
    case_id = case["id"]
    if settings.fallback_a == "bm25-ap" and settings.context_a == "section-route":
        prepared = bm25_fallback(case, pages, vote, claim_text, raw, settings)
        if prepared is not None:
            return prepared
    wide = wide_fallback(pages, vote, claim_text, raw, settings, found if ap_in_prepare(settings) else None)
    if wide is not None:
        return wide_prepared(case_id, raw, wide, pages, vote, claim_text, settings)
    try:
        cross_language = case["claim"].get("language") != case["booklet"].get("language")
        mode = context.fallback(settings.context_a)
        booklet_text, shown = context.select(pages, vote, claim_text, mode, cross_language)
    except Exception as e:  # e.g. embedding model files missing; must not stop the run
        raw["error"] = f"context selection failed ({type(e).__name__}: {e})"
        return finished(case_id, raw, response(case_id, FALLBACK_LABEL, start=start), "context selection failed")
    if mode != settings.context_a:
        raw["fallback"] = mode  # the variant could not route this case
    prompt_version = context.prompt_version(mode)  # each variant names its prompt
    raw["prompt_version"] = prompt_version
    raw["pages_sent"], raw["pages_total"], raw["context_pages"] = len(shown), len(pages), sorted(shown)
    return Prepared(case_id, raw, kind="A-pages", vote=vote, claim_text=claim_text, shown=shown,
                    messages=nli.build_messages_a(booklet_text, vote, claim_text, prompt_version),
                    chat_args={"max_tokens": settings.max_tokens_a, "json_mode": settings.json_mode_a,
                               "json_schema": nli.ANSWER_SCHEMA_A if settings.schema_a else None})


def bm25_fallback(case, pages, vote, claim_text, raw, settings):
    """Session 12, step 5 (off by default; --fallback-a bm25-ap): a case section-route cannot route gets the 8 chunks
    of the booklet (embed-e5-small's chunks and prompt) with the best BM25 score (Kaan's bm25, src/contexts/bm25.py)
    for the claim. When the claim is in another language than the booklet, Apertus first translates it into the
    booklet's language (one call in complete_a_translate, its tokens in the case's metrics); BM25 then ranks with the
    translation, and the reading call gets the claim as it is. None (embed-e5-small as before) if the booklet has no
    text."""
    from src.contexts import embed_e5_small
    chunks = embed_e5_small.chunk_pages(pages)
    if not chunks:
        return None
    raw["fallback"], raw["prompt_version"], raw["pages_total"] = "bm25-ap", embed_e5_small.PROMPT_VERSION, len(pages)
    page_texts = {n: pages[n] for n in sorted({n for n, _ in chunks})}
    p = Prepared(case["id"], raw, kind="A-translate", vote=vote, claim_text=claim_text,
                 ask=(case["booklet"].get("language") or "", chunks, page_texts),
                 chat_args={"max_tokens": settings.max_tokens_a, "json_mode": settings.json_mode_a,
                            "json_schema": nli.ANSWER_SCHEMA_A if settings.schema_a else None})
    if case["claim"].get("language") == case["booklet"].get("language"):
        return bm25_pages(p, claim_text)  # one language: no translation needed
    return p


def bm25_pages(p, search_text):
    """The A-pages request of a bm25-ap fallback: the 8 chunks with the best BM25 score for search_text."""
    from src.contexts import embed_e5_small
    _, chunks, page_texts = p.ask
    keep = rankers.best("BM25", [t for _, t in chunks], search_text, embed_e5_small.TOP_K)
    chosen = [chunks[i] for i in keep]
    shown = {n: page_texts[n] for n, _ in chosen}
    p.raw["pages_sent"], p.raw["context_pages"] = len(shown), sorted(shown)
    return Prepared(p.case_id, p.raw, kind="A-pages", vote=p.vote, claim_text=p.claim_text, shown=shown,
                    messages=nli.build_messages_a(embed_e5_small.excerpts_prompt_text(chosen), p.vote, p.claim_text,
                                                  embed_e5_small.PROMPT_VERSION),
                    chat_args=p.chat_args)


def complete_a_translate(p, start, settings):
    """Session 12, step 5: Apertus translates the claim into the booklet's language; BM25 chooses the chunks with it."""
    from src import ap_parse
    translated, call = ap_parse.translate(p.claim_text, p.ask[0])
    tokens = p.raw.setdefault("ap_tokens", [0, 0])
    tokens[0] += call.get("input_tokens", 0)
    tokens[1] += call.get("output_tokens", 0)
    p.raw.setdefault("ap_calls", []).append(call)
    return complete_a_pages(bm25_pages(p, translated or p.claim_text), start, settings)


FALLBACK_LEVELS = ("embed", "vw", "bw", "vw+bw", "bm25-ap")
AP_PART_MODES = ("off", "after-rules", "all")
AP_STRUCTURE_MODES = ("off", "after-parser", "all")


def ap_on(settings):
    return settings.ap_part_a != "off" or settings.ap_structure_a != "off"


def ap_in_prepare(settings):
    """Apertus called while a case is prepared (ap_route; the sequential path): AP-structure, or AP-part for every
    claim. AP-part after the rules alone is asked when the case is completed (ask_part_after_rules)."""
    return settings.ap_structure_a != "off" or settings.ap_part_a == "all"


def ask_part_after_rules(settings):
    """Session 11, step 3: AP-part after the rules, without AP-structure. The worker process prepares, for a claim
    whose opening the rules do not know, every valid part of its vote and the usual fallback; the main process then
    asks Apertus which part the opening names (one request, src/ap_parse.claim) and sends that part's request."""
    return (settings.ap_part_a == "after-rules" and settings.ap_structure_a == "off"
            and settings.context_a == "section-route")


def part_candidates(pages, vote, claim_text, raw, settings):
    """{part: routed} for every part of the case's vote that passed the parser's checks, when the rules name no
    part and the vote is found; {} otherwise (then nothing is asked). An error leaves the case to the fallback."""
    from src import ap_parse, claim_router
    try:
        if claim_router.route(claim_text) is not None:
            return {}
        variant = context.VARIANTS["section-route"]
        found = variant.find(variant.parsed_booklet(pages), vote)
        if found is None:
            return {}
        candidates = {}
        for part in ap_parse.PARTS:
            if part in found.valid:
                routed = variant.route_part(pages, found, part, claim_text)
                if routed is not None:
                    candidates[part] = routed
        return candidates
    except Exception as e:
        raw["ask_part_error"] = f"{type(e).__name__}: {e}"
        log.warning("%s: preparing the parts failed (%s); running the fallback", raw.get("id"), raw["ask_part_error"])
        return {}


def complete_a_ask_part(p, start, settings):
    """A case whose opening the rules do not know: Apertus names the part (one call, its tokens count in the
    case's metrics); the case is then completed as routed to that part, or as its fallback when Apertus names no
    part or one the parser did not validate (or the call fails)."""
    from src import ap_parse
    language, candidates, fallback = p.ask
    part, statement, call = ap_parse.claim(p.claim_text, language)
    tokens = p.raw.setdefault("ap_tokens", [0, 0])
    tokens[0] += call.get("input_tokens", 0)
    tokens[1] += call.get("output_tokens", 0)
    p.raw.setdefault("ap_calls", []).append(call)
    p.raw["ap_part"] = {"rules": None, "apertus": part, "statement": statement}
    if part in candidates:
        routed = candidates[part]
        _, paragraphs = routed
        p.raw["prompt_version"], p.raw["route"] = paragraph_prompt_version(settings), part
        p.raw["paragraphs_sent"] = [[page, len(text)] for page, text in paragraphs]
        p.raw["context_pages"] = sorted({page for page, _ in paragraphs})
        q = Prepared(p.case_id, p.raw, kind="A-paragraphs", vote=p.vote, claim_text=p.claim_text, routed=routed,
                     messages=paragraph_messages(routed, p.vote, p.claim_text, settings),
                     chat_args={"max_tokens": settings.max_tokens_a, "json_schema": paragraph_schema(settings)})
    else:
        p.raw.update(fallback.raw)
        q = Prepared(**{**fallback.__dict__, "raw": p.raw})
    if q.kind == "done":
        return q.done
    return COMPLETE[q.kind](q, start, settings)


def ap_route(pages, vote, claim_text, language, raw, settings):
    """Session 11, step 3 (off by default): section-route with Apertus in a parsing role. Returns (routed or None,
    ("found", the vote or None)); the second item tells wide_fallback which vote AP-structure found.

    Part: the rules (claim_router); AP-part "after-rules" asks Apertus only when they find none, "all" always.
    Vote: the Python parser; AP-structure "after-parser" asks Apertus's contents reading only when the parser gives
    no valid part for the vote, "all" always (then the Python parser is not used for the case). Apertus's entries
    pass the parser's own heading checks before any part is used. Every call's tokens go into raw["ap_tokens"], which
    complete() adds to the case's metrics; calls are listed in raw["ap_calls"].
    """
    from src import ap_parse, claim_router

    variant = context.VARIANTS["section-route"]
    calls = raw.setdefault("ap_calls", [])
    tokens = raw.setdefault("ap_tokens", [0, 0])

    def spend(call):
        tokens[0] += call.get("input_tokens", 0)
        tokens[1] += call.get("output_tokens", 0)
        calls.append({k: v for k, v in call.items() if k != "endpoint"} | {"endpoint": call.get("endpoint")})

    part = claim_router.route(claim_text)
    if settings.ap_part_a == "all" or (settings.ap_part_a == "after-rules" and part is None):
        ap_part, statement, call = ap_parse.claim(claim_text, language or "")
        spend(call)
        raw["ap_part"] = {"rules": part, "apertus": ap_part, "statement": statement}
        part = ap_part
    found = None if settings.ap_structure_a == "all" else variant.find(variant.parsed_booklet(pages), vote)
    use_ap = settings.ap_structure_a == "all" or (
        settings.ap_structure_a == "after-parser" and (found is None or part is None or part not in found.valid))
    if use_ap:
        entries, call = ap_parse.structure(pages)
        if call["first"]:
            spend(call)
        ap_booklet = ap_parse.booklet_from_entries(pages, entries)
        ap_found = variant.find(ap_booklet, vote) if ap_booklet is not None else None
        raw["ap_structure"] = {"entries": len(entries or []), "vote_found": ap_found is not None,
                               "valid": sorted(ap_found.valid) if ap_found is not None else []}
        if settings.ap_structure_a == "all" or (ap_found is not None and (found is None or part in ap_found.valid)):
            found = ap_found
    routed = variant.route_part(pages, found, part, claim_text) if part is not None else None
    return routed, ("found", found)


def wide_fallback(pages, vote, claim_text, raw, settings, ap_found=None):
    """Session 11, step 2 (off by default): the vote-wide or booklet-wide paragraphs for a case section-route could not
    route, or None (then the case runs as embed-e5-small, as before). An error here also leaves it to embed-e5-small.
    ap_found: with AP-structure on, the vote as ap_route found it (a ("found", vote or None) pair)."""
    if settings.fallback_a in ("embed", "bm25-ap") or settings.context_a != "section-route":
        return None
    try:
        variant = context.VARIANTS[settings.context_a]
        levels = set(settings.fallback_a.split("+"))
        if ap_found is not None:
            return variant.wide_route(pages, vote, claim_text, levels, found=ap_found[1])
        return variant.wide_route(pages, vote, claim_text, levels)
    except Exception as e:
        raw["wide_error"] = f"{type(e).__name__}: {e}"
        log.warning("%s: fallback level failed (%s)", raw.get("id"), raw["wide_error"])
        return None


def wide_prepared(case_id, raw, wide, pages, vote, claim_text, settings):
    """The Prepared case of a fallback level: numbered paragraphs with the routed prompt (L1) under the level's own
    version name; the answer and the evidence are handled exactly as for a routed case."""
    variant = context.VARIANTS[settings.context_a]
    level, paragraphs, names = wide
    version = variant.WIDE_PROMPT_VERSIONS[level] + ("-L1" if settings.label_rule_a else "")
    messages = nli.build_messages_a_paragraphs(variant.PART_LINES[level], variant.wide_texts(paragraphs, names),
                                               vote, claim_text, version)
    raw["prompt_version"], raw["route"] = version, level
    raw["paragraphs_sent"] = [[page, len(text)] for page, text in paragraphs]
    raw["pages_total"], raw["context_pages"] = len(pages), sorted({page for page, _ in paragraphs})
    return Prepared(case_id, raw, kind="A-paragraphs", messages=messages, vote=vote, claim_text=claim_text,
                    routed=(level, paragraphs), chat_args={"max_tokens": settings.max_tokens_a,
                                                           "json_schema": paragraph_schema(settings)})


def complete_a_pages(p, start, settings):
    """Task A with page context: the call; the answer names up to five pages, whose text becomes the evidence."""
    try:
        result = llm.chat(p.messages, **p.chat_args)
    except llm.LLMError as e:
        p.raw["error"] = str(e)
        note_call(p.raw, e)
        return response(p.case_id, FALLBACK_LABEL, start=start), "model call failed"

    note_call(p.raw, result)
    p.raw["answer"], p.raw["output_tokens"] = result.text, result.output_tokens
    label, page_numbers, reason = nli.parse_label_and_pages(result.text)
    if label is None:
        p.raw["parse_reason"] = reason
        return response(p.case_id, FALLBACK_LABEL, result.input_tokens, result.output_tokens, start), "unparseable answer"
    # Evidence comes from the pages that were sent; a page number outside them is ignored.
    cited = parse.evidence_items(p.shown, page_numbers) if label in (0, 2) else []
    status = "ok" if label == 1 or cited else "no valid pages for label 0/2"
    items = evidence.items(settings.evidence_a, cited, p.shown, p.claim_text, page_numbers) if label in (0, 2) else []
    return response(p.case_id, label, result.input_tokens, result.output_tokens, start, items), status


def paragraph_messages(routed, vote, claim_text, settings):
    """The prompt for a routed case: the PART line, the numbered paragraphs as shown, VOTE and CLAIM."""
    variant = context.VARIANTS[settings.context_a]
    part, paragraphs = routed
    return nli.build_messages_a_paragraphs(variant.PART_LINES[part], [variant.display(t) for _, t in paragraphs],
                                           vote, claim_text, paragraph_prompt_version(settings))


def paragraph_schema(settings):
    """The answer schema of a routed case: the coupled one with CS (session 10, step 6), else the plain one."""
    if not settings.schema_a:
        return None
    return nli.ANSWER_SCHEMA_A_COUPLED if settings.coupled_schema_a else nli.ANSWER_SCHEMA_A_PARAGRAPHS


def paragraph_prompt_version(settings):
    if settings.short_prompt_a:  # session 10, step 5: P-short (L1's sentence included)
        return "A-v5-short"
    version = context.VARIANTS[settings.context_a].PROMPT_VERSION
    return version + "-L1" if settings.label_rule_a else version


def complete_a_paragraphs(p, start, settings):
    """Task A for a routed case: one part of the vote as numbered paragraphs; the answer cites paragraphs,
    whose verbatim text and page become the evidence."""
    variant = context.VARIANTS[settings.context_a]
    part, paragraphs = p.routed
    try:
        result = llm.chat(p.messages, **p.chat_args)
    except llm.LLMError as e:
        p.raw["error"] = str(e)
        note_call(p.raw, e)
        return response(p.case_id, FALLBACK_LABEL, start=start), "model call failed"

    note_call(p.raw, result)
    p.raw["answer"], p.raw["output_tokens"] = result.text, result.output_tokens
    label, numbers, reason = nli.parse_label_and_pages(result.text, key="paragraphs")
    if label is None:
        p.raw["parse_reason"] = reason
        return response(p.case_id, FALLBACK_LABEL, result.input_tokens, result.output_tokens, start), "unparseable answer"
    input_tokens, output_tokens = result.input_tokens, result.output_tokens
    if label == 1 and numbers and settings.second_look_cited_a:
        second = second_look_cited(p, numbers, settings)
        if second is not None:
            result2, label2, numbers2, shown2 = second
            input_tokens, output_tokens = input_tokens + result2.input_tokens, output_tokens + result2.output_tokens
            if label2 in (0, 2):  # Apertus's second answer replaces the neutral one only if it is 0 or 2
                label, numbers, paragraphs = label2, numbers2, shown2
    if label == 1 and settings.second_look_a:
        second = second_look(p.routed, p.vote, p.claim_text, p.raw, settings)
        if second is not None:
            result2, label2, numbers2, shown2 = second
            input_tokens, output_tokens = input_tokens + result2.input_tokens, output_tokens + result2.output_tokens
            if label2 in (0, 2):  # only an entailment or contradiction replaces the first neutral answer
                label, numbers, paragraphs = label2, numbers2, shown2
    items = variant.evidence_items(paragraphs, numbers, halves=settings.evidence_halves_a) if label in (0, 2) else []
    status = "ok" if label == 1 or items else "no valid paragraphs for label 0/2"
    return response(p.case_id, label, input_tokens, output_tokens, start, items), status


def second_look_cited(p, numbers, settings):
    """SL (session 10, step 6; off by default): the first answer was neutral but cited paragraphs. Ask once more with
    only the cited paragraphs (in their order, numbered from 1) and the claim, prompt A-v4-second-look-cited (all
    three labels allowed). Returns (result, label, paragraph numbers, the cited paragraphs) or None when there is
    nothing valid to send or the call fails (the first answer stays). Recorded in raw["second_look_cited"]."""
    variant = context.VARIANTS[settings.context_a]
    part, paragraphs = p.routed
    cited = sorted({n for n in numbers if isinstance(n, int) and 1 <= n <= len(paragraphs)})
    if not cited:
        return None
    shown = [paragraphs[n - 1] for n in cited]
    messages = nli.build_messages_a_paragraphs(variant.PART_LINES[part], [variant.display(t) for _, t in shown],
                                               p.vote, p.claim_text, "A-v4-second-look-cited")
    p.raw["second_look_cited"] = {"cited": cited}
    try:
        result = llm.chat(messages, max_tokens=settings.max_tokens_a,
                          json_schema=nli.ANSWER_SCHEMA_A_PARAGRAPHS if settings.schema_a else None)
    except llm.LLMError as e:
        p.raw["second_look_cited"].update(error=str(e), attempts=e.attempts)
        return None
    label, numbers2, reason = nli.parse_label_and_pages(result.text, key="paragraphs")
    p.raw["second_look_cited"].update(answer=result.text, input_tokens=result.input_tokens,
                                      output_tokens=result.output_tokens, attempts=result.attempts,
                                      endpoint=result.endpoint)
    if label is None:
        p.raw["second_look_cited"]["parse_reason"] = reason
        return result, None, [], shown
    return result, label, numbers2, shown


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


def prepare_b(case, start, raw, settings):
    """Task B up to the model call: the reference (cut if long, by default) and the messages."""
    case_id = case["id"]
    try:
        reference_text = case["reference"]["text"]
        claim_text = case["claim"]["text"]
    except (KeyError, TypeError):
        return finished(case_id, raw, response(case_id, FALLBACK_LABEL, start=start),
                        "invalid request (missing reference.text or claim.text)")

    raw["prompt_version"] = settings.prompt_b
    messages, max_tokens, schema = None, settings.max_tokens_b, nli.ANSWER_SCHEMA_B if settings.schema_b else None
    if settings.context_b != "full":  # session 9, phase C: cut or numbered long passages
        raw["context_b"] = settings.context_b
        try:
            if settings.context_b in ("para", "unified"):
                # B-para (session 9): A-v4-section-route. B-U (session 10, step 9): task A's default routed prompt.
                version = "A-v4-section-route" if settings.context_b == "para" else paragraph_prompt_version(settings)
                texts = taskb_context.para_texts(reference_text, claim_text)
                raw["prompt_version"], raw["paragraphs_sent"] = version, len(texts)
                messages = nli.build_messages_a_paragraphs(taskb_context.PART_LINE, texts, case.get("vote", ""),
                                                           claim_text, version)
                max_tokens, schema = settings.max_tokens_a, nli.ANSWER_SCHEMA_A_PARAGRAPHS
            else:
                same_language = case["claim"].get("language") == case["reference"].get("language")
                if taskb_context.needs_translation(reference_text, settings.context_b, same_language):
                    # Session 12, step 3 (B-BM25, off): Apertus translates the claim first, in complete_b_translate
                    return Prepared(case_id, raw, kind="B-translate", claim_text=claim_text,
                                    ask=(case["reference"].get("language") or "", reference_text),
                                    chat_args={"max_tokens": max_tokens, "json_schema": schema})
                text = taskb_context.cut_text(reference_text, claim_text, settings.context_b, same_language)
                raw["chars_sent"] = len(text)
                messages = nli.build_messages_b(text, claim_text, settings.prompt_b)
        except Exception as e:  # e.g. no e5 files: the whole reference, as by default
            raw["context_b_error"] = f"{type(e).__name__}: {e}"
            model = taskb_context.ranking_model(settings.context_b, same_language_b(case))
            if model:  # session 12, step 2: later cases skip the model at once
                rankers.failed(model, e)
            messages, max_tokens = None, settings.max_tokens_b
            schema = nli.ANSWER_SCHEMA_B if settings.schema_b else None
            raw["prompt_version"] = settings.prompt_b
    return Prepared(case_id, raw, kind="B",
                    messages=messages or nli.build_messages_b(reference_text, claim_text, settings.prompt_b),
                    chat_args={"max_tokens": max_tokens, "json_schema": schema})


def complete_b(p, start, settings):
    """Task B: the call; label only."""
    try:
        result = llm.chat(p.messages, **p.chat_args)
    except llm.LLMError as e:
        p.raw["error"] = str(e)
        note_call(p.raw, e)
        return response(p.case_id, FALLBACK_LABEL, start=start), "model call failed"

    note_call(p.raw, result)
    p.raw["answer"] = result.text
    label, reason = nli.parse_label(result.text)
    status = "ok"
    if label is None:
        p.raw["parse_reason"] = reason
        label, status = FALLBACK_LABEL, "unparseable answer"
    return response(p.case_id, label, result.input_tokens, result.output_tokens, start), status


def same_language_b(case):
    try:
        return case["claim"].get("language") == case["reference"].get("language")
    except (AttributeError, KeyError, TypeError):
        return True


def complete_b_translate(p, start, settings):
    """Session 12, step 3 (B-BM25, off by default): a long reference in another language than the claim. Apertus
    translates the claim into the reference's language (one call, its tokens count in the case's metrics); BM25 ranks
    the paragraphs with that translation (with the claim itself if the call fails); the reading call then gets the
    cut reference and the claim as it is."""
    from src import ap_parse
    language, reference_text = p.ask
    translated, call = ap_parse.translate(p.claim_text, language)
    tokens = p.raw.setdefault("ap_tokens", [0, 0])
    tokens[0] += call.get("input_tokens", 0)
    tokens[1] += call.get("output_tokens", 0)
    p.raw.setdefault("ap_calls", []).append(call)
    text = taskb_context.cut_text(reference_text, translated or p.claim_text, settings.context_b, False)
    p.raw["chars_sent"] = len(text)
    q = Prepared(p.case_id, p.raw, kind="B", claim_text=p.claim_text, chat_args=p.chat_args,
                 messages=nli.build_messages_b(text, p.claim_text, settings.prompt_b))
    return complete_b(q, start, settings)


COMPLETE = {"B": complete_b, "A-pages": complete_a_pages, "A-paragraphs": complete_a_paragraphs,
            "A-ask-part": complete_a_ask_part, "B-translate": complete_b_translate, "A-translate": complete_a_translate}


def prepare(case, data_dir=".", settings=None):
    """Everything a case needs before its model call. Returns a Prepared (see there)."""
    from src import timing
    with timing.phase("prepare"):
        return _prepare(case, data_dir, settings)


def _prepare(case, data_dir=".", settings=None):
    settings = settings or Settings()
    start = time.perf_counter()  # the case's time starts here
    case_id = case["id"]
    task = task_of(case)
    raw = {"id": case_id, "task": task}
    rankers.ACTIVE["name"], rankers.CASE["guard"] = settings.ranker, None
    if settings.ranker != "e5":
        raw["ranker"] = settings.ranker
    if task is None:
        prepared = finished(case_id, raw, response(case_id, FALLBACK_LABEL, start=start),
                            "invalid request (needs exactly one of booklet/reference)")
    elif task == "A":
        prepared = prepare_a(case, data_dir, start, raw, settings)
    else:
        prepared = prepare_b(case, start, raw, settings)
    if rankers.CASE["guard"]:  # session 12, step 2: this case went on without its embedding model
        prepared.raw["ranker_guard"] = rankers.CASE["guard"]
    prepared.seconds = time.perf_counter() - start
    return prepared


def complete(prepared, settings=None):
    """The model call(s) of a prepared case and its response: (response, status, raw). The case's
    inference_time_ms is its preparation time plus the time from here to its response."""
    settings = settings or Settings()
    if prepared.kind == "done":
        resp, status = prepared.done
        add_ap_tokens(resp, prepared.raw)
        return resp, status, prepared.raw
    start = time.perf_counter() - prepared.seconds
    resp, status = COMPLETE[prepared.kind](prepared, start, settings)
    add_ap_tokens(resp, prepared.raw)
    return resp, status, prepared.raw


def add_ap_tokens(resp, raw):
    """Session 11, step 3: the tokens of Apertus's parsing calls of this case (if any) count in its metrics."""
    extra = raw.get("ap_tokens")
    if extra:
        resp["metrics"]["input_tokens"] += extra[0]
        resp["metrics"]["output_tokens"] += extra[1]


def predict(case, data_dir=".", settings=None):
    """Return (response, status, raw) for one case, prepared and completed at once (the sequential path).
    status is 'ok' or a failure kind; raw keeps details for analysis."""
    settings = settings or Settings()
    return complete(prepare(case, data_dir, settings), settings)


def needs_local_model(case, settings):
    """True for a case whose preparation loads or runs the embedding model before its request: a task B case
    whose reference is cut (B-cut or B-para, long references only). src/pipeline.py prepares the others first."""
    if task_of(case) != "B" or settings.context_b in ("full", "cut4-l", "cut4-bm25"):  # L and BM25 need no model
        return False
    try:
        if settings.context_b == "cut4-h" and case["claim"].get("language") == case["reference"].get("language"):
            return False  # selector H uses L for a pair in one language
        return taskb_context.is_long(case["reference"]["text"], settings.context_b)
    except (KeyError, TypeError):
        return False


def preparation_key(todo, settings):
    """The order in which src/pipeline.py prepares the cases (session 10): first the cases that need no local
    model before their request (all but long task B references), then by booklet in the order the booklets first
    appear, then in input order. Only the order of the work changes, never a request."""
    first_seen = {}
    for _, case in todo:
        first_seen.setdefault(booklet_path(case), len(first_seen))

    def key(case):
        return needs_local_model(case, settings), first_seen.get(booklet_path(case), 0)
    return key


def lane_key(todo):
    """The worker process a case is prepared in (src/pipeline.py: lane_key % workers): task A cases by booklet, in
    the order the booklets first appear, so each booklet is read by one process only; task B cases in lane 0."""
    first_seen = {}
    for _, case in todo:
        if booklet_path(case):
            first_seen.setdefault(booklet_path(case), len(first_seen))
    return lambda case: first_seen.get(booklet_path(case), 0)


def booklet_path(case):
    try:
        return str(case["booklet"]["path"])
    except (KeyError, TypeError):
        return ""


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
    parser.add_argument("--coupled-schema-a", action=argparse.BooleanOptionalAction, default=defaults.coupled_schema_a,
                        help="development only: CS, the coupled answer schema for routed cases (session 10, step 6)")
    parser.add_argument("--second-look-cited-a", action=argparse.BooleanOptionalAction,
                        default=defaults.second_look_cited_a,
                        help="development only: SL, a second call after a neutral answer that cites paragraphs (step 6)")
    parser.add_argument("--short-prompt-a", action=argparse.BooleanOptionalAction, default=defaults.short_prompt_a,
                        help="development only: P-short, the routed prompt in fewer words (session 10, step 5)")
    parser.add_argument("--second-look-a", action=argparse.BooleanOptionalAction, default=defaults.second_look_a,
                        help="development only: L2, a second call after a neutral answer (session 9, D)")
    parser.add_argument("--second-look-threshold", type=float, default=defaults.second_look_threshold,
                        help="development only: L2's similarity threshold")
    parser.add_argument("--evidence-a", default=defaults.evidence_a, choices=evidence.MODES,
                        help="development only: which task A evidence items to return")
    parser.add_argument("--ap-part-a", default=defaults.ap_part_a, choices=AP_PART_MODES,
                        help="development only: Apertus names the claim's part (session 11, step 3)")
    parser.add_argument("--ap-structure-a", default=defaults.ap_structure_a, choices=AP_STRUCTURE_MODES,
                        help="development only: Apertus reads the contents pages (session 11, step 3)")
    parser.add_argument("--fallback-a", default=defaults.fallback_a, choices=FALLBACK_LEVELS,
                        help="development only: what a case section-route cannot route gets (session 11, step 2)")
    parser.add_argument("--ranker", default=defaults.ranker, choices=rankers.NAMES,
                        help="development only: the local ranker of long parts, the fallback and cut4-r (session 12)")
    parser.add_argument("--workers", type=int, default=pipeline.default_workers(),
                        help="background processes that prepare cases while a request is in flight (session 10; "
                             "default 2, or 1 on a single CPU; each owns whole booklets); 0 runs every case in "
                             "turn, as before session 10")
    parser.add_argument("--in-flight", type=int, default=1, choices=(1, 2),
                        help="development only: model requests sent at the same time (with --workers > 0)")
    args = parser.parse_args()
    settings = Settings(prompt_b=args.prompt_b, schema_b=args.schema_b, max_tokens_b=args.max_tokens_b,
                        max_tokens_a=args.max_tokens_a, json_mode_a=args.json_mode_a,
                        schema_a=args.schema_a, context_a=args.context_a,
                        evidence_a=args.evidence_a, evidence_halves_a=args.evidence_halves_a,
                        context_b=args.context_b, label_rule_a=args.label_rule_a, second_look_a=args.second_look_a,
                        second_look_threshold=args.second_look_threshold, section_top_k_a=args.section_top_k_a,
                        short_prompt_a=args.short_prompt_a, coupled_schema_a=args.coupled_schema_a,
                        second_look_cited_a=args.second_look_cited_a, fallback_a=args.fallback_a,
                        ap_part_a=args.ap_part_a, ap_structure_a=args.ap_structure_a, ranker=args.ranker)
    if args.input.resolve() == args.output.resolve():
        parser.error("Input and output must be different files.")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s", stream=sys.stderr)
    logging.getLogger("pypdf").setLevel(logging.ERROR)  # font warnings are noise here
    # Session 12, step 2: the memory guard. Below the memory the ranker's model needs, or without its files, the whole
    # run uses no embedding model (src/rankers.py), so that no case is lost to an out-of-memory kill.
    ranker, guard_reason = rankers.run_guard(settings.ranker, pipeline.cgroup_memory())
    if guard_reason:
        log.warning("Memory guard: %s; this run uses no embedding model", guard_reason)
        settings = dataclasses.replace(settings, ranker=ranker)

    env.load_env_file()
    lines = read_lines(args.input)
    failures = Counter()
    answered = set()  # ids already answered (as JSON text, so any id value can be compared)
    todo = []  # (line number, case): every case that gets a response
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
        todo.append((number, case))

    data_dir = args.input.resolve().parent
    counts = {"written": 0, "routing_failed": 0, "no_model": 0}  # routing_failed: routing raised, the case ran as the
    # fallback; no_model (session 12, step 2): the case was prepared without an embedding model (memory guard)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.raw:
        args.raw.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("wb") as out, (args.raw.open("wb") if args.raw else contextlib.nullcontext()) as raw_out:
        def emit(number, case, result):
            resp, status, raw = result
            if status != "ok":
                failures[status] += 1
            counts["routing_failed"] += "route_error" in raw
            counts["no_model"] += "ranker_guard" in raw or raw.get("ranker") == "none"
            log.info("[%d/%d] %s -> %s%s", number, len(lines), case["id"], resp["label_name"],
                     "" if status == "ok" else f" (fallback: {status})")
            write_line(out, resp)
            if raw_out is not None:
                write_line(raw_out, raw)
            counts["written"] += 1

        def guarded(step):
            def run_step(arg):
                try:
                    return step(arg)
                except Exception as e:  # never let one case stop the run
                    case_id = arg["id"] if isinstance(arg, dict) else arg.case_id
                    return response(case_id, FALLBACK_LABEL), f"unexpected error ({type(e).__name__})", {"id": case_id}
            return run_step

        sequential = guarded(lambda case: predict(case, data_dir, settings))
        # Session 11, step 3: Apertus's parsing calls are made while a case is prepared, so with them on every case
        # is prepared and completed in turn (requests stay one at a time).
        if args.workers == 0 or ap_in_prepare(settings):  # the sequential path: each case prepared and completed in turn
            for number, case in todo:
                emit(number, case, sequential(case))
        else:
            pipeline.run(todo, functools.partial(prepare, data_dir=data_dir, settings=settings),
                         guarded(lambda p: complete(p, settings)),
                         sequential, emit, workers=args.workers, in_flight=args.in_flight,
                         order_key=preparation_key(todo, settings), lane_key=lane_key(todo))
    written, routing_failed = counts["written"], counts["routing_failed"]

    log.info("Wrote %d responses to %s", written, args.output)
    if routing_failed:
        log.warning("Routing failed and the case ran as the fallback variant: %d", routing_failed)
    if counts["no_model"]:
        log.warning("Cases prepared without an embedding model (memory guard): %d", counts["no_model"])
    if failures:
        log.warning("Fallback or skipped cases: %s", ", ".join(f"{k}: {v}" for k, v in failures.most_common()))
    else:
        log.info("No failures.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
