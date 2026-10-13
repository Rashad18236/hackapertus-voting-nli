"""Apertus in the parsing roles (session 11, step 3; every role is off by default).

The challenge page asks to parse the booklet and the claims using Apertus. This module measures two roles; what
the router and the parser decide by rules stays as it is unless a role passes its rule (docs/decisions):

- AP-structure: Apertus reads the booklet's contents pages (the pages src/booklet.py reads for its contents) in one
  call per booklet and lists each vote with its title and the start pages of its summary, detailed section,
  arguments and legal text. The answer is never trusted as it is: each vote goes through the same heading checks as
  a contents entry the parser read itself (booklet._parse_vote), and a part that fails them is not used.
- AP-claim: Apertus reads the claim in one call and names the part of the booklet its opening refers to (or
  "none"), and gives the claim's statement without the opening, in the booklet's language.

Apertus never decides a label here: these calls only choose what the reading call shows. Every call counts as
tokens; the structure call is made once per booklet (and cached per booklet text), so its tokens are spread over
that booklet's cases in the reports.
"""

import hashlib
import json

from src import booklet, llm, memo

STRUCTURE_VERSION = "AP-structure-v1"
CLAIM_VERSION = "AP-claim-v1"
CONTENTS_PAGES = 6  # booklet.contents_entries reads the first six pages

STRUCTURE_PROMPT = """You read the first pages of an official Swiss federal voting booklet (German, French or Italian). They contain its table of contents. List every vote (ballot) the contents name, in the order they appear, with:
- "title": the vote's title as printed in the contents;
- "summary", "detail", "arguments", "law": the page number where the contents say that vote's summary ("In Kürze", "En bref", "In breve"), detailed explanation ("Im Detail", "En détail", "In dettaglio"), arguments ("Argumente", "Arguments", "Gli argomenti") and text put to the vote ("Abstimmungstext", "Texte soumis au vote", "Testo in votazione") start; null if the contents give no page for it.
Use only page numbers printed in the contents; never guess. Answer with JSON only."""

STRUCTURE_SCHEMA = {
    "type": "object",
    "properties": {"votes": {"type": "array", "maxItems": 8, "items": {
        "type": "object",
        "properties": {"title": {"type": "string"},
                       **{k: {"type": ["integer", "null"]} for k in ("summary", "detail", "arguments", "law")}},
        "required": ["title", "summary", "detail", "arguments", "law"],
        "additionalProperties": False}}},
    "required": ["votes"],
    "additionalProperties": False,
}

CLAIM_PROMPT = """A CLAIM about a Swiss federal vote opens with words that name its source in the official voting booklet. Say which part of the booklet the opening names:
- "summary": the booklet's summary of the vote ("according to the summary", "in brief");
- "detail": what happens if the vote is accepted, the detailed explanation;
- "committee": the initiative or referendum committee, its arguments;
- "council": the Federal Council (and Parliament), its arguments;
- "law": the text put to the vote, the legal text itself;
- "none": the opening names no source.
Also give "statement": what the claim says, without the opening that names the source, translated into LANGUAGE (de German, fr French, it Italian) if it is in another language. Answer with JSON only."""

PARTS = ("summary", "detail", "committee", "council", "law", "none")
CLAIM_SCHEMA = {
    "type": "object",
    "properties": {"part": {"type": "string", "enum": list(PARTS)}, "statement": {"type": "string"}},
    "required": ["part", "statement"],
    "additionalProperties": False,
}

_structures = {}  # SHA-256 of the contents pages -> (entries or None, call record)


def contents_text(pages, first_pages=CONTENTS_PAGES):
    """The pages the parser reads for the contents, each with a page marker."""
    return "\n\n".join(f"=== PAGE {n} ===\n{pages[n].strip()}" for n in sorted(pages)[:first_pages])


def structure_messages(pages):
    return [{"role": "system", "content": STRUCTURE_PROMPT}, {"role": "user", "content": contents_text(pages)}]


def structure(pages, max_tokens=700):
    """(entries, call) for a booklet: entries is Apertus's list of votes ({title, summary, detail, arguments, law})
    or None when the call fails or its answer cannot be read; call records tokens and whether this request was the
    first for the booklet (only then were tokens spent). Asked once per booklet text."""
    key = hashlib.sha256(contents_text(pages).encode("utf-8")).hexdigest()
    first = key not in _structures
    entries, call = memo.once(_structures, key, lambda: _ask_structure(pages, max_tokens))
    return entries, dict(call, first=first)


def _ask_structure(pages, max_tokens):
    call = {"version": STRUCTURE_VERSION, "input_tokens": 0, "output_tokens": 0}
    try:
        result = llm.chat(structure_messages(pages), max_tokens=max_tokens, json_schema=STRUCTURE_SCHEMA)
    except llm.LLMError as e:
        call["error"] = str(e)[:200]
        return None, call
    call.update(input_tokens=result.input_tokens, output_tokens=result.output_tokens, answer=result.text,
                endpoint=result.endpoint)
    try:
        votes = json.loads(result.text)["votes"]
        entries = [{"title": str(v["title"]), **{k: v.get(k) for k in ("summary", "detail", "arguments", "law")}}
                   for v in votes]
    except (ValueError, KeyError, TypeError):
        call["parse_reason"] = "unreadable structure answer"
        return None, call
    return entries, call


def booklet_from_entries(pages, entries):
    """A Booklet built from Apertus's entries with the parser's own checks (booklet._parse_vote): every start page
    must carry its heading, the pages must be in order, the arguments' sub-sections must agree. A part that fails
    its checks is not valid, exactly as for a contents entry the parser read itself. None without usable entries."""
    blocks = []
    for e in entries or []:
        s = e.get("summary")
        if not isinstance(s, int):
            continue
        b = {"title": e.get("title", ""), "summary": (s, s)}
        for k in ("detail", "arguments", "law"):
            if isinstance(e.get(k), int):
                b[k] = e[k]
        blocks.append(b)
    if not blocks:
        return None
    blocks.sort(key=lambda b: b["summary"][0])
    first_detail = min((b.get("detail", 10**6) for b in blocks), default=None)
    votes = []
    for i, b in enumerate(blocks):
        vote = booklet.Vote(title=b["title"], entry={k: v for k, v in b.items() if k != "title"})
        votes.append(vote)
        try:
            booklet._parse_vote(pages, blocks, i, b, first_detail, max(pages), vote)
        except Exception as e:  # an answer with odd numbers must not stop the case
            vote.problems.append(f"structure check failed: {type(e).__name__}")
            vote.parts, vote.valid, vote.ok = {}, set(), False
    return booklet.Booklet(votes=votes)


def claim_messages(claim_text, language):
    return [{"role": "system", "content": CLAIM_PROMPT},
            {"role": "user", "content": f"LANGUAGE: {language}\n\nCLAIM:\n{claim_text}"}]


def claim(claim_text, language, max_tokens=200):
    """(part or None for "none", statement or None, call record) from one call; (None, None, call) on failure."""
    call = {"version": CLAIM_VERSION, "input_tokens": 0, "output_tokens": 0}
    try:
        result = llm.chat(claim_messages(claim_text, language), max_tokens=max_tokens, json_schema=CLAIM_SCHEMA)
    except llm.LLMError as e:
        call["error"] = str(e)[:200]
        return None, None, call
    call.update(input_tokens=result.input_tokens, output_tokens=result.output_tokens, answer=result.text,
                endpoint=result.endpoint)
    try:
        answer = json.loads(result.text)
        part, statement = answer["part"], str(answer["statement"]).strip()
    except (ValueError, KeyError, TypeError):
        call["parse_reason"] = "unreadable claim answer"
        return None, None, call
    if part not in PARTS:
        call["parse_reason"] = f"unknown part {part!r}"
        return None, None, call
    return (None if part == "none" else part), (statement or None), call


# ---------------------------------------------------------------- session 12, step 3: Apertus translates a claim

TRANSLATE_VERSION = "AP-translate-v1"
LANGUAGE_NAMES = {"de": "German", "fr": "French", "it": "Italian"}
TRANSLATE_PROMPT = """You translate a CLAIM about a Swiss federal vote into the language named in TARGET (German, French or Italian). Translate faithfully: keep every name, number, date and amount, add nothing and leave nothing out. Answer with one JSON object and nothing else, for example: {"translation": "..."}"""
TRANSLATE_SCHEMA = {"type": "object", "properties": {"translation": {"type": "string"}}, "required": ["translation"],
                    "additionalProperties": False}


def translate_messages(claim_text, target_language):
    return [{"role": "system", "content": TRANSLATE_PROMPT},
            {"role": "user", "content": f"TARGET: {LANGUAGE_NAMES.get(target_language, target_language)}\n\n"
                                        f"CLAIM:\n{claim_text}"}]


def translate(claim_text, target_language, max_tokens=256):
    """(the claim in the target language, or None, call record) from one call. Apertus's text is used only to choose
    which paragraphs the reading call shows; the reading call itself gets the claim as it is."""
    call = {"version": TRANSLATE_VERSION, "input_tokens": 0, "output_tokens": 0}
    try:
        result = llm.chat(translate_messages(claim_text, target_language), max_tokens=max_tokens,
                          json_schema=TRANSLATE_SCHEMA)
    except llm.LLMError as e:
        call["error"] = str(e)[:200]
        return None, call
    call.update(input_tokens=result.input_tokens, output_tokens=result.output_tokens, answer=result.text,
                endpoint=result.endpoint)
    try:
        text = str(json.loads(result.text)["translation"]).strip()
    except (ValueError, KeyError, TypeError):
        call["parse_reason"] = "unreadable translation answer"
        return None, call
    return (text or None), call
