"""Task B context variants (session 9, phase C): how much of the reference passage Apertus reads.

The default was "cut" in session 9 and is "full" again since session 10, step 2 (B-cut's embedding costs local
time when the model is fast). The passage's words are never changed, only cut or numbered:

- "full" (default): the whole reference text with task B's prompt (v3-topic-first).
- "cut" (B-cut): a reference over CUT_CHARS characters becomes its first line (the ballot's title) plus the
  TOP_K paragraphs most similar to the claim (multilingual-e5-small, ranked as section-route ranks a long
  part), in their order; the prompt is unchanged. Shorter references stay whole.
- "cut4" (B-cut4, session 10, step 5): the same with CUT4_CHARS and CUT4_TOP_K: a reference over 3,000
  characters becomes its first line plus the 4 most similar paragraphs.
- "unified" (B-U, session 10, step 9): B-para's numbered paragraphs (B-cut's text) with task A's default routed
  prompt (A-v4-section-route-L1) and answer schema; the cited paragraphs are not used (task B evidence stays []).
- "para" (B-para): the same text as numbered paragraphs ("[1] ..."), with task A's paragraph prompt and answer
  schema (A-v4-section-route); the answer's paragraph numbers are not used (task B evidence stays []).

Paragraphs come from src/booklet.py's page_paragraphs (the same splitting section-route uses): consecutive
lines, verbatim, fragments under 40 characters dropped. If the passage gives no paragraphs, the whole text is
used.
"""

import hashlib
import re

from src import booklet, memo
from src.contexts import retrieval, section_route

MODES = ("full", "cut", "para", "cut4", "unified", "cut4-q", "cut4-t", "cut4-l", "cut4-h", "cut4-r", "cut4-bm25")
CUT_CHARS = 8000
TOP_K = 8
CUT4_CHARS = 3000
CUT4_TOP_K = 4
LIMITS = {"cut": (CUT_CHARS, TOP_K), "para": (CUT_CHARS, TOP_K), "cut4": (CUT4_CHARS, CUT4_TOP_K),
          "unified": (CUT_CHARS, TOP_K), **{m: (CUT4_CHARS, CUT4_TOP_K) for m in ("cut4-q", "cut4-t", "cut4-l", "cut4-h", "cut4-r", "cut4-bm25")}}
# Session 11, step 6 (off by default): B-cut4 with another way to pick its 4 paragraphs (the "selector"):
#   cut4    E: e5 (multilingual-e5-small) on whole paragraphs, as session 10
#   cut4-q  Q: the same model quantised to 8-bit integers (the model's own export, src/contexts/embed_e5_small.py)
#   cut4-t  T: e5 on the first T_CHARS characters of each paragraph
#   cut4-l  L: no model: shared character 4-grams and numbers between claim and paragraph
#   cut4-h  H: L when claim and reference share a language, else H_MODEL (the fastest e5 variant, measured)
#   cut4-r  R (session 12, step 3): the ranker src/rankers.py's ACTIVE names (B-R), on the paragraphs' whole text
#   cut4-bm25  B (session 12, step 3): Kaan's BM25 on the claim; when claim and reference differ in language, on the
#              claim translated by Apertus (src/cli.py makes that call, then passes the translation as the search text)
SELECTORS = {"cut4": "E", "cut4-q": "Q", "cut4-t": "T", "cut4-l": "L", "cut4-h": "H", "cut4-r": "R",
             "cut4-bm25": "B"}
T_CHARS = 300
H_MODEL = "cut4-t"
PART_LINE = ("a passage from the booklet's section on the ballot named in VOTE; its first paragraph is the "
             "ballot's title (voice: as stated in the passage)")


def split(reference_text):
    """(first line, [paragraphs of the rest]) of a reference passage."""
    lines = reference_text.strip().splitlines()
    if not lines:
        return "", []
    return lines[0].strip(), booklet.page_paragraphs("\n".join(lines[1:]))


def needs_translation(reference_text, mode, same_language):
    """Session 12, step 3: B-BM25 (cut4-bm25) ranks a long cross-language reference with the claim translated by
    Apertus (one call, made by src/cli.py in the main process)."""
    return (mode == "cut4-bm25" and not same_language and is_long(reference_text, mode)
            and len(split(reference_text)[1]) > LIMITS[mode][1])


def is_long(reference_text, mode="cut"):
    return len(reference_text) > LIMITS.get(mode, (CUT_CHARS, TOP_K))[0]


def cut_paragraphs(reference_text, claim_text, mode="cut", same_language=True):
    """(first line, paragraphs): all of them for a short reference, the top_k most similar to the claim (in their
    order) for a long one (CUT_CHARS and TOP_K, or the mode's own limits). same_language: whether claim and reference
    share a language (only selector H uses it)."""
    top_k = LIMITS.get(mode, (CUT_CHARS, TOP_K))[1]
    first, paragraphs = split(reference_text)
    if is_long(reference_text, mode) and len(paragraphs) > top_k:
        selector = SELECTORS.get(mode, "E")
        if selector == "H":
            selector = "L" if same_language else SELECTORS[H_MODEL]
        if selector == "E":
            paragraphs = [text for _, text in section_route.most_similar([(0, p) for p in paragraphs], claim_text,
                                                                         top_k)]
        else:
            scores = selector_scores(selector, paragraphs, claim_text)
            best = sorted(sorted(range(len(paragraphs)), key=lambda i: -scores[i])[:top_k])
            paragraphs = [paragraphs[i] for i in best]
    return first, paragraphs


_q_vectors = {}  # (selector, SHA-256 of the paragraphs) -> vectors


def selector_scores(selector, paragraphs, claim_text):
    """Similarity of the claim to each paragraph for selector Q, T or L (session 11, step 6)."""
    if selector == "L":
        return [lexical_score(claim_text, p) for p in paragraphs]
    if selector in ("R", "B"):
        from src import rankers
        name = rankers.ACTIVE["name"] if selector == "R" else "BM25"
        return rankers.scores(name, [section_route.display(p) for p in paragraphs], claim_text)
    model = "e5-small-q8" if selector == "Q" else "e5-small"
    texts = [section_route.display(p) for p in paragraphs]
    if selector == "T":
        texts = [t[:T_CHARS] for t in texts]
    key = (selector, hashlib.sha256("\n\n".join(texts).encode("utf-8")).hexdigest())
    vectors = memo.once(_q_vectors, key, lambda: retrieval.embedder(model).embed([f"passage: {t}" for t in texts]))
    return list(vectors @ retrieval.query_vector(model, claim_text))


_WORD = re.compile(r"[^\w\s]")
_NUMBER = re.compile(r"\d+(?:[.,']\d+)*")


def lexical_score(claim_text, paragraph):
    """Selector L: the share of the claim's character 4-grams found in the paragraph, plus 1 for each number they
    share (numbers carry much of a claim's meaning: shares, dates, amounts). Lower case, punctuation removed."""
    def grams(text):
        flat = " ".join(_WORD.sub(" ", text.lower()).split())
        return {flat[i:i + 4] for i in range(max(0, len(flat) - 3))}
    claim_grams = grams(claim_text)
    shared = len(claim_grams & grams(paragraph)) / len(claim_grams) if claim_grams else 0.0
    numbers = set(_NUMBER.findall(claim_text)) & set(_NUMBER.findall(paragraph))
    return shared + len(numbers)


def _selector(mode, same_language):
    selector = SELECTORS.get(mode, "E")
    if selector == "H":
        selector = "L" if same_language else SELECTORS[H_MODEL]
    return selector


def ranking_model(mode, same_language=True):
    """The embedding model ("e5-small", "static-s") this mode ranks a long reference's paragraphs with, or None."""
    from src import rankers
    selector = _selector(mode, same_language)
    if selector in ("L", "Q", "B"):
        return None  # L and B need no model; Q (8-bit e5, off) keeps its own error path (src/cli.py)
    if selector == "R":
        return rankers.uses_model(rankers.ACTIVE["name"])
    return "e5-small"


def no_ranking_model(mode, same_language=True):
    """Session 12, step 2: whether this mode would rank with an embedding model that cannot run: the run's ranker is
    "none" (memory guard), or the model failed earlier in this process."""
    from src import rankers
    if _selector(mode, same_language) in ("L", "Q", "B"):
        return False
    if rankers.ACTIVE["name"] == "none":
        return True
    model = ranking_model(mode, same_language)
    if model in rankers._unusable:
        rankers.CASE["guard"] = rankers._unusable[model]
        return True
    return False


def cut_text(reference_text, claim_text, mode="cut", same_language=True):
    """B-cut's (or B-cut4's) reference text: unchanged if short; else the first line and the kept paragraphs,
    verbatim."""
    if not is_long(reference_text, mode):
        return reference_text
    if len(split(reference_text)[1]) > LIMITS.get(mode, (CUT_CHARS, TOP_K))[1] and no_ranking_model(mode, same_language):
        return reference_text  # session 12, step 2: no embedding model can run, so the reference is sent whole
    first, paragraphs = cut_paragraphs(reference_text, claim_text, mode, same_language)
    if not paragraphs:
        return reference_text
    return "\n\n".join([first] + paragraphs)


def para_texts(reference_text, claim_text):
    """B-para's numbered paragraphs, as shown to the model: the first line, then the (kept) paragraphs."""
    first, paragraphs = cut_paragraphs(reference_text, claim_text)
    if not paragraphs:
        return [section_route.display(reference_text)]
    return [first] + [section_route.display(p) for p in paragraphs]
