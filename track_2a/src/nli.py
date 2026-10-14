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

# v5-min (task B cheap fixes; prepared while the canary stopped the stage on 2026-10-09).
# For use with --schema-b only: strict JSON fixes the answer format, so the prompt has no format
# instructions. Fixed instructions: 77 tokens here plus 9 for the user message's labels = 86 (Apertus
# tokenizer; at most 90 asked). Keeps v3's three rules: another ballot or subject is neutral;
# contradiction only when both cannot be true; missing information is neutral, never contradiction.
PROMPTS_B["v5-min"] = """Compare the CLAIM with the REFERENCE TEXT from a Swiss voting booklet (German, French or Italian). Use only the reference text.
0: the reference supports the claim.
2: claim and reference cannot both be true.
1: otherwise, including when the reference is about a different ballot or subject than the claim. Missing information is 1, never 2."""

# v5-ballot (task B cheap fixes, continued): v5-min plus one sentence, BALLOT_SENTENCE, after "Use only the
# reference text.": every task B passage starts with the title of its own ballot, and most v3 errors on dev were
# claims about another ballot called a contradiction. The sentence adds 14 tokens (Apertus v1 tokenizer): 91
# here plus 9 for the user message's labels = 100. Also for --schema-b only.
# Session 10, step 5 (off by default). BP-short: v3-topic-first's rules in fewer words (fixed text at most 150
# tokens with the Apertus v1 tokenizer), label names from the dataset README word for word (see A-v5-short).
PROMPTS_B["v6-short"] = """Check a CLAIM against a REFERENCE TEXT from a Swiss voting booklet. Languages may differ. Use only the reference text.

1 (Unrelated / Neutral) if the reference text does not deal with the claim's subject. Otherwise 0 (Entailment) if it supports the claim; 2 (Contradiction) only if it states something that cannot be true together with the claim; else 1.
Missing information is never a contradiction. "According to the text / committee / Federal Council, X" is 1 if the text does not deal with X.

JSON only: {"label": <0, 1 or 2>}"""

BALLOT_SENTENCE = "The first line of the reference text names the ballot it is about."
PROMPTS_B["v5-ballot"] = PROMPTS_B["v5-min"].replace(
    "Use only the reference text.", "Use only the reference text. " + BALLOT_SENTENCE, 1)

# The task B answer as a JSON Schema, for schema-constrained output (--schema-b; task B cheap fixes):
# the endpoint can then only produce {"label": 0|1|2}. Same mechanism as ANSWER_SCHEMA_A.
ANSWER_SCHEMA_B = {
    "type": "object",
    "properties": {"label": {"type": "integer", "enum": [0, 1, 2]}},
    "required": ["label"],
    "additionalProperties": False,
}

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

# Session 9, phase D (off by default). L1: the routed prompt plus one sentence on what makes a contradiction.
L1_SENTENCE = ("A claim that gives a different number, share, date, actor or direction than the reference text gives "
               "for the same thing is a contradiction.")
PROMPTS_A["A-v4-section-route-L1"] = PROMPTS_A["A-v4-section-route"].replace(
    _RULE_B, _RULE_B + "\n" + L1_SENTENCE)
assert PROMPTS_A["A-v4-section-route-L1"] != PROMPTS_A["A-v4-section-route"]
# Session 11, step 2: the two fallback levels send the routed prompt with L1's sentence under their own version names
# (their PART line says what the paragraphs are: src/contexts/section_route.py).
for _level in ("vote-wide", "booklet-wide"):
    PROMPTS_A[f"A-v4-{_level}"] = PROMPTS_A["A-v4-section-route"]
    PROMPTS_A[f"A-v4-{_level}-L1"] = PROMPTS_A["A-v4-section-route-L1"]

# Session 10, step 5 (off by default). P-short: the routed prompt with the same rules in fewer words (fixed text at
# most 200 tokens with the Apertus v1 tokenizer, user labels included); L1's sentence stays word for word. The label
# names are the dataset README's, word for word ("Entailment (0), Unrelated / Neutral (1) or Contradiction (2)";
# the README at commit fc2b2760 is the first with label definitions).
PROMPTS_A["A-v5-short"] = f"""REFERENCE TEXT: numbered paragraphs, one PART of a Swiss voting booklet on the ballot in VOTE. Check the CLAIM against it alone; languages may differ.

1 (Unrelated / Neutral) if it does not deal with the claim's subject; else 0 (Entailment) if it supports the claim, 2 (Contradiction) only if it states something that cannot be true together with the claim, otherwise 1.
Missing information is never a contradiction. "According to the committee / Federal Council, X" is 1 if the text does not deal with X.
{L1_SENTENCE}

JSON only; justifying paragraphs first (up to three, none for 1):
{{"paragraphs": [2, 5], "label": 0}}"""

# L2: a second look at a neutral answer, with the three paragraphs most similar to the claim, asking 0, then 2,
# then 1.
PROMPTS_A["A-v4-second-look"] = """You check a CLAIM against a REFERENCE TEXT from an official Swiss federal voting booklet. The reference text is the three paragraphs ("[n] ...") closest to the claim from one part of the booklet's section on the ballot named in VOTE; the line PART says which part it is and whose voice it is. The reference text and the claim may be in different languages (German, French or Italian). Use only the reference text, never outside knowledge.

Decide in this order:
0 (entailment) if the reference text supports the claim;
2 (contradiction) if the reference text states something that cannot be true together with the claim;
1 (neutral) only if neither: the reference text does not deal with the subject of the claim, or does not say enough to decide.
Missing information is never a contradiction.

First give the numbers of the paragraphs that justify your label, at most three, most relevant first (for label 1, an empty list). Then the label.

Answer with one JSON object and nothing else, paragraphs first, for example:
{"paragraphs": [2], "label": 0}"""

# Session 9, E2 (information only): no booklet text. The answer keeps task A's schema; "pages" stays empty.
PROMPTS_A["A-v0-closed-book"] = """You get a CLAIM about the official Swiss federal voting booklet's section on the ballot named in VOTE, but not the booklet itself. Decide from what you know about this ballot and its booklet:
0 (entailment) if the booklet supports the claim;
2 (contradiction) if the booklet states something that cannot be true together with the claim;
1 (neutral) if the booklet does not deal with the claim, or you cannot tell.
The claim may be in German, French or Italian.

Answer with one JSON object and nothing else, with an empty list of pages, for example:
{"pages": [], "label": 0}"""

ANSWER_SCHEMA_A_PARAGRAPHS = {
    "type": "object",
    "properties": {
        "paragraphs": {"type": "array", "items": {"type": "integer"}, "maxItems": 3},
        "label": {"type": "integer", "enum": [0, 1, 2]},
    },
    "required": ["paragraphs", "label"],
    "additionalProperties": False,
}


# Session 10, step 6 (CS, off by default): the routed answer with its two parts coupled. A neutral answer cites no
# paragraph; an entailment or a contradiction cites one to three. Needs an endpoint that enforces anyOf.
ANSWER_SCHEMA_A_COUPLED = {
    "anyOf": [
        {"type": "object",
         "properties": {"paragraphs": {"type": "array", "items": {"type": "integer"}, "maxItems": 0},
                        "label": {"type": "integer", "enum": [1]}},
         "required": ["paragraphs", "label"], "additionalProperties": False},
        {"type": "object",
         "properties": {"paragraphs": {"type": "array", "items": {"type": "integer"}, "minItems": 1, "maxItems": 3},
                        "label": {"type": "integer", "enum": [0, 2]}},
         "required": ["paragraphs", "label"], "additionalProperties": False},
    ]
}

# Session 10, step 6 (SL, off by default): after a neutral answer that still cites paragraphs, one more call with
# only the cited paragraphs. A-v4-second-look with its first sentence adapted; all three labels allowed.
PROMPTS_A["A-v4-second-look-cited"] = PROMPTS_A["A-v4-second-look"].replace(
    'The reference text is the three paragraphs ("[n] ...") closest to the claim from one part',
    'The reference text is the paragraphs ("[n] ...") cited for the claim from one part')
assert PROMPTS_A["A-v4-second-look-cited"] != PROMPTS_A["A-v4-second-look"]


# Session 13, step 1 (all off by default): five rewrites of the routed prompt against contradictions answered neutral
# (15 of session 12's 23 val errors), word for word from the session 13 instruction. HEADER_A is the first paragraph of
# A-v4-section-route; ACCORDING the sentence on "according to ..." claims with the label as a number.
HEADER_A = PROMPTS_A["A-v4-section-route"].split("\n\n", 1)[0]
ACCORDING = ('A claim of the form "according to the text / the committee / the Federal Council, X" is 1 when the text '
             'does not deal with X.')
_ANSWER_A = PROMPTS_A["A-v4-section-route"][PROMPTS_A["A-v4-section-route"].index("First give the numbers"):]

# A1: what the claim says and what the text says on that point, then paragraphs and label.
PROMPTS_A["A-v6-says"] = HEADER_A + """

Work in this order:
1. "claim_says": what the claim asserts, in at most 12 words, in the language of the reference text.
2. "text_says": what the reference text says on exactly that point, in at most 15 words, in its own language. If the text does not deal with that point, write the single word "nothing".
3. "paragraphs": the numbers of the paragraphs that justify your answer, at most three, most relevant first (an empty list if the text says nothing).
4. "label": 1 (neutral) if text_says is "nothing"; 0 (entailment) if the text says the same as the claim; 2 (contradiction) if the text gives a different number, share, date, actor, direction or outcome for the same thing. Missing information is never 2. A different value is never 1.
""" + ACCORDING + """

Answer with one JSON object and nothing else, fields in this order, for example:
{"claim_says": "...", "text_says": "...", "paragraphs": [2, 5], "label": 0}"""

# A2: neutral only when the text does not deal with the point, or deals with it without settling it.
RULE_A_RESIDUAL = """Decide in this order:
1. Does the reference text deal with the point the claim makes? If it says nothing about that point, the label is 1 (neutral). """ + ACCORDING + """
2. If it does deal with that point:
   0 (entailment): the text states the same as the claim, in its own words.
   2 (contradiction): the text states a different number, share, date, actor, direction or outcome for the same thing, or the opposite of the claim.
   1 (neutral) only if the text deals with the subject but does not settle the point either way.
Missing information is never 2. A different value is never 1."""
PROMPTS_A["A-v6-residual"] = HEADER_A + "\n\n" + RULE_A_RESIDUAL + "\n\n" + _ANSWER_A

# A3: A2's rules, then what differs between claim and text, then the label.
PROMPTS_A["A-v6-mismatch"] = HEADER_A + "\n\n" + RULE_A_RESIDUAL + """

First give the paragraphs that justify your answer, at most three, most relevant first. Then "mismatch": what, if anything, differs between the claim and the text on the same point: "none" (the text says the same), "number", "date", "actor", "direction", "negation", "scope", or "not_covered" (the text does not deal with the point). Then the label: none -> 0, not_covered -> 1, anything else -> 2.

Answer with one JSON object and nothing else, for example:
{"paragraphs": [2, 5], "mismatch": "none", "label": 0}"""

# A4: A2's rules, then the claim reversed and which of the two the text states; no label field (Python maps the word).
PROMPTS_A["A-v6-opposite"] = HEADER_A + "\n\n" + RULE_A_RESIDUAL + """

First give the paragraphs that justify your answer, at most three, most relevant first. Then "opposite_claim": the claim with its central point reversed (the other number, the other actor, the opposite direction or outcome), at most 15 words, in the language of the reference text. Then "text_states": "claim" if the text states what the claim says, "opposite" if the text states what the opposite claim says, "neither" if the text deals with neither.

Answer with one JSON object and nothing else, for example:
{"paragraphs": [2, 5], "opposite_claim": "...", "text_states": "claim"}"""

# A5: today's prompt (A-v4-section-route-L1) with the contradiction line first and every label as a word.
_RULE_A_WORDS = """Decide in this order:
1. Does the reference text deal with the subject of the claim at all? If not, the label is "not_covered".
2. If it does:
   "contradicted" only if the reference text states something that cannot be true together with the claim;
   "supported" if the reference text supports the claim;
   otherwise "not_covered" (insufficient information).
Missing information is never "contradicted". A claim of the form "according to the text / the committee / the Federal Council, X" is "not_covered" when the reference text does not deal with X.
""" + L1_SENTENCE.replace("is a contradiction.", 'is "contradicted".')
assert _RULE_A_WORDS.endswith('is "contradicted".')
PROMPTS_A["A-v6-words"] = PROMPTS_A["A-v4-section-route-L1"].replace(_RULE_B + "\n" + L1_SENTENCE, _RULE_A_WORDS).replace(
    "(for label 1, an empty list)", '(for "not_covered", an empty list)').replace(
    '{"paragraphs": [2, 5], "label": 0}', '{"paragraphs": [2, 5], "label": "contradicted"}')
assert "1 (neutral)" not in PROMPTS_A["A-v6-words"] and '"label": "contradicted"}' in PROMPTS_A["A-v6-words"]

_PARAGRAPHS_PROPERTY = ANSWER_SCHEMA_A_PARAGRAPHS["properties"]["paragraphs"]


def _schema(**properties):
    """A strict answer schema: the fields in the order given, all required, nothing else."""
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


MISMATCHES = ["none", "number", "date", "actor", "direction", "negation", "scope", "not_covered"]
# Per routed version of session 13: its answer schema, the field the label is read from, the words Apertus chooses
# from (mapped to 0/1/2; None: the field holds 0, 1 or 2) and the answer budget.
ROUTED_VERSIONS = {
    "A-v6-says": {"schema": _schema(claim_says={"type": "string", "maxLength": 120},
                                    text_says={"type": "string", "maxLength": 150},
                                    paragraphs=_PARAGRAPHS_PROPERTY,
                                    label={"type": "integer", "enum": [0, 1, 2]}),
                  "field": "label", "words": None, "max_tokens": 256},
    "A-v6-residual": {"schema": ANSWER_SCHEMA_A_PARAGRAPHS, "field": "label", "words": None, "max_tokens": 128},
    "A-v6-mismatch": {"schema": _schema(paragraphs=_PARAGRAPHS_PROPERTY,
                                        mismatch={"type": "string", "enum": MISMATCHES},
                                        label={"type": "integer", "enum": [0, 1, 2]}),
                      "field": "label", "words": None, "max_tokens": 128},
    "A-v6-opposite": {"schema": _schema(paragraphs=_PARAGRAPHS_PROPERTY,
                                        opposite_claim={"type": "string", "maxLength": 150},
                                        text_states={"type": "string", "enum": ["claim", "opposite", "neither"]}),
                      "field": "text_states", "words": {"claim": 0, "opposite": 2, "neither": 1}, "max_tokens": 256},
    "A-v6-words": {"schema": _schema(paragraphs=_PARAGRAPHS_PROPERTY,
                                     label={"type": "string", "enum": ["contradicted", "supported", "not_covered"]}),
                   "field": "label", "words": {"supported": 0, "not_covered": 1, "contradicted": 2}, "max_tokens": 128},
}

# A6 (session 13, step 1; on by default since session 15): a second look after a neutral answer that cites paragraphs. The excerpt is
# the cited paragraphs with their neighbours (src/cli.py second_look_a6); Apertus's finding is mapped to the label.
PROMPTS_A["A-v6-second-look"] = """You compare a CLAIM with a short EXCERPT from an official Swiss federal voting booklet (numbered paragraphs; the excerpt and the claim may be in different languages). Use only the excerpt.
"finding": "same" if the excerpt states what the claim says; "different" if the excerpt gives a different number, share, date, actor, direction or outcome for the same thing, or the opposite; "nothing" if the excerpt does not deal with the point the claim makes.

Answer with one JSON object and nothing else:
{"finding": "same"}"""
# A6b (session 15, step 2; off by default, `--second-look-a6-prompt A-v6-second-look-b`): A6's second look with
# "related but not settled" spelled out, so that a passage on the claim's subject that does not state the claim's value
# is "nothing", not "different". Only this prompt differs from A6; excerpt, schema and mapping are A6's.
PROMPTS_A["A-v6-second-look-b"] = """You compare a CLAIM with a short EXCERPT from an official Swiss federal voting booklet (numbered paragraphs; the excerpt and the claim may be in different languages). Use only the excerpt.
"finding": "same" if the excerpt states what the claim says; "different" if the excerpt gives a different number, share, date, actor, direction or outcome FOR THE SAME THING, or states the opposite; "nothing" if the excerpt does not settle the point the claim makes, including when it deals with the same subject but does not state the claim's value or its opposite.
A text that does not state the claim's value is "nothing", never "different".

Answer with one JSON object and nothing else:
{"finding": "same"}"""
SECOND_LOOK_A6_VERSIONS = ("A-v6-second-look", "A-v6-second-look-b")
ANSWER_SCHEMA_A6 = _schema(finding={"type": "string", "enum": ["same", "different", "nothing"]})
FINDING_LABELS = {"same": 0, "different": 2, "nothing": 1}


def build_messages_excerpt(numbered, claim_text, version="A-v6-second-look"):
    """Messages for A6: the EXCERPT as numbered paragraphs ([(number, text)], numbers as first shown), then CLAIM."""
    excerpt = "\n".join(f"[{n}] {text}" for n, text in numbered)
    return [{"role": "system", "content": PROMPTS_A[version]},
            {"role": "user", "content": f"EXCERPT:\n{excerpt}\n\nCLAIM:\n{claim_text}"}]


def parse_word(answer, field, words):
    """(label or None, reason) from the word Apertus chose in `field` (e.g. A6's finding), mapped by `words`."""
    obj = _first_json_object(answer or "")
    if obj is None:
        return None, "no JSON object"
    value = obj.get(field)
    label = words.get(value.strip().lower()) if isinstance(value, str) else None
    if label is None:
        return None, f"invalid {field} {value!r}"
    return label, ""


def parse_routed_answer(answer, version):
    """(label or None, paragraph numbers, reason) of a routed answer. Session 13's versions read the label from
    their own field (mapping the word Apertus chose); every other version as parse_label_and_pages."""
    spec = ROUTED_VERSIONS.get(version)
    if spec is None or spec["words"] is None:
        return parse_label_and_pages(answer, key="paragraphs")
    label, reason = parse_word(answer, spec["field"], spec["words"])
    if label is None:
        return None, [], reason
    return label, _numbers(_first_json_object(answer).get("paragraphs")), ""


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
    if version == "A-v0-closed-book":  # session 9, E2: no booklet text
        user = f"VOTE: {vote}\n\nCLAIM:\n{claim_text}"
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
    return label, _numbers(obj.get(key)), ""


def _numbers(raw_numbers):
    """The page or paragraph numbers of an answer, as ints as given (digit strings accepted), possibly empty."""
    numbers = []
    if isinstance(raw_numbers, list):
        for p in raw_numbers:
            if isinstance(p, bool):
                continue
            if isinstance(p, int):
                numbers.append(p)
            elif isinstance(p, str) and p.strip().isdigit():
                numbers.append(int(p.strip()))
    return numbers


# Robustness experiments (Kaan; off by default, src/strategies.py): prompts that rewrite the claim. They never
# see the booklet; the rewritten claim is then judged with the normal prompts above.
CLAIM_PROMPTS = {}
CLAIM_PROMPTS["negate-claim"] = """You rewrite a CLAIM about a Swiss federal voting booklet into its negation: one claim that is true exactly when the original is false. Keep the language of the claim (German, French or Italian), keep its opening that names a source ("according to the summary", "the Federal Council holds", ...) unchanged, and negate only what is said about the subject. Change as few words as possible.

Answer with one JSON object and nothing else, for example:
{"claim": "Laut der Zusammenfassung zahlt der Bund keine 40 Millionen Franken."}"""
CLAIM_PROMPTS["decompose-claim"] = """You split a CLAIM about a Swiss federal voting booklet into at most four shorter claims that together say exactly what the original says. Each short claim must state one fact, be understandable on its own, keep the language of the claim (German, French or Italian), and repeat the claim's opening that names a source ("according to the summary", "the Federal Council holds", ...). Do not add or drop anything. If the claim states only one fact, return it unchanged as the only item.

Answer with one JSON object and nothing else, for example:
{"claims": ["Laut der Zusammenfassung zahlt der Bund 40 Millionen Franken.", "Laut der Zusammenfassung zahlen die Kantone den Rest."]}"""
CLAIM_SCHEMAS = {
    "negate-claim": {"type": "object", "properties": {"claim": {"type": "string"}}, "required": ["claim"],
                     "additionalProperties": False},
    "decompose-claim": {"type": "object", "properties": {"claims": {"type": "array", "items": {"type": "string"},
                                                                    "minItems": 1, "maxItems": 4}},
                        "required": ["claims"], "additionalProperties": False},
}


def build_messages_claim(version, claim_text):
    return [{"role": "system", "content": CLAIM_PROMPTS[version]}, {"role": "user", "content": f"CLAIM:\n{claim_text}"}]


def parse_claims(answer, key):
    """The rewritten claim(s) from a negate-claim ("claim") or decompose-claim ("claims") answer: a list of
    non-empty strings, or [] when the answer cannot be read."""
    obj = _first_json_object(answer or "")
    value = obj.get(key) if obj else None
    values = value if isinstance(value, list) else [value]
    return [v.strip() for v in values if isinstance(v, str) and v.strip()]


# Session 13, step 2 (all off by default): three task B prompts against unrelated passages answered contradiction (9 of
# session 12's 18 val errors), word for word from the session 13 instruction. B1 names both ballots first; B2 is
# v3-topic-first with its decision block replaced; B4 is v3-topic-first with its answer block replaced.
PROMPTS_B["v7-same-ballot"] = """You check a CLAIM against a REFERENCE TEXT from an official Swiss federal voting booklet. The first line of the reference text names the ballot it is about. The reference text and the claim may be in different languages (German, French or Italian). Use only the reference text, never outside knowledge.

Work in this order:
1. "passage_ballot": the ballot the reference text is about, at most 8 words, in the language of the reference text.
2. "claim_ballot": the ballot the claim is about, at most 8 words, in the language of the reference text.
3. "same_ballot": true only if the claim is about the ballot the reference text is about.
4. "label": 1 (neutral) if same_ballot is false. Otherwise 0 (entailment) if the reference text supports the claim; 2 (contradiction) only if the reference text states something that cannot be true together with the claim; otherwise 1 (neutral: insufficient information). Missing information is never a contradiction. """ + ACCORDING + """

Answer with one JSON object and nothing else, fields in this order:
{"passage_ballot": "...", "claim_ballot": "...", "same_ballot": true, "label": 0}"""

_DECIDE_B = PROMPTS_B["v3-topic-first"][PROMPTS_B["v3-topic-first"].index("Decide in this order:"):
                                        PROMPTS_B["v3-topic-first"].index("\n\nAnswer with one JSON object")]
PROMPTS_B["v7-unrelated"] = PROMPTS_B["v3-topic-first"].replace(_DECIDE_B, """Decide in this order:
1. Is the reference text about the same ballot and the same point as the claim? If it is about another ballot or another subject, or does not deal with the point the claim makes, the label is 1 (unrelated). When unsure whether it deals with the point, the label is 1.
2. Only if it deals with the point: 0 (entailment) if the reference text supports the claim; 2 (contradiction) only if the reference text states something that cannot be true together with the claim.
A text about a different ballot never contradicts the claim, even when the subjects are similar and even when the claim says "according to the text". Missing information is never a contradiction.""")
assert PROMPTS_B["v7-unrelated"] != PROMPTS_B["v3-topic-first"]

PROMPTS_B["v7-claim-first"] = PROMPTS_B["v3-topic-first"].replace(_ANSWER_B, """First "claim_says": what the claim asserts, in at most 12 words, in the language of the reference text. Then the label.

Answer with one JSON object and nothing else, fields in this order:
{"claim_says": "...", "label": 0}""")
assert PROMPTS_B["v7-claim-first"] != PROMPTS_B["v3-topic-first"]

# Session 15, step 3 (off by default): B1 retried with only its format fixed: both ballot fields at most 6 words and
# 40 characters, a 64-token budget (B1's answer ran into its 80-character cap and out of budget in session 13).
PROMPTS_B["v7-same-ballot-f"] = PROMPTS_B["v7-same-ballot"].replace("at most 8 words", "at most 6 words")
assert PROMPTS_B["v7-same-ballot-f"].count("at most 6 words") == 2

# Per session 13 task B version: its answer schema and budget (B2 keeps today's: no schema, 32 tokens). The label is
# read from "label" as today (parse_label).
B_VERSIONS = {
    "v7-same-ballot-f": {"schema": _schema(passage_ballot={"type": "string", "maxLength": 40},
                                           claim_ballot={"type": "string", "maxLength": 40},
                                           same_ballot={"type": "boolean"},
                                           label={"type": "integer", "enum": [0, 1, 2]}), "max_tokens": 64},
    "v7-same-ballot": {"schema": _schema(passage_ballot={"type": "string", "maxLength": 80},
                                         claim_ballot={"type": "string", "maxLength": 80},
                                         same_ballot={"type": "boolean"},
                                         label={"type": "integer", "enum": [0, 1, 2]}), "max_tokens": 160},
    "v7-claim-first": {"schema": _schema(claim_says={"type": "string", "maxLength": 120},
                                         label={"type": "integer", "enum": [0, 1, 2]}), "max_tokens": 128},
}


DEFAULT_PROMPT_B = "v3-topic-first"  # best on dev (session 2, Run A)


# B6 (session 15, step 4; off by default, `--second-look-b6`): after a task B answer 2 (contradiction), one more request
# with only the reference's first line (the ballot's title), the case's vote field and the claim. Apertus's
# "same_ballot" false makes the label 1; true keeps the first answer (Python only decides when to ask).
B6_VERSION = "B6-same-ballot-v1"
B6_QUESTION = 'Is the claim about the ballot named in the title? Answer in JSON: {"same_ballot": true|false}.'
ANSWER_SCHEMA_B6 = _schema(same_ballot={"type": "boolean"})


def build_messages_b6(title, vote, claim_text):
    """B6's one user message: the reference's title, the vote field, the claim, and the question."""
    return [{"role": "user", "content": f"TITLE: {title}\nVOTE: {vote}\nCLAIM: {claim_text}\n\n{B6_QUESTION}"}]


def parse_same_ballot(answer):
    """(True / False / None, reason) from B6's answer: the boolean Apertus gave in "same_ballot"."""
    obj = _first_json_object(answer or "")
    if obj is None:
        return None, "no JSON object"
    value = obj.get("same_ballot")
    if not isinstance(value, bool):
        return None, f"same_ballot is {value!r}"
    return value, ""


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
