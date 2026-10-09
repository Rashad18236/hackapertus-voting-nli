"""Prompt construction and answer parsing.

Task B (reference passage): the model answers {"label": 0|1|2}. Evidence is
not scored for task B (official contract), so we no longer ask for it: that
saves output tokens and removes the long quotes that broke the JSON in the
v1 baseline.

The prompt is in English; claims and references are passed through untouched,
never translated.

parse_label() returns None when the answer cannot be read. It never guesses;
the caller decides what to write (src/cli.py writes the contract's fallback
label and logs the failure).
"""

import json
import re

LABEL_NAMES = {0: "entailment", 1: "neutral", 2: "contradiction"}

# Task B prompts, by version name. Every run in docs/results.md names the
# version it used. DEFAULT_PROMPT_B is what the pipeline uses unless the
# development flag --prompt-b selects another one.
PROMPTS_B = {}

PROMPTS_B["v2-label-only"] = """You are a careful fact checker for official Swiss federal voting booklets.

You get a REFERENCE TEXT from a voting booklet and a CLAIM. They may be in different languages (German, French or Italian). The reference text is the only source of truth: do not use outside knowledge, even if you know the claim is true or false in the real world.

Choose exactly one label:
0 = entailment: the reference text supports the claim (states it or clearly implies it).
1 = neutral: the reference text gives insufficient information to decide. A claim that is true in the real world but not covered by the reference text is neutral.
2 = contradiction: the reference text refutes the claim (states something that makes it false).

Answer with one JSON object and nothing else:
{"label": <0, 1 or 2>}"""

# v3: only the decision rule changes. Subject first; contradiction needs an
# incompatible statement; missing information is never a contradiction.
PROMPTS_B["v3-topic-first"] = """You check a CLAIM against a REFERENCE TEXT from an official Swiss federal voting booklet. They may be in different languages (German, French or Italian). Use only the reference text, never outside knowledge.

Decide in this order:
1. Does the reference text deal with the subject of the claim at all? If not, the label is 1 (neutral).
2. If it does:
   0 (entailment) if the reference text supports the claim;
   2 (contradiction) only if the reference text states something that cannot be true together with the claim;
   otherwise 1 (neutral: insufficient information).
Missing information is never a contradiction. A claim of the form "according to the text / the committee / the Federal Council, X" is neutral when the reference text does not deal with X.

Answer with one JSON object and nothing else:
{"label": <0, 1 or 2>}"""

# v4: v3 plus three short examples, one per label. Written for this purpose
# (an invented ballot on water supply); not taken from the dataset.
_EXAMPLES_B = """
Examples (an invented ballot, for illustration only):
REFERENCE TEXT: Der Bundesrat empfiehlt, das Gesetz über die Wasserversorgung anzunehmen.
CLAIM: Selon le texte, le Conseil fédéral recommande d'accepter la loi sur l'approvisionnement en eau.
{"label": 0}
REFERENCE TEXT: Die Vorlage regelt die Finanzierung der Wasserversorgung in Berggebieten.
CLAIM: Secondo il testo, la proposta prevede 12 nuove stazioni di ricarica per auto elettriche.
{"label": 1}
REFERENCE TEXT: Der Bund zahlt einen Beitrag von 40 Millionen Franken pro Jahr.
CLAIM: Secondo il testo, la Confederazione versa un contributo di 80 milioni di franchi all'anno.
{"label": 2}
"""
_ANSWER_B = 'Answer with one JSON object and nothing else:\n{"label": <0, 1 or 2>}'
assert PROMPTS_B["v3-topic-first"].endswith(_ANSWER_B)
PROMPTS_B["v4-topic-first-examples"] = (
    PROMPTS_B["v3-topic-first"][: -len(_ANSWER_B)] + _EXAMPLES_B.lstrip("\n") + "\n" + _ANSWER_B
)

# Task A: the whole booklet, page by page. Same decision rule as task B's
# v3-topic-first; the answer also names the pages that justify the label.
_RULE_A = """You check a CLAIM against an official Swiss federal voting booklet. The booklet is given page by page; each page starts with a line "=== PAGE n ===". A booklet can cover several ballots: use only the part about the ballot named in VOTE. The booklet and the claim may be in different languages (German, French or Italian). Use only the booklet, never outside knowledge.

Decide in this order:
1. Does the booklet's part on VOTE deal with the subject of the claim at all? If not, the label is 1 (neutral).
2. If it does:
   0 (entailment) if the booklet supports the claim;
   2 (contradiction) only if the booklet states something that cannot be true together with the claim;
   otherwise 1 (neutral: insufficient information).
Missing information is never a contradiction. A claim of the form "according to the text / the committee / the Federal Council, X" is neutral when the booklet does not deal with X.
"""

PROMPTS_A = {}
# A-v1: stopped after 2 cases: the model always returned "pages": [] with this format line.
PROMPTS_A["A-v1-fulldoc"] = _RULE_A + """
Answer with one JSON object and nothing else:
{"label": <0, 1 or 2>, "pages": [<for label 0 or 2: up to five page numbers whose text justifies the label, most relevant first; prefer the detailed section on the ballot over the summary at the front. For label 1: []>]}"""
# A-v2: same rule; concrete example and an explicit page rule. Tried on 3 cases: still "pages": [].
PROMPTS_A["A-v2-fulldoc"] = _RULE_A + """
Also name the pages that justify your label: the numbers n from the "=== PAGE n ===" lines, at most five, most relevant first. Prefer pages from the detailed section on the ballot over the short summary at the front of the booklet. For label 0 or 2 you must name at least one page. Only for label 1, use an empty list.

Answer with one JSON object and nothing else, for example:
{"label": 0, "pages": [14, 15]}"""
# A-v3: same rule; pages are asked for FIRST, before the label. On the same 3 cases
# the model then named pages every time. This is the full-document baseline prompt.
PROMPTS_A["A-v3-fulldoc"] = _RULE_A + """
First find the pages of the booklet that are relevant to the claim: the numbers n from the "=== PAGE n ===" lines, at most five, most relevant first, preferring the detailed section on the ballot over the short summary at the front. Then decide the label.

Answer with one JSON object and nothing else, pages first, for example:
{"pages": [14, 15], "label": 0}"""
PROMPT_VERSION_A = "A-v3-fulldoc"

# The task A answer as a JSON Schema, for schema-constrained output (--schema-a):
# the endpoint can then only produce {"pages": [up to 5 ints], "label": 0|1|2}.
ANSWER_SCHEMA_A = {
    "type": "object",
    "properties": {
        "pages": {"type": "array", "items": {"type": "integer"}, "maxItems": 5},
        "label": {"type": "integer", "enum": [0, 1, 2]},
    },
    "required": ["pages", "label"],
    "additionalProperties": False,
}

# A-v3-excerpts: A-v3-fulldoc with only the description of the input changed, for
# selected context (src/contexts/embed_e5_small.py): the model sees the passages most similar
# to the claim, not the whole booklet. Rule and answer format are identical.
_INPUT_FULLDOC = 'The booklet is given page by page; each page starts with a line "=== PAGE n ===".'
_INPUT_EXCERPTS = ('You get only excerpts of the booklet: the passages most similar to the claim, in page order; '
                   'each excerpt starts with a line "=== PAGE n ===" naming its page.')
assert _INPUT_FULLDOC in PROMPTS_A["A-v3-fulldoc"]
PROMPTS_A["A-v3-excerpts"] = PROMPTS_A["A-v3-fulldoc"].replace(_INPUT_FULLDOC, _INPUT_EXCERPTS)

# A-v4-section-route (session 6), for the context variant "section-route": one part of the
# vote's section (the part the claim's opening names, src/claim_router.py) as numbered
# paragraphs. The decision rule is task B's v3-topic-first, word for word; one line names the
# part and whose voice it is; the answer names up to three paragraphs instead of pages.
_RULE_B = PROMPTS_B["v3-topic-first"][PROMPTS_B["v3-topic-first"].index("Decide in this order:"):
                                      PROMPTS_B["v3-topic-first"].index("Answer with one JSON object")].strip()
PROMPTS_A["A-v4-section-route"] = f"""You check a CLAIM against a REFERENCE TEXT from an official Swiss federal voting booklet. The reference text is one part of the booklet's section on the ballot named in VOTE, given as numbered paragraphs ("[n] ..."); the line PART says which part it is and whose voice it is. The reference text and the claim may be in different languages (German, French or Italian). Use only the reference text, never outside knowledge.

{_RULE_B}

First give the numbers of the paragraphs that justify your label, at most three, most relevant first (for label 1, an empty list). Then the label.

Answer with one JSON object and nothing else, paragraphs first, for example:
{{"paragraphs": [2, 5], "label": 0}}"""

ANSWER_SCHEMA_A_PARAGRAPHS = {
    "type": "object",
    "properties": {
        "paragraphs": {"type": "array", "items": {"type": "integer"}, "maxItems": 3},
        "label": {"type": "integer", "enum": [0, 1, 2]},
    },
    "required": ["paragraphs", "label"],
    "additionalProperties": False,
}


def build_messages_a_paragraphs(part_line, paragraph_texts, vote, claim_text, version="A-v4-section-route"):
    """Messages for a routed part: PART line, numbered paragraphs (as shown), VOTE and CLAIM."""
    numbered = "\n".join(f"[{i}] {text}" for i, text in enumerate(paragraph_texts, start=1))
    user = f"PART: {part_line}\n\nREFERENCE TEXT:\n{numbered}\n\nVOTE: {vote}\n\nCLAIM:\n{claim_text}"
    return [
        {"role": "system", "content": PROMPTS_A[version]},
        {"role": "user", "content": user},
    ]


def build_messages_a(booklet_text, vote, claim_text, version=PROMPT_VERSION_A):
    heading = "BOOKLET EXCERPTS" if version == "A-v3-excerpts" else "BOOKLET"
    user = f"{heading}:\n{booklet_text}\n\nVOTE: {vote}\n\nCLAIM:\n{claim_text}"
    return [
        {"role": "system", "content": PROMPTS_A[version]},
        {"role": "user", "content": user},
    ]


# An explicit label statement in prose, e.g. "Therefore, the label is 0 (entailment)".
_PROSE_LABEL = re.compile(r"\blabel\s*(?:is|:|=)\s*\(?\s*([012])\b", re.IGNORECASE)


def label_from_prose(answer):
    """Return the label stated in prose, or None.

    Only an explicit "label is N" / "label: N" counts, and only if every such
    statement in the answer names the same label; conflicting statements (for
    example an echo of the instructions) give None. This reads the model's own
    answer; it never guesses.
    """
    found = {int(m) for m in _PROSE_LABEL.findall(answer)}
    return found.pop() if len(found) == 1 else None


def parse_label_and_pages(answer, key="pages"):
    """Return (label or None, numbers, reason). numbers: the list under `key` ("pages", or
    "paragraphs" for A-v4-section-route) as ints as given, possibly empty.

    A JSON object is preferred. Without one, an explicit label statement in
    prose is accepted (no numbers then); see label_from_prose.
    """
    obj = _first_json_object(answer)
    if obj is None:
        label = label_from_prose(answer)
        if label is not None:
            return label, [], ""
        return None, [], "no JSON object"
    label = _read_label(obj.get("label"))
    if label is None:
        return None, [], f"invalid label {obj.get('label')!r}"
    pages = []
    raw_pages = obj.get(key)
    if isinstance(raw_pages, list):
        for p in raw_pages:
            if isinstance(p, bool):
                continue
            if isinstance(p, int):
                pages.append(p)
            elif isinstance(p, str) and p.strip().isdigit():
                pages.append(int(p.strip()))
    return label, pages, ""


DEFAULT_PROMPT_B = "v3-topic-first"  # best on dev (session 2, Run A)


def build_messages_b(reference_text, claim_text, version=DEFAULT_PROMPT_B):
    user = f"REFERENCE TEXT:\n{reference_text}\n\nCLAIM:\n{claim_text}"
    return [
        {"role": "system", "content": PROMPTS_B[version]},
        {"role": "user", "content": user},
    ]


def _first_json_object(text):
    """Return the first JSON object found in text, or None.

    Tolerates code fences and prose around the object.
    """
    decoder = json.JSONDecoder()
    for start in [m.start() for m in re.finditer(r"\{", text)]:
        try:
            obj, _ = decoder.raw_decode(text, start)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    return None


def _read_label(value):
    """Accept 0/1/2 as int or digit string, or an exact label name. Else None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value in LABEL_NAMES:
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("0", "1", "2"):
            return int(v)
        for number, name in LABEL_NAMES.items():
            if v == name:
                return number
    return None


def parse_label(answer):
    """Return (label or None, reason). reason is "" on success."""
    obj = _first_json_object(answer)
    if obj is None:
        return None, "no JSON object"
    label = _read_label(obj.get("label"))
    if label is None:
        return None, f"invalid label {obj.get('label')!r}"
    return label, ""


def find_verbatim(quote, reference_text):
    """Return the passage of reference_text that the quote points to, or None.

    Not used by task B any more; kept for task A evidence. An exact substring
    is returned as is. Otherwise differences in whitespace and letter case are
    allowed, and the reference's own characters are returned, so the result
    is always verbatim. Any other change means no match.
    """
    quote = quote.strip()
    if not quote:
        return None
    if quote in reference_text:
        return quote
    pattern = r"\s+".join(re.escape(w) for w in quote.split())
    match = re.search(pattern, reference_text) or re.search(pattern, reference_text, re.IGNORECASE)
    return match.group(0) if match else None
