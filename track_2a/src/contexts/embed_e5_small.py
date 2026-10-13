"""Context variant "embed-e5-small": only the passages most similar to the claim.

Built by Kaan on the `embedding` branch; merged with session 3 in PR #5.

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

The embedding model only chooses what Apertus reads; Apertus makes the
entailment decision.

e5 expects "query: " before the search text and "passage: " before each
document text (model card); without them retrieval quality drops.

Chunk embeddings are cached in memory per booklet (keyed by the booklet text's
SHA-256): booklets repeat across cases, and the result depends only on the
text, never on case order. The first case of each booklet pays for embedding it.
"""

import hashlib
import os
import threading
from pathlib import Path

from src import memo, parse, pipeline

NAME = "embed-e5-small"
PROMPT_VERSION = "A-v3-excerpts"

CHUNK_CHARS = 1000  # about 250 to 300 tokens, well under e5's 512-token limit
TOP_K = 8
MAX_TOKENS = 512  # e5's maximum input length; longer inputs are truncated
BATCH_SIZE = 16  # session 8: 32 before; with length-sorted batches, 16 is faster and needs less memory
BATCH_TOKENS = None  # session 11, step 5 (off): if set, a batch also holds at most this many tokens (texts x longest)
MODEL_DIR = Path(os.environ.get("EMBED_MODEL_DIR", "/app/models/multilingual-e5-small"))


def select(pages, vote, claim_text, cross_language=False):
    """Return (prompt_text, shown): the selected chunks, and the full pages they come from
    (evidence is the full text of the pages the model cites). Languages play no role. Session 12: when src/rankers.py's
    ACTIVE names another ranker, the same chunks are ranked by it ("none": BM25 alone, the word overlap)."""
    from src import rankers
    name = rankers.effective(rankers.ACTIVE["name"])
    if name == "e5":
        try:
            chunks = select_chunks(pages, claim_text)
            return excerpts_prompt_text(chunks), {n: pages[n] for n, _ in chunks}
        except Exception as e:  # session 12, step 2: e5 cannot run here; BM25 alone
            rankers.failed("e5-small", e)
            name = "none"
    every = chunk_pages(pages)
    keep = rankers.best_or_without("BM25" if name == "none" else name, [t for _, t in every], claim_text, TOP_K,
                                   without="BM25") if every else []
    chunks = [every[i] for i in keep]
    return excerpts_prompt_text(chunks), {n: pages[n] for n, _ in chunks}


def chunk_pages(pages, max_chars=CHUNK_CHARS):
    """Return [(page, text)] in page order; long pages become several chunks with the same page."""
    chunks = []
    for n, text in sorted(pages.items()):
        for piece in parse._split(text.strip(), max_chars):
            chunks.append((n, piece))
    return chunks


MEMORY_ARENA = True


class E5Embedder:
    """multilingual-e5-small in ONNX format: tokenize, run the model, mean-pool, L2-normalise."""

    _lock = threading.Lock()  # session 10: one embedding at a time, also across threads (onnxruntime uses every core)

    def __init__(self, model_dir=MODEL_DIR, model_file="model.onnx"):
        # Imported here so the other variants and the tests need neither package loaded.
        from src import deferral, timing
        deferral.check()  # session 11, step 4: in a lane's first pass the model is not loaded
        with timing.phase("e5_load"):
            self._load(model_dir, model_file)

    def _load(self, model_dir, model_file):
        import onnxruntime
        from tokenizers import Tokenizer

        self.tokenizer = Tokenizer.from_file(str(Path(model_dir) / "tokenizer.json"))
        self.tokenizer.enable_truncation(max_length=MAX_TOKENS)
        self.tokenizer.enable_padding()
        options = onnxruntime.SessionOptions()
        options.log_severity_level = 3  # errors only
        # Session 10: as many threads as the container may use. By default onnxruntime starts one per core of the
        # machine, which under a CPU limit (docker run --cpus 2 on 4 cores) is throttled: 2 threads embedded 124
        # paragraphs in 9.5-10.1 s against 11.3-12.5 s. The vectors are the same for 1, 2 and 4 threads.
        options.intra_op_num_threads = pipeline.embedding_threads()  # session 11: the lanes' share with SHARE_CPUS
        # Session 11, step 5 (off by default): onnxruntime's memory arena keeps the largest batch's buffers for the
        # rest of the run; without it they are freed after each batch (the same arithmetic, so the same vectors).
        options.enable_cpu_mem_arena = MEMORY_ARENA
        self.session = onnxruntime.InferenceSession(str(Path(model_dir) / model_file), options,
                                                    providers=["CPUExecutionProvider"])
        self.input_names = {i.name for i in self.session.get_inputs()}

    def embed(self, texts):
        """Return an array (len(texts), 384) of unit-length vectors, in the order of texts.

        Each batch is padded to its longest text, so the texts are batched by length (sorted by number of
        characters) and the vectors put back in the texts' order afterwards. Session 8: a long law part, which
        mixes clause lines of a few words with paragraphs of 1,000 characters, embeds 2 to 3 times faster; the
        vectors are the same (padding is masked out)."""
        import numpy as np

        from src import deferral, timing
        deferral.check()  # session 11, step 4: in a lane's first pass nothing is embedded
        with self._lock, timing.phase("embed"):
            return self._embed(np, texts)

    def _batches(self, texts, order):
        """The texts' indices in batches, in length order: BATCH_SIZE texts each, as since session 8; with
        BATCH_TOKENS set (session 11, step 5), a batch also stops before its texts times its longest text's tokens
        would exceed BATCH_TOKENS (a batch is padded to its longest text, so this bounds its memory)."""
        if BATCH_TOKENS is None:
            return [order[start:start + BATCH_SIZE] for start in range(0, len(order), BATCH_SIZE)]
        encoded = self.tokenizer.encode_batch([texts[i] for i in order])  # padded: the real length is the mask's sum
        lengths = {i: sum(e.attention_mask) for i, e in zip(order, encoded)}
        batches, current, longest = [], [], 0
        for i in order:
            longer = max(longest, lengths[i])
            if current and (len(current) == BATCH_SIZE or (len(current) + 1) * longer > BATCH_TOKENS):
                batches.append(current)
                current, longer = [], lengths[i]
            current.append(i)
            longest = longer
        if current:
            batches.append(current)
        return batches

    def _embed(self, np, texts):
        order = sorted(range(len(texts)), key=lambda i: len(texts[i]))
        vectors = []
        for batch in self._batches(texts, order):
            encoded = self.tokenizer.encode_batch([texts[i] for i in batch])
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
        by_length = np.concatenate(vectors)
        result = np.empty_like(by_length)
        result[order] = by_length  # row k of by_length belongs to texts[order[k]]
        return result


_embedders = {}    # session 10: the one E5Embedder of the run, shared with src/contexts/retrieval.py
_chunk_cache = {}  # booklet text SHA-256 -> (chunks, chunk vectors)


def _get_embedder():
    """The run's E5Embedder, loaded on first use (once, also when several threads ask at the same time)."""
    return memo.once(_embedders, MODEL_DIR, E5Embedder)


QUANTISED_FILE = "model_qint8_avx512_vnni.onnx"  # session 11, step 6: the 8-bit export in the model's own repository


def _get_quantised_embedder():
    """Session 11, step 6 (task B selector Q, off by default): the same model quantised to 8-bit integers, from the
    model's own repository at the same commit (MIT). Loaded on first use."""
    return memo.once(_embedders, (MODEL_DIR, QUANTISED_FILE), lambda: E5Embedder(MODEL_DIR, QUANTISED_FILE))


def chunk_scores(pages, claim_text, embedder=None):
    """(chunks, scores): every chunk of the pages as [(page, text)] in page order, and its cosine similarity to
    the claim. Shared by select_chunks and the hybrid variants (src/contexts/bm25.py)."""
    embedder = embedder or _get_embedder()
    key = hashlib.sha256(parse.booklet_prompt_text(pages).encode("utf-8")).hexdigest()

    def embed_booklet():
        chunks = chunk_pages(pages)
        return chunks, embedder.embed([f"passage: {text}" for _, text in chunks])
    chunks, vectors = memo.once(_chunk_cache, key, embed_booklet)
    if not chunks:
        return [], []
    query = embedder.embed([f"query: {claim_text}"])[0]
    return chunks, vectors @ query  # cosine similarity, since all vectors have length 1


def select_chunks(pages, claim_text, embedder=None, top_k=TOP_K):
    """Return the top_k chunks most similar to the claim, as [(page, text)] in page order."""
    chunks, scores = chunk_scores(pages, claim_text, embedder)
    if not chunks:
        return []
    best = sorted(range(len(chunks)), key=lambda i: -scores[i])[:top_k]
    return [chunks[i] for i in sorted(best)]  # chunk order = page order


def excerpts_prompt_text(chunks):
    """Selected chunks with a page marker before each, in page order."""
    return "\n\n".join(f"=== PAGE {n} ===\n{text}" for n, text in chunks)
