"""Context selection for task A: send the model only the booklet passages most similar to the claim.

How it works:
1. Each page is split into chunks of at most CHUNK_CHARS characters (at
   whitespace). Every chunk keeps its 1-based page number.
2. The claim and all chunks are embedded with intfloat/multilingual-e5-small
   (MIT licence), a multilingual sentence-embedding model, so a German claim can
   match a French or Italian passage. It runs locally on CPU via onnxruntime;
   the weights are baked into the Docker image (see Dockerfile).
3. The TOP_K chunks with the highest cosine similarity to the claim are kept
   and shown to the model in page order, with the same "=== PAGE n ===" markers
   as the full document, so the model's page citations still work.

e5 expects "query: " before the search text and "passage: " before each
document text (model card); without them retrieval quality drops.

Chunk embeddings are cached in memory per booklet (keyed by the booklet text's
SHA-256): booklets repeat across cases, and the result depends only on the
text, never on case order. The first case of each booklet pays for embedding it.
"""

import hashlib
import os
from pathlib import Path

from src import parse

CHUNK_CHARS = 1000  # about 250 to 300 tokens, well under e5's 512-token limit
TOP_K = 8
MAX_TOKENS = 512  # e5's maximum input length; longer inputs are truncated
BATCH_SIZE = 32
MODEL_DIR = Path(os.environ.get("EMBED_MODEL_DIR", "/app/models/multilingual-e5-small"))


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
        # Imported here so the full-document path and the tests need neither package loaded.
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
