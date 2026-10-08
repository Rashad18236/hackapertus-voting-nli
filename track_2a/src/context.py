"""Which booklet pages task A sends to the model.

MODES:
- "full":         every page (the full-document baseline).
- "vote-section": only the pages about the ballot named in `vote`.

Selection is deterministic and local (no model call, no embeddings), so it
costs no tokens and does not depend on case order.

How "vote-section" works. Voting booklets cover several ballots. Every page
of a ballot's part starts with a running header that names it ("Deuxième
objet : loi sur la chasse", "Erste Vorlage: Bargeld-Initiative", "Primo
oggetto: Sublocazione"). The header is in the booklet's language, like `vote`,
so we match the two without caring which language the claim is in:

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
"""

import math
import re
import unicodedata

from rapidfuzz import fuzz

MODES = ("full", "vote-section")

HEAD_CHARS = 160      # how much of each page counts as its header
REL_THRESHOLD = 0.5   # keep pages whose header score is at least this share of the best
FOLLOW = 1            # also keep this many pages after each kept page
MAX_GAP = 10          # fill gaps of at most this many pages between kept pages
TITLE_CHARS = 70      # the start of the vote title used for the full-title match
TITLE_MIN_RATIO = 90  # fuzzy match score (0-100) for the full-title match

_WORD = re.compile(r"[^\W\d_]{4,}")


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
    """Return {page number: text} for the pages to send, in page order."""
    if mode == "full":
        return dict(sorted(pages.items()))
    if mode == "vote-section":
        return {p: pages[p] for p in vote_section(pages, vote)}
    raise ValueError(f"unknown context mode {mode!r}")
