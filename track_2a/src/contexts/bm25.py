"""Context variant "bm25": the 8 chunks with the best BM25 keyword score for the claim (robustness experiments,
Kaan). Also the shared code of bm25-mt, hybrid, vote-section-hybrid and section-route-hybrid.

Why BM25: embeddings match meaning; BM25 matches the exact words, numbers and names of the claim ("2 Milliarden",
"Art. 12"), which an embedding can blur. Its weakness is language: a German claim shares few words with a French
booklet, so bm25-mt first translates the claim into the booklet's language (src/translate.py), and hybrid
combines both rankings.

Chunks are embed-e5-small's (src/contexts/embed_e5_small.py: pages cut into pieces of at most 1,000 characters,
each keeping its 1-based page), so the variants differ only in how they rank the same chunks, and the prompt is
the same (A-v3-excerpts, "=== PAGE n ===" excerpts in page order).

BM25 (Okapi; k1 = 1.5, b = 0.75): a chunk's score is the sum over the claim's words of
idf(word) * tf * (k1 + 1) / (tf + k1 * (1 - b + b * length / mean length)), with idf = ln(1 + (N - df + 0.5) /
(df + 0.5)) over the booklet's chunks. Words: letters and digits, lower case, at least two characters, cut to their
first STEM characters, a crude stemmer that lets "Initiative" match "Initiativen" and "initiatives" without a
language-specific library. Pure Python; no new dependency.

Hybrid ranking: reciprocal-rank fusion, score = 1 / (RRF_K + rank by e5) + 1 / (RRF_K + rank by BM25), with
RRF_K = 60 (the usual constant); it needs no score calibration between the two methods.
"""

import hashlib
import math
import re
from collections import Counter

from src import langid, translate
from src.contexts import embed_e5_small, vote_section

NAME = "bm25"
PROMPT_VERSION = "A-v3-excerpts"
TOP_K = 8
K1, B = 1.5, 0.75
STEM = 7
RRF_K = 60
_WORD = re.compile(r"[^\W_]{2,}")
_index_cache = {}  # SHA-256 of the chunks -> (token counts per chunk, document frequencies, mean length)


def tokens(text):
    return [w[:STEM] for w in _WORD.findall(text.lower())]


def _index(chunks):
    key = hashlib.sha256("\x00".join(t for _, t in chunks).encode("utf-8")).hexdigest()
    if key not in _index_cache:
        counts = [Counter(tokens(t)) for _, t in chunks]
        df = Counter(w for c in counts for w in c)
        mean = sum(sum(c.values()) for c in counts) / max(1, len(counts))
        _index_cache[key] = (counts, df, mean or 1.0)
    return _index_cache[key]


def bm25_scores(chunks, query):
    """BM25 score of every chunk ([(page, text)]) for the query text, in the chunks' order."""
    counts, df, mean = _index(chunks)
    n = len(chunks)
    words = set(tokens(query))
    idf = {w: math.log(1 + (n - df[w] + 0.5) / (df[w] + 0.5)) for w in words if df[w]}
    scores = []
    for c in counts:
        length = sum(c.values())
        scores.append(sum(idf[w] * c[w] * (K1 + 1) / (c[w] + K1 * (1 - B + B * length / mean))
                          for w in idf if c[w]))
    return scores


def ranks(scores):
    """Rank (1 = best) of each position for a list of scores; ties keep the earlier position first."""
    order = sorted(range(len(scores)), key=lambda i: -scores[i])
    out = [0] * len(scores)
    for rank, i in enumerate(order, start=1):
        out[i] = rank
    return out


def top(chunks, scores, top_k=TOP_K):
    """The top_k chunks by score, in page order."""
    best = sorted(range(len(chunks)), key=lambda i: -scores[i])[:top_k]
    return [chunks[i] for i in sorted(best)]


def booklet_language(pages):
    """The booklet's language, from its text (the variants' interface does not pass the request's field)."""
    return langid.detect(" ".join(pages[p] for p in sorted(pages)[:8]))


def translated_claim(pages, claim_text):
    """The claim in the booklet's language (local MT); the claim unchanged when it already is, or when
    translation is not available."""
    src, tgt = langid.detect(claim_text), booklet_language(pages)
    try:
        return translate.translate([claim_text], src, tgt)[0]
    except translate.TranslationError:
        return claim_text


def hybrid_chunks(pages, claim_text, top_k=TOP_K):
    """The top_k chunks by reciprocal-rank fusion of e5 and BM25 on the translated claim, in page order."""
    chunks, e5 = embed_e5_small.chunk_scores(pages, claim_text)
    if not chunks:
        return []
    bm = bm25_scores(chunks, translated_claim(pages, claim_text))
    fused = [1 / (RRF_K + a) + 1 / (RRF_K + b) for a, b in zip(ranks(list(e5)), ranks(bm))]
    return top(chunks, fused, top_k)


def as_selection(pages, chunks):
    """(prompt_text, shown) in the registry's format (src/context.py), as embed-e5-small builds it."""
    return embed_e5_small.excerpts_prompt_text(chunks), {n: pages[n] for n, _ in chunks}


def section_only(pages, vote):
    """The vote's pages (src/contexts/vote_section.py), or all pages when the section is not found."""
    return {p: pages[p] for p in vote_section.section_pages(pages, vote)} or pages


def select(pages, vote, claim_text, cross_language=False):
    chunks = embed_e5_small.chunk_pages(pages)
    return as_selection(pages, top(chunks, bm25_scores(chunks, claim_text)) if chunks else [])

