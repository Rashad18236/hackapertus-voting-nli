"""Which booklet text task A sends to the model.

MODES:
- "full":           every page (the full-document baseline).
- "vote-section":   only the pages about the ballot named in `vote`.
- "embed-e5-small": only the passages most similar to the claim, found with a
                    local embedding model.

`select` returns the text for the prompt and the pages it was taken from;
evidence is taken only from those pages (src/cli.py).

All three run locally: no Apertus call, no tokens. Apertus alone makes the
entailment decision; this module only chooses what it reads.

## "vote-section" (deterministic, no model)

Voting booklets cover several ballots. Every page of a ballot's part starts
with a running header that names it ("Deuxième objet : loi sur la chasse",
"Erste Vorlage: Bargeld-Initiative", "Primo oggetto: Sublocazione"). The header
is in the booklet's language, like `vote`, so we match the two without caring
which language the claim is in:

1. Title match: keep every page that contains the full vote title (fuzzy, so
   line breaks and hyphenation do not matter).
2. Header match: score the first HEAD_CHARS characters of every page by the
   words (4+ letters) it shares with `vote`, weighting each word by how rare it
   is among the booklet's page headers (a word in every header, such as
   "initiative", counts little). Keep pages scoring at least REL_THRESHOLD of
   the best page *without* the full title: full-title pages share every title
   word and would otherwise set the bar too high for the short running header.
3. Facing page: also keep the page after each kept page (two-page spreads
   often carry the header on one side only).
4. Gap filling: if two kept pages are at most MAX_GAP pages apart, keep the
   pages between them too (pages such as "Arguments of the Federal Council"
   inside the section may not repeat the ballot's name).
5. If nothing matches, send every page.

Measured offline on the 169 dev task A cases that have a gold page: the
selection contains a page matching the gold passage in 98.8 % of them, with
47 % of the booklet's characters on average (docs/decisions.md, session 3).

## "embed-e5-small" (local embedding model)

1. Each page is split into chunks of at most CHUNK_CHARS characters (at
   whitespace). Every chunk keeps its 1-based page number.
2. The claim and all chunks are embedded with intfloat/multilingual-e5-small
   (MIT licence, open weights), a multilingual sentence-embedding model, so a
   German claim can match a French or Italian passage. It runs locally on CPU
   via onnxruntime; the weights are baked into the Docker image (see
   Dockerfile), nothing is downloaded at run time.
3. The TOP_K chunks with the highest cosine similarity to the claim are kept
   and shown to the model in page order, each with a "=== PAGE n ===" marker,
   so the model's page citations still work.

e5 expects "query: " before the search text and "passage: " before each
document text (model card); without them retrieval quality drops.

Chunk embeddings are cached in memory per booklet (keyed by the booklet text's
SHA-256): booklets repeat across cases, and the result depends only on the
text, never on case order. The first case of each booklet pays for embedding it.
"""

import hashlib
import math
import os
import re
import unicodedata
from pathlib import Path

from rapidfuzz import fuzz

from src import parse

MODES = ("full", "vote-section", "embed-e5-small")

# "vote-section"
HEAD_CHARS = 160      # how much of each page counts as its header
REL_THRESHOLD = 0.5   # keep pages whose header score is at least this share of the best
FOLLOW = 1            # also keep this many pages after each kept page
MAX_GAP = 10          # fill gaps of at most this many pages between kept pages
TITLE_CHARS = 70      # the start of the vote title used for the full-title match
TITLE_MIN_RATIO = 90  # fuzzy match score (0-100) for the full-title match

# "embed-e5-small"
CHUNK_CHARS = 1000  # about 250 to 300 tokens, well under e5's 512-token limit
TOP_K = 8
MAX_TOKENS = 512  # e5's maximum input length; longer inputs are truncated
BATCH_SIZE = 32
MODEL_DIR = Path(os.environ.get("EMBED_MODEL_DIR", "/app/models/multilingual-e5-small"))

_WORD = re.compile(r"[^\W\d_]{4,}")


def select(pages, vote, claim_text, mode):
    """Return (prompt_text, shown): the booklet text for the prompt, and {page: full page text}
    for every page that text comes from (the pages evidence may cite)."""
    if mode == "embed-e5-small":
        chunks = select_chunks(pages, claim_text)
        return excerpts_prompt_text(chunks), {n: pages[n] for n, _ in chunks}
    shown = select_pages(pages, vote, mode)
    return parse.booklet_prompt_text(shown), shown


# ---------------------------------------------------------------- "full" and "vote-section"

def _norm(text):
    text = unicodedata.normalize("NFKC", text).replace("­", "")
    text = re.sub(r"(\w) ?-\s*\n\s*(\w)", r"\1\2", text)  # words hyphenated across lines
    return re.sub(r"\s+", " ", text).strip().lower()


def _header(text):
    return _norm(re.sub(r"^\s*\d+\s*", "", text))[:HEAD_CHARS]  # drop a leading page number


def vote_section(pages, vote):
    """Return the sorted page numbers that belong to the ballot named in `vote`."""
    if not pages or not vote.strip():
        return sorted(pages)
    n = len(pages)
    heads = {p: set(_WORD.findall(_header(t))) for p, t in pages.items()}
    doc_freq = {}
    for words in heads.values():
        for w in words:
            doc_freq[w] = doc_freq.get(w, 0) + 1
    title_words = set(_WORD.findall(_norm(vote)))
    weight = {w: math.log((n + 1) / (doc_freq[w] + 1)) for w in title_words if w in doc_freq}
    score = {p: sum(weight.get(w, 0.0) for w in heads[p] & title_words) for p in pages}
    key = _norm(vote)[:TITLE_CHARS]
    title_pages = {p for p, t in pages.items() if fuzz.partial_ratio(key, _norm(t)) >= TITLE_MIN_RATIO}
    # The threshold comes from the running-header pages (pages without the full
    # title): full-title pages share every title word and would set the bar too
    # high for the short name in the running header.
    best = max((s for p, s in score.items() if p not in title_pages), default=0.0) or max(score.values())
    keep = {p for p, s in score.items() if best > 0 and s >= REL_THRESHOLD * best} | title_pages
    for p in list(keep):
        keep.update(q for q in range(p + 1, p + FOLLOW + 1) if q in pages)
    ordered = sorted(keep)
    for a, b in zip(ordered, ordered[1:]):
        if b - a <= MAX_GAP:
            keep.update(q for q in range(a, b) if q in pages)
    return sorted(keep) if keep else sorted(pages)


def select_pages(pages, vote, mode="full"):
    """Return {page number: text} for the pages to send, in page order ("full" or "vote-section")."""
    if mode == "full":
        return dict(sorted(pages.items()))
    if mode == "vote-section":
        return {p: pages[p] for p in vote_section(pages, vote)}
    raise ValueError(f"unknown page selection mode {mode!r}")


# ---------------------------------------------------------------- "embed-e5-small"

def chunk_pages(pages, max_chars=CHUNK_CHARS):
    """Return [(page, text)] in page order; long pages become several chunks with the same page."""
    chunks = []
    for n, text in sorted(pages.items()):
        for piece in parse._split(text.strip(), max_chars):
            chunks.append((n, piece))
    return chunks


class E5Embedder:
    """multilingual-e5-small in ONNX format: tokenize, run the model, mean-pool, L2-normalise."""

    def __init__(self, model_dir=MODEL_DIR):
        # Imported here so the other modes and the tests need neither package loaded.
        import onnxruntime
        from tokenizers import Tokenizer

        self.tokenizer = Tokenizer.from_file(str(Path(model_dir) / "tokenizer.json"))
        self.tokenizer.enable_truncation(max_length=MAX_TOKENS)
        self.tokenizer.enable_padding()
        options = onnxruntime.SessionOptions()
        options.log_severity_level = 3  # errors only
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
            hidden = self.session.run(None, inputs)[0]  # (batch, tokens, 384)
            # Mean pooling over real tokens (padding excluded), as in the model card.
            summed = (hidden * mask[:, :, None]).sum(axis=1)
            mean = summed / mask.sum(axis=1, keepdims=True)
            vectors.append(mean / np.linalg.norm(mean, axis=1, keepdims=True))
        return np.concatenate(vectors)


_embedder = None
_chunk_cache = {}  # booklet text SHA-256 -> (chunks, chunk vectors)


def _get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = E5Embedder()
    return _embedder


def select_chunks(pages, claim_text, embedder=None, top_k=TOP_K):
    """Return the top_k chunks most similar to the claim, as [(page, text)] in page order."""
    embedder = embedder or _get_embedder()
    key = hashlib.sha256(parse.booklet_prompt_text(pages).encode("utf-8")).hexdigest()
    if key not in _chunk_cache:
        chunks = chunk_pages(pages)
        _chunk_cache[key] = (chunks, embedder.embed([f"passage: {text}" for _, text in chunks]))
    chunks, vectors = _chunk_cache[key]
    if not chunks:
        return []
    query = embedder.embed([f"query: {claim_text}"])[0]
    scores = vectors @ query  # cosine similarity, since all vectors have length 1
    best = sorted(range(len(chunks)), key=lambda i: -scores[i])[:top_k]
    return [chunks[i] for i in sorted(best)]  # chunk order = page order


def excerpts_prompt_text(chunks):
    """Selected chunks with a page marker before each, in page order."""
    return "\n\n".join(f"=== PAGE {n} ===\n{text}" for n, text in chunks)
