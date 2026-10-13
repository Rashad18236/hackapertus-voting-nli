"""Context variant "bm25-mt": BM25 with the claim machine-translated into the booklet's language first
(robustness experiments, Kaan). See src/contexts/bm25.py; translation: src/translate.py."""

from src.contexts import bm25, embed_e5_small

NAME = "bm25-mt"
PROMPT_VERSION = "A-v3-excerpts"


def select(pages, vote, claim_text, cross_language=False):
    chunks = embed_e5_small.chunk_pages(pages)
    query = bm25.translated_claim(pages, claim_text)
    return bm25.as_selection(pages, bm25.top(chunks, bm25.bm25_scores(chunks, query)) if chunks else [])
