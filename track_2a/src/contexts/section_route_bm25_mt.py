"""Context variant "section-route-bm25-mt": section-route exactly as it is, but a case it cannot route runs as
"bm25-mt" instead of "embed-e5-small" (robustness experiments, Kaan).

Why: with routing off, bm25-mt answered 289 of 300 dev task A cases right against embed-e5-small's 270
(docs/runs/2026-10-12_kaan_retrievers_devA300). Routed cases send exactly the same requests as section-route;
only FALLBACK differs (see src/contexts/section_route_hybrid.py for the same pattern).
"""

from src.contexts import bm25_mt, section_route
from src.contexts.section_route import (PART_LINES, PROMPT_VERSION, display, evidence_items,  # noqa: F401
                                        most_similar, route, similarities, split_in_half)

NAME = "section-route-bm25-mt"
FALLBACK = "bm25-mt"


def select(pages, vote, claim_text, cross_language=False):
    if route(pages, vote, claim_text) is None:
        return bm25_mt.select(pages, vote, claim_text, cross_language)
    return section_route.select(pages, vote, claim_text, cross_language)
