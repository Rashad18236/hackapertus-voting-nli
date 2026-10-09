"""Context variant "section-route": the part of the vote that the claim's opening names.

Built in session 6 (Rashad, with Claude). Local and deterministic: a parser,
a pattern router and, for long parts, the e5 embedding of embed-e5-small.

1. The claim's opening names its source (src/claim_router.py): the summary,
   the Federal Council, the committee, the text put to the vote, or what
   happens if the vote is accepted (the detailed section).
2. The booklet is parsed into votes and parts (src/booklet.py); the case's
   `vote` picks the vote.
3. The routed part is sent as numbered paragraphs, running headers and page
   numbers removed; each paragraph keeps its page and its verbatim text, so
   the paragraphs Apertus cites become the evidence (src/cli.py). The
   committee's and the council's parts include their recommendation boxes
   from the summary pages.
4. If the part has more than MAX_CHARS characters, only the TOP_K paragraphs
   most similar to the claim are kept (multilingual-e5-small, the model of
   embed-e5-small), in page order.
5. If the router, the parser or the vote match gives nothing, the case runs
   exactly as embed-e5-small (FALLBACK): same selection, prompt and evidence.

Apertus alone decides the label; this variant only chooses what it reads.
"""

import hashlib
import re

from src import booklet, claim_router, parse
from src.contexts import embed_e5_small, retrieval

NAME = "section-route"
PROMPT_VERSION = "A-v4-section-route"  # when routed; a fallback case uses FALLBACK's prompt
FALLBACK = "embed-e5-small"
MAX_CHARS = 8000
TOP_K = 8

# The PART line of the prompt: which part and whose voice, one line per route.
PART_LINES = {
    "summary": "the summary of the vote, with each side's recommendation box "
               "(voice: the Federal Chancellery's neutral summary; each box speaks for its side)",
    "detail": "the detailed explanation of the vote, what changes if it is accepted "
              "(voice: the Federal Chancellery's neutral explanation)",
    "committee": "the committee's arguments and recommendation (voice: the initiative or referendum committee)",
    "council": "the arguments and recommendation of the Federal Council and Parliament "
               "(voice: the Federal Council and Parliament)",
    "law": "the text put to the vote, the legal text itself (voice: the law as it would be adopted)",
}

_vectors = {}  # SHA-256 of a part's paragraphs -> their e5 vectors


def display(text):
    """A paragraph as shown to the model: words hyphenated across lines joined, whitespace collapsed."""
    text = re.sub(r"(\w) ?-\s*\n\s*(\w)", r"\1\2", text)
    return re.sub(r"\s+", " ", text).strip()


def route(pages, vote, claim_text):
    """(part, [(page, verbatim text)]) for the claim, or None when it must fall back."""
    part = claim_router.route(claim_text)
    if part is None:
        return None
    found = booklet.find_vote(booklet.parse(pages), vote)
    if found is None or not found.ok:
        return None
    paragraphs = booklet.part_paragraphs(pages, found, part)
    if not paragraphs:
        return None
    if sum(len(display(t)) for _, t in paragraphs) > MAX_CHARS:
        paragraphs = most_similar(paragraphs, claim_text)
    return part, paragraphs


def similarities(paragraphs, claim_text):
    """Cosine similarity (e5-small) between the claim and each paragraph as shown, in the paragraphs' order."""
    texts = [display(t) for _, t in paragraphs]
    key = hashlib.sha256("\n\n".join(texts).encode("utf-8")).hexdigest()
    if key not in _vectors:
        _vectors[key] = retrieval.embedder("e5-small").embed([f"passage: {t}" for t in texts])
    return _vectors[key] @ retrieval.query_vector("e5-small", claim_text)


def most_similar(paragraphs, claim_text, top_k=TOP_K):
    """The top_k paragraphs by cosine similarity to the claim (e5-small), in their original order."""
    scores = similarities(paragraphs, claim_text)
    best = sorted(range(len(paragraphs)), key=lambda i: -scores[i])[:top_k]
    return [paragraphs[i] for i in sorted(best)]


def select(pages, vote, claim_text, cross_language=False):
    """The registry's interface (src/context.py): the routed paragraphs as prompt text and the pages
    they come from, or embed-e5-small's selection when the case falls back."""
    routed = route(pages, vote, claim_text)
    if routed is None:
        return embed_e5_small.select(pages, vote, claim_text, cross_language)
    _, paragraphs = routed
    text = "\n".join(f"[{i}] {display(t)}" for i, (_, t) in enumerate(paragraphs, start=1))
    return text, {p: pages[p] for p, _ in paragraphs}


HALVES_FILL_TO = 5  # with halves=True: items up to this many (the scorer looks at the first five)
_SENTENCE_END = re.compile(r"[.!?](?=\s)")


def evidence_items(paragraphs, cited, max_items=3, halves=False):
    """Evidence for cited paragraph numbers (1-based, as shown): verbatim text with its page.

    Unknown or repeated numbers are skipped, and so is a paragraph whose text equals one already taken (a law
    can repeat a clause word for word; session 8, P7); a paragraph over 5,000 characters is split.

    halves=True (session 9, A2; off by default): after these items, the two halves of each cited paragraph, cut
    at the sentence end nearest its middle, are added in turn until there are HALVES_FILL_TO items; a text
    already present is skipped, and a paragraph with no sentence end inside it gives no halves.
    """
    items, seen, taken, used = [], set(), set(), []
    for n in cited:
        if n in seen or not 1 <= n <= len(paragraphs):
            continue
        seen.add(n)
        page, text = paragraphs[n - 1]
        if text in taken:
            continue
        taken.add(text)
        used.append((page, text))
        items += [{"page": page, "text": piece} for piece in parse._split(text, parse.MAX_ITEM_CHARS)]
    items = items[:max_items]
    if halves:
        present = {item["text"] for item in items}
        for page, text in used:
            for half in split_in_half(text):
                if len(items) >= HALVES_FILL_TO:
                    break
                if half not in present:
                    items.append({"page": page, "text": half})
                    present.add(half)
    return items


def split_in_half(text):
    """The two halves of a paragraph, cut after the sentence end (. ! ?) nearest its middle; [] if it has
    no sentence end inside it. Both halves are verbatim pieces of the text."""
    middle = len(text) / 2
    ends = [m.end() for m in _SENTENCE_END.finditer(text) if 0 < m.end() < len(text.rstrip())]
    if not ends:
        return []
    cut = min(ends, key=lambda e: abs(e - middle))
    first, second = text[:cut].strip(), text[cut:].strip()
    return [h for h in (first, second) if h]
