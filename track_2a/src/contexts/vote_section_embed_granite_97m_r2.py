"""Context variant "vote-section-embed-granite-97m-r2": only the Granite chunks most similar to the claim, from the vote's section.

Built in session 4 (Rashad, with Claude).
Shared selection code: src/contexts/retrieval.py. Fixed settings of this name
(a different setting is a different variant name): granite-embedding-97m-multilingual-r2, scope
"section", top 8 chunks, 0 neighbours, cross-language rule "same".
"""

from src.contexts import retrieval

NAME = "vote-section-embed-granite-97m-r2"
PROMPT_VERSION = "A-v3-excerpts"
SETTINGS = dict(model="granite-97m-r2", scope="section", k=8, neighbours=0, cross_rule="same")


def select(pages, vote, claim_text, cross_language=False):
    """Return (prompt_text, shown): the selected chunks, and the full pages they come from."""
    return retrieval.select(pages, vote, claim_text, cross_language=cross_language, **SETTINGS)
