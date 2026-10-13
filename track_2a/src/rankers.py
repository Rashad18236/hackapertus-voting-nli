"""Which local ranker chooses what Apertus reads (session 12, steps 1 and 2).

Three places in the pipeline keep only some of a text's pieces, the ones most similar to the claim:

- a routed part longer than section-route's MAX_CHARS: its TOP_K (8) paragraphs (src/contexts/section_route.py);
- the fallback when routing fails: the 8 chunks of the booklet (src/contexts/embed_e5_small.py, the "embed"
  fallback);
- a task B reference over 3,000 characters: its first line and 4 paragraphs (src/taskb_context.py, cut4-r).

ACTIVE["name"] says which ranker does this; src/cli.py sets it from Settings.ranker before each case, and the
memory guard (step 2) sets it to "none" when no embedding model can run. "e5" is today's code, unchanged.

Rankers:

- "e5"      multilingual-e5-small (today's default; onnxruntime);
- "S"       model S (src/static_embed.py, a static table: tokens' vectors averaged; numpy only);
- "BM25"    Kaan's BM25 keyword score (src/contexts/bm25.py), on the claim as it is; pure Python;
- "S+BM25", "e5+BM25": reciprocal-rank fusion of the two orders, 1 / (60 + rank) summed;
- "none"    no ranking model (step 2's guard): a cut part keeps its first 8 paragraphs; the fallback ranks the
            booklet's chunks by BM25 alone (word overlap); a long task B reference is sent whole (src/cli.py).

Step 2, the memory guard: no task may die for lack of memory or of a model file. run_guard() is asked once per run
(src/cli.py): when the container's memory limit is below what the ranker's model needs (MIN_MEMORY), or its files are
missing, the run uses "none". Where a model is used, an exception while loading or running it (MemoryError
included) is caught (failed()), and that process goes on without it from then on. Each case that went on without its
model says so in its raw answer ("ranker_guard"), and the run log counts them.

Only the choice of paragraphs changes; Apertus alone decides the label.
"""

import hashlib
import logging
from pathlib import Path

from src import memo

log = logging.getLogger(__name__)
GIB = 1 << 30
# Session 12, step 2: the smallest container memory limit (docker run --memory) at which a run with the model answered
# every case of the step 2 grid (with one lane below pipeline.MEMORY_FOR_TWO_LANES); below it the run uses "none".
MIN_MEMORY = {"e5-small": 3 * GIB // 2, "static-s": GIB // 2}
CASE = {"guard": None}  # this process's current case: why it went on without its model (src/cli.py resets it)
_unusable = {}  # model -> why it could not be loaded in this process

NAMES = ("e5", "S", "BM25", "S+BM25", "e5+BM25", "none")
MODEL = {"e5": "e5-small", "S": "static-s"}
ACTIVE = {"name": "e5"}

_vectors = {}  # (model, SHA-256 of the texts) -> vectors


def uses_model(name):
    """The embedding model a ranker needs ("e5-small", "static-s"), or None."""
    return MODEL.get(name.split("+")[0])


def model_scores(model, texts, claim_text):
    """Cosine similarity of the claim to each text, with the model's own prefixes (src/contexts/retrieval.py)."""
    from src.contexts import retrieval

    _, query_prefix, passage_prefix = retrieval.MODELS[model]
    key = (model, hashlib.sha256("\n\n".join(texts).encode("utf-8")).hexdigest())
    vectors = memo.once(_vectors, key, lambda: retrieval.embedder(model).embed([passage_prefix + t for t in texts]))
    return list(vectors @ retrieval.query_vector(model, claim_text))


def bm25_scores(texts, claim_text):
    from src.contexts import bm25
    return bm25.bm25_scores([(0, t) for t in texts], claim_text)


def fused(first, second):
    from src.contexts import bm25
    return [1 / (bm25.RRF_K + a) + 1 / (bm25.RRF_K + b) for a, b in zip(bm25.ranks(first), bm25.ranks(second))]


def scores(name, texts, claim_text):
    """One score per text (higher = more similar) for ranker `name`."""
    if name == "none":
        return [-i for i in range(len(texts))]  # keeps the first ones
    if name == "BM25":
        return bm25_scores(texts, claim_text)
    if "+" in name:
        return fused(model_scores(MODEL[name.split("+")[0]], texts, claim_text), bm25_scores(texts, claim_text))
    return model_scores(MODEL[name], texts, claim_text)


def best(name, texts, claim_text, top_k):
    """Indices of the top_k texts for ranker `name`, in their original order (ties: the earlier text first)."""
    values = scores(name, texts, claim_text)
    return sorted(sorted(range(len(texts)), key=lambda i: -values[i])[:top_k])


def model_files(model):
    """The files a model needs."""
    if model == "e5-small":
        from src.contexts import embed_e5_small
        return [embed_e5_small.MODEL_DIR / "model.onnx", embed_e5_small.MODEL_DIR / "tokenizer.json"]
    if model == "static-s":
        from src import static_embed
        return [static_embed.MODEL_DIR / static_embed.MATRIX_FILE, static_embed.MODEL_DIR / "tokenizer.json"]
    return []


def run_guard(name, memory_limit):
    """(the ranker for the whole run, the reason when it is "none" instead of `name`, else None)."""
    model = uses_model(name)
    if model is None:
        return name, None
    need = MIN_MEMORY.get(model)
    if memory_limit is not None and need is not None and memory_limit < need:
        return "none", f"memory limit {memory_limit / GIB:.2f} GiB is below the {need / GIB:.2f} GiB {model} needs"
    if not all(Path(f).is_file() for f in model_files(model)):
        return "none", f"{model}'s files are missing"
    return name, None


def effective(name):
    """`name`, or "none" once its model failed to load or run in this process (see failed())."""
    model = uses_model(name)
    if model in _unusable:
        CASE["guard"] = _unusable[model]
        return "none"
    return name


def failed(model, error):
    """Record that a model failed in this process (any exception, MemoryError included): this case and every later
    one go on without it. deferral.NeedsModel is a BaseException, so it never arrives here."""
    _unusable.setdefault(model, f"{model} could not be used ({type(error).__name__}: {error})")
    log.warning("%s; going on without an embedding model", _unusable[model])
    CASE["guard"] = _unusable[model]


def best_or_without(name, texts, claim_text, top_k, without="none"):
    """best() for ranker `name`; if its model fails, best() for `without` ("none": the first top_k; "BM25")."""
    name = effective(name)
    if name != "none":
        try:
            return best(name, texts, claim_text, top_k)
        except Exception as e:
            if uses_model(name) is None:
                raise
            failed(uses_model(name), e)
    return best(without, texts, claim_text, top_k)
