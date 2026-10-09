"""Context variant "closed-book": no booklet text at all, only the claim and the vote's name.

Session 9, phase E2 (information only; never a default). It measures how much of the task the model answers
from what it already knows. The official reference point is always the supplied source, so this variant is not
a solution: it gives no evidence and is not used by the pipeline's defaults.
"""

NAME = "closed-book"
PROMPT_VERSION = "A-v0-closed-book"


def select(pages, vote, claim_text, cross_language=False):
    """Return (prompt_text, shown): nothing is shown."""
    return "", {}
