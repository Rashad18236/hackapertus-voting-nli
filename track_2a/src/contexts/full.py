"""Context variant "full": every page of the booklet (the full-document baseline).

Built in session 2 (Rashad, with Claude).
"""

from src import parse

NAME = "full"
PROMPT_VERSION = "A-v3-fulldoc"


def select(pages, vote, claim_text):
    """Return (prompt_text, shown): the whole booklet, and every page."""
    shown = dict(sorted(pages.items()))
    return parse.booklet_prompt_text(shown), shown
