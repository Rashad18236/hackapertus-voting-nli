"""Tell German, French and Italian apart by their most common short words (robustness experiments, Kaan).

Used where a variant needs a text's language but only has the text: bm25-mt (src/contexts/bm25_mt.py) needs the
booklet's language to translate the claim into it. The request's own language fields are preferred wherever
they reach the code (src/strategies.py); this is the fallback, and it also copes with a wrong language field.

Each language has about twenty of its most frequent function words; the language whose words occur most often
wins. On a booklet page or a claim of one sentence this is reliable enough; ties go to the first of de, fr, it.
"""

import re

LANGS = ("de", "fr", "it")
_STOPWORDS = {
    "de": {"der", "die", "das", "und", "ist", "nicht", "mit", "von", "den", "dem", "des", "ein", "eine", "auf",
           "für", "werden", "wird", "sich", "auch", "dass", "bei", "nach"},
    "fr": {"le", "la", "les", "et", "est", "des", "une", "pour", "dans", "que", "qui", "pas", "sur", "par",
           "au", "aux", "du", "ne", "sont", "avec", "cette", "être"},
    "it": {"il", "la", "le", "e", "è", "di", "che", "per", "una", "non", "con", "del", "della", "dei", "gli",
           "nel", "sono", "alla", "anche", "come", "questo", "essere"},
}
_WORD = re.compile(r"[^\W\d_]+")


def detect(text, default="de"):
    """'de', 'fr' or 'it' for text; default when no function word is found."""
    words = _WORD.findall(text.lower())
    counts = {lang: sum(w in _STOPWORDS[lang] for w in words) for lang in LANGS}
    best = max(LANGS, key=lambda lang: counts[lang])
    return best if counts[best] > 0 else default
