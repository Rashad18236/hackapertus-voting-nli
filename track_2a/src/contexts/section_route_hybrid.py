"""Context variant "section-route-hybrid": section-route exactly as it is, but a case it cannot route runs as
"vote-section-hybrid" instead of "embed-e5-small" (robustness experiments, Kaan).

Everything a routed case uses (route, PART_LINES, display, evidence_items, most_similar, similarities and the
prompt) is section-route's own, so routed cases send exactly the same requests; only FALLBACK differs.
"""

from src.contexts import bm25, section_route
from src.contexts.section_route import (PART_LINES, PROMPT_VERSION, display, evidence_items,  # noqa: F401
                                        most_similar, route, similarities, split_in_half)

NAME = "section-route-hybrid"
FALLBACK = "vote-section-hybrid"


def select(pages, vote, claim_text, cross_language=False):
    routed = route(pages, vote, claim_text)
    if routed is None:
        return bm25.as_selection(pages, bm25.hybrid_chunks(bm25.section_only(pages, vote), claim_text))
    return section_route.select(pages, vote, claim_text, cross_language)
