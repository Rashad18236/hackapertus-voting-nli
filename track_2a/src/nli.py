"""Prompt construction and answer parsing for the beginner task.

We ask for a fixed two-line answer instead of JSON: it is easier for a small
model to follow and easier for us to parse and explain.
"""

import logging
import re

LABELS = {"entailment": 0, "neutral": 1, "contradiction": 2}
FALLBACK_LABEL = "neutral"

SYSTEM_PROMPT = """You check claims against an official Swiss voting booklet.
Use only the reference text, never outside knowledge.
The claim and the reference may be in different languages (German, French, Italian).

Decide:
- entailment: the reference text states or clearly implies the claim.
- contradiction: the reference text states something that makes the claim false.
- neutral: the reference text does not settle the claim, even if the claim is true.

Answer in exactly two lines:
LABEL: <entailment, neutral or contradiction>
EVIDENCE: <one sentence copied exactly from the reference text, or NONE if neutral>"""


def build_messages(reference_text, claim_text):
    user = f"REFERENCE TEXT:\n{reference_text}\n\nCLAIM:\n{claim_text}"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def parse_label(answer):
    """Return the label name; fall back to neutral if the answer is unreadable."""
    match = re.search(r"LABEL:\s*(\w+)", answer, re.IGNORECASE)
    if match and match.group(1).lower() in LABELS:
        return match.group(1).lower()
    # The model ignored the format: take the first label word it mentions.
    words = re.findall(r"entailment|neutral|contradiction", answer, re.IGNORECASE)
    if words:
        return words[0].lower()
    logging.warning("Could not read a label from the model answer; using %s", FALLBACK_LABEL)
    return FALLBACK_LABEL


def parse_evidence(answer, reference_text):
    """Return the quoted sentence only if it appears exactly in the reference."""
    match = re.search(r"EVIDENCE:\s*(.+)", answer, re.IGNORECASE)
    if not match:
        return None
    quote = match.group(1).strip().strip("\"'«»“”„")
    if not quote or quote.upper() == "NONE":
        return None
    if quote in reference_text:
        return quote
    logging.info("Model quote is not verbatim in the reference; dropping it")
    return None
