"""Context variant "hybrid": the whole booklet's chunks ranked by reciprocal-rank fusion of e5 (meaning) and
BM25 on the translated claim (exact words), top 8 (robustness experiments, Kaan). See src/contexts/bm25.py."""

from src.contexts import bm25

NAME = "hybrid"
PROMPT_VERSION = "A-v3-excerpts"


def select(pages, vote, claim_text, cross_language=False):
    return bm25.as_selection(pages, bm25.hybrid_chunks(pages, claim_text))
