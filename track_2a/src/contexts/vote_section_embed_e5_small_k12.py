"""Context variant "vote-section-embed-e5-small-k12": as vote-section-embed-e5-small, with the top 12 chunks.

Built in session 4 (Rashad, with Claude): the setting chosen by the offline search grid
(docs/runs/2026-10-08_rashad_search-grid_devA201/).
Shared selection code: src/contexts/retrieval.py. Fixed settings of this name
(a different setting is a different variant name): multilingual-e5-small, scope
"section", top 12 chunks, 0 neighbours, cross-language rule "same".
"""

from src.contexts import retrieval

NAME = "vote-section-embed-e5-small-k12"
PROMPT_VERSION = "A-v3-excerpts"
SETTINGS = dict(model="e5-small", scope="section", k=12, neighbours=0, cross_rule="same")


def select(pages, vote, claim_text, cross_language=False):
    """Return (prompt_text, shown): the selected chunks, and the full pages they come from."""
    return retrieval.select(pages, vote, claim_text, cross_language=cross_language, **SETTINGS)
