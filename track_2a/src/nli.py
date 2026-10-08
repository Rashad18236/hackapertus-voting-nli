"""Prompt construction and answer parsing for the beginner task.

The prompt is in English; claims and references are passed through untouched,
never translated. The model answers with a JSON object
{"label": 0|1|2, "evidence": "<verbatim quote or empty>"}.

If the answer cannot be parsed, we record a parse failure and do NOT guess a
label: a guess would hide prompt problems behind lucky hits.
"""

import json
import re

PROMPT_VERSION = "v1-json"
LABEL_NAMES = {0: "entailment", 1: "neutral", 2: "contradiction"}

SYSTEM_PROMPT = """You are a careful fact checker for official Swiss federal voting booklets.

You get a REFERENCE TEXT from a voting booklet and a CLAIM. They may be in different languages (German, French or Italian). The reference text is the only source of truth: do not use outside knowledge, even if you know the claim is true or false in the real world.

Choose exactly one label:
0 = entailment: the reference text states the claim or clearly implies it.
1 = neutral: the reference text does not say whether the claim is true or false. A claim that is true in the real world but not covered by the reference text is neutral.
2 = contradiction: the reference text states something that makes the claim false.

Answer with one JSON object and nothing else:
{"label": <0, 1 or 2>, "evidence": "<the shortest passage from the reference text that justifies the label, copied character for character in its original language; empty string if the label is 1>"}"""


def build_messages(reference_text, claim_text):
    user = f"REFERENCE TEXT:\n{reference_text}\n\nCLAIM:\n{claim_text}"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
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


def find_verbatim(quote, reference_text):
    """Return the passage of reference_text that the quote points to, or None.

    An exact substring is returned as is. Otherwise we allow differences in
    whitespace (the model often turns line breaks into spaces) and in letter
    case (it often capitalises the first word of a quote taken from mid-
    sentence). Either way we return the reference's own characters, so the
    result is always verbatim. Any other change means the quote is dropped.
    """
    quote = quote.strip()
    if not quote:
        return None
    if quote in reference_text:
        return quote
    pattern = r"\s+".join(re.escape(w) for w in quote.split())
    match = re.search(pattern, reference_text) or re.search(pattern, reference_text, re.IGNORECASE)
    return match.group(0) if match else None


def parse_answer(answer, reference_text):
    """Parse a model answer.

    Returns a dict with keys label (0/1/2 or None), evidence (verbatim text or
    None), parse_failure (bool), reason (str, why parsing failed or why the
    evidence was dropped; empty if all went well).
    """
    obj = _first_json_object(answer)
    if obj is None:
        return {"label": None, "evidence": None, "parse_failure": True, "reason": "no JSON object"}
    label = _read_label(obj.get("label"))
    if label is None:
        return {"label": None, "evidence": None, "parse_failure": True,
                "reason": f"invalid label {obj.get('label')!r}"}
    raw_evidence = obj.get("evidence")
    if label == 1 or not isinstance(raw_evidence, str) or not raw_evidence.strip():
        return {"label": label, "evidence": None, "parse_failure": False,
                "reason": "" if label == 1 else "no evidence given"}
    evidence = find_verbatim(raw_evidence, reference_text)
    return {"label": label, "evidence": evidence, "parse_failure": False,
            "reason": "" if evidence else "evidence not verbatim"}
