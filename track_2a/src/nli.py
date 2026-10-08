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

PROMPT_VERSION_B = "v2-label-only"
LABEL_NAMES = {0: "entailment", 1: "neutral", 2: "contradiction"}

SYSTEM_PROMPT_B = """You are a careful fact checker for official Swiss federal voting booklets.

You get a REFERENCE TEXT from a voting booklet and a CLAIM. They may be in different languages (German, French or Italian). The reference text is the only source of truth: do not use outside knowledge, even if you know the claim is true or false in the real world.

Choose exactly one label:
0 = entailment: the reference text supports the claim (states it or clearly implies it).
1 = neutral: the reference text gives insufficient information to decide. A claim that is true in the real world but not covered by the reference text is neutral.
2 = contradiction: the reference text refutes the claim (states something that makes it false).

Answer with one JSON object and nothing else:
{"label": <0, 1 or 2>}"""


def build_messages_b(reference_text, claim_text):
    user = f"REFERENCE TEXT:\n{reference_text}\n\nCLAIM:\n{claim_text}"
    return [
        {"role": "system", "content": SYSTEM_PROMPT_B},
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
