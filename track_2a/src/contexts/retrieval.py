"""Shared code for the embedding variants added in session 4 (not a variant itself).

Variants built on this module: vote-section-embed-e5-small, embed-granite-97m-r2,
vote-section-embed-granite-97m-r2 and named settings of them (src/context.py).
The older embed-e5-small keeps its own code (src/contexts/embed_e5_small.py),
so its behaviour does not change.

How a selection works:

1. Candidate pages: the whole booklet (scope "booklet") or the vote's section
   (scope "section", src/contexts/vote_section.py).
2. Cross-language rule, used when the claim's language differs from the
   booklet's: "same" (nothing changes), "double" (twice as many chunks), or
   "section" (send the whole vote section instead of chunks).
3. Each candidate page is split into chunks of at most CHUNK_CHARS characters
   (as in embed-e5-small) and embedded lazily: a page is embedded the first
   time a selection needs it and cached by its text's SHA-256. Each page is
   embedded on its own, so the vectors, and therefore the selection, never
   depend on which cases ran before.
4. The top k chunks by cosine similarity to the claim are kept; with
   neighbours n, also the n chunks before and after each kept chunk (in page
   order, among the candidate chunks). They are sent in page order with
   "=== PAGE n ===" markers.

Models (both run locally on CPU with onnxruntime; Apertus alone decides the label):

- "e5-small": intfloat/multilingual-e5-small, mean pooling, "query: " and
  "passage: " prefixes (its model card); the code of embed-e5-small.
- "granite-97m-r2": ibm-granite/granite-embedding-97m-multilingual-r2
  (Apache-2.0, commit 835ad14), ONNX export from the model's own repository,
  CLS pooling and no prefixes (its model card).
"""

import hashlib
import os
import time
from pathlib import Path

from src import parse
from src.contexts import embed_e5_small, vote_section

CHUNK_CHARS = 1000  # as embed-e5-small
MAX_TOKENS = 512    # chunks of 1,000 characters stay well below this
BATCH_SIZE = 32
GRANITE_DIR = Path(os.environ.get("GRANITE_MODEL_DIR", "/app/models/granite-embedding-97m-multilingual-r2"))
CROSS_RULES = ("same", "double", "section")


class GraniteEmbedder:
    """granite-embedding-97m-multilingual-r2 in ONNX format: tokenize, run, CLS pooling, L2-normalise."""

    def __init__(self, model_dir=GRANITE_DIR):
        import onnxruntime
        from tokenizers import Tokenizer

        self.tokenizer = Tokenizer.from_file(str(Path(model_dir) / "tokenizer.json"))
        self.tokenizer.enable_truncation(max_length=MAX_TOKENS)
        self.tokenizer.enable_padding()
        options = onnxruntime.SessionOptions()
        options.log_severity_level = 3
        self.session = onnxruntime.InferenceSession(str(Path(model_dir) / "model.onnx"), options,
                                                    providers=["CPUExecutionProvider"])
        self.input_names = {i.name for i in self.session.get_inputs()}

    def embed(self, texts):
        """Return an array (len(texts), 384) of unit-length vectors."""
        import numpy as np

        vectors = []
        for start in range(0, len(texts), BATCH_SIZE):
            encoded = self.tokenizer.encode_batch(texts[start:start + BATCH_SIZE])
            ids = np.array([e.ids for e in encoded], dtype=np.int64)
            mask = np.array([e.attention_mask for e in encoded], dtype=np.int64)
            inputs = {"input_ids": ids, "attention_mask": mask}
            if "token_type_ids" in self.input_names:
                inputs["token_type_ids"] = np.zeros_like(ids)
            cls = self.session.run(None, inputs)[0][:, 0]  # CLS pooling: the first token's vector
            vectors.append(cls / np.linalg.norm(cls, axis=1, keepdims=True))
        return np.concatenate(vectors)


# name -> (embedder factory, query prefix, passage prefix)
MODELS = {
    "e5-small": (lambda: embed_e5_small.E5Embedder(), "query: ", "passage: "),
    "granite-97m-r2": (lambda: GraniteEmbedder(), "", ""),
}

_embedders = {}
_page_cache = {}   # (model, SHA-256 of page text) -> (chunk texts, vectors, CPU seconds)
_query_cache = {}  # (model, claim text) -> vector


def embedder(model):
    if model not in _embedders:
        _embedders[model] = MODELS[model][0]()
    return _embedders[model]


def page_chunks(model, text):
    """(chunk texts, vectors, CPU seconds to embed) for one page, embedded on first use."""
    key = (model, hashlib.sha256(text.encode("utf-8")).hexdigest())
    if key not in _page_cache:
        chunks = parse._split(text.strip(), CHUNK_CHARS)
        vectors, cpu = None, 0.0
        if chunks:
            prefix = MODELS[model][2]
            start = time.process_time()
            vectors = embedder(model).embed([prefix + c for c in chunks])
            cpu = time.process_time() - start
        _page_cache[key] = (chunks, vectors, cpu)
    return _page_cache[key]


def query_vector(model, claim_text):
    key = (model, claim_text)
    if key not in _query_cache:
        _query_cache[key] = embedder(model).embed([MODELS[model][1] + claim_text])[0]
    return _query_cache[key]


def rank(vectors, query, k, neighbours):
    """Indices of the top k rows by cosine similarity, plus `neighbours` rows on each side, sorted."""
    import numpy as np

    if vectors is None or len(vectors) == 0:
        return []
    scores = np.asarray(vectors) @ query
    best = sorted(range(len(scores)), key=lambda i: -scores[i])[:k]
    keep = set(best)
    for i in best:
        keep.update(j for j in range(i - neighbours, i + neighbours + 1) if 0 <= j < len(scores))
    return sorted(keep)


def select(pages, vote, claim_text, *, model, scope, k, neighbours=0, cross_rule="same", cross_language=False):
    """Return (prompt_text, shown) like every context variant (see src/context.py)."""
    import numpy as np

    if cross_rule not in CROSS_RULES:
        raise ValueError(f"unknown cross-language rule {cross_rule!r}")
    candidates = vote_section.section_pages(pages, vote) if scope == "section" else sorted(pages)
    if cross_language and cross_rule == "section":
        section = {p: pages[p] for p in vote_section.section_pages(pages, vote)}
        return parse.booklet_prompt_text(section), section
    if cross_language and cross_rule == "double":
        k = 2 * k
    chunks, vectors = [], []
    for p in candidates:
        texts, vecs, _ = page_chunks(model, pages[p])
        chunks += [(p, t) for t in texts]
        if vecs is not None:
            vectors.append(vecs)
    if not chunks:
        return "", {}
    keep = rank(np.concatenate(vectors), query_vector(model, claim_text), k, neighbours)
    selected = [chunks[i] for i in keep]
    return embed_e5_small.excerpts_prompt_text(selected), {p: pages[p] for p, _ in selected}


def rank_pages(shown, claim_text, model="e5-small"):
    """Page numbers of `shown`, most similar to the claim first (a page's score is its best chunk's)."""
    query = query_vector(model, claim_text)
    best = {}
    for p, text in shown.items():
        _, vectors, _ = page_chunks(model, text)
        if vectors is not None:
            best[p] = float((vectors @ query).max())
    return sorted(best, key=lambda p: (-best[p], p))
