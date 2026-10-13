"""Local machine translation between German, French and Italian (robustness experiments, Kaan; off by default).

Used by the cross-language tournament (src/strategies.py) and by bm25-mt (src/contexts/bm25_mt.py). Not an LLM
call: no tokens, no BASE_URL. Apertus still makes every entailment decision; translation only changes the
language a text is shown in.

Model: facebook/m2m100_418M (MIT licence; one model for all six directions between de, fr and it; Helsinki-NLP's
opus-mt has no French-to-Italian model), converted to CTranslate2 with int8 weights (about 450 MB) by
scripts/fetch_mt_model.py. CTranslate2 runs it on CPU without PyTorch. The model folder comes from
MT_MODEL_DIR (default /app/models/m2m100_418M-ct2, as EMBED_MODEL_DIR for e5); it is not in the Docker image
(requirements-experiments.txt, not requirements.txt).

How a text is translated: it is cut into pieces of whole sentences of at most PIECE_CHARS characters (the model
translates short inputs best and has a 1,024-token limit), the pieces of all texts go to the model in one batch,
and each text's pieces are joined again with a space. Line breaks inside a text are not kept. Greedy decoding
(beam 1) keeps it fast; the result is deterministic. Translations are cached in memory by text and direction.
"""

import os
import re
import time
from pathlib import Path

MODEL_DIR = Path(os.environ.get("MT_MODEL_DIR", "/app/models/m2m100_418M-ct2"))
LANGS = ("de", "fr", "it")
PIECE_CHARS = 400
_SENTENCE_END = re.compile(r"(?<=[.!?;:])\s+")

_model = {}    # "translator", "sp": loaded once per process
_cache = {}    # (src, tgt, text) -> translation
stats = {"ms": 0, "pieces": 0}  # total translation time of this process (for reports)


class TranslationError(RuntimeError):
    """The model is missing or failed; callers fall back to their untranslated path."""


def _load():
    if not _model:
        try:
            import ctranslate2
            import sentencepiece
        except ImportError as e:
            raise TranslationError(f"translation needs ctranslate2 and sentencepiece ({e})") from e
        if not (MODEL_DIR / "model.bin").is_file():
            raise TranslationError(f"no translation model in {MODEL_DIR} (run scripts/fetch_mt_model.py)")
        threads = int(os.environ.get("MT_THREADS") or min(4, os.cpu_count() or 1))
        _model["translator"] = ctranslate2.Translator(str(MODEL_DIR), device="cpu", compute_type="int8",
                                                      intra_threads=threads)
        _model["sp"] = sentencepiece.SentencePieceProcessor(model_file=str(MODEL_DIR / "sentencepiece.bpe.model"))
    return _model["translator"], _model["sp"]


def pieces(text, max_chars=PIECE_CHARS):
    """text as pieces of whole sentences of at most max_chars characters. A sentence longer than max_chars
    (a list, a law clause) is first cut at spaces."""
    sentences = []
    for sentence in _SENTENCE_END.split(re.sub(r"\s+", " ", text).strip()):
        while len(sentence) > max_chars:
            cut = sentence.rfind(" ", 0, max_chars)
            cut = cut if cut > 0 else max_chars
            sentences.append(sentence[:cut])
            sentence = sentence[cut:].strip()
        if sentence:
            sentences.append(sentence)
    out, current = [], ""
    for sentence in sentences:
        if current and len(current) + 1 + len(sentence) > max_chars:
            out.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        out.append(current)
    return out


def translate(texts, src, tgt):
    """texts translated from src into tgt (both in LANGS), in order. Same language or empty text: unchanged.
    Raises TranslationError when the model is missing or fails."""
    if src == tgt or not texts:
        return list(texts)
    if src not in LANGS or tgt not in LANGS:
        raise TranslationError(f"unsupported direction {src}->{tgt}")
    todo = [t for t in dict.fromkeys(texts) if t.strip() and (src, tgt, t) not in _cache]
    if todo:
        translator, sp = _load()
        split = [pieces(t) for t in todo]
        flat = [p for ps in split for p in ps]
        start = time.perf_counter()
        try:
            results = translator.translate_batch(
                [[f"__{src}__"] + sp.encode(p, out_type=str) + ["</s>"] for p in flat],
                target_prefix=[[f"__{tgt}__"]] * len(flat), beam_size=1, max_batch_size=16,
                max_decoding_length=512)
        except Exception as e:  # never let translation stop a case
            raise TranslationError(f"translation failed ({type(e).__name__}: {e})") from e
        stats["ms"] += round((time.perf_counter() - start) * 1000)
        stats["pieces"] += len(flat)
        decoded = iter(sp.decode(r.hypotheses[0][1:]) for r in results)  # drop the target language token
        for text, ps in zip(todo, split):
            _cache[(src, tgt, text)] = " ".join(next(decoded) for _ in ps)
    return [_cache.get((src, tgt, t), t) for t in texts]
