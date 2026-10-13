"""Context variant "vote-section-hybrid": "hybrid" on the pages of the vote named in `vote` only
(src/contexts/vote_section.py; all pages when the section is not found). Robustness experiments, Kaan."""

from src.contexts import bm25

NAME = "vote-section-hybrid"
PROMPT_VERSION = "A-v3-excerpts"


def select(pages, vote, claim_text, cross_language=False):
    return bm25.as_selection(pages, bm25.hybrid_chunks(bm25.section_only(pages, vote), claim_text))
