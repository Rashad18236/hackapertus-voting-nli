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

from src import booklet, claim_router, memo, parse
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
_booklets = {}  # SHA-256 of a booklet's pages -> booklet.parse(pages); session 10: parsed once per booklet, not per case


def display(text):
    """A paragraph as shown to the model: words hyphenated across lines joined, whitespace collapsed."""
    text = re.sub(r"(\w) ?-\s*\n\s*(\w)", r"\1\2", text)
    return re.sub(r"\s+", " ", text).strip()


def route(pages, vote, claim_text):
    """(part, [(page, verbatim text)]) for the claim, or None when it must fall back."""
    part = claim_router.route(claim_text)
    if part is None:
        return None
    return route_part(pages, find(parsed_booklet(pages), vote), part, claim_text)


def find(parsed, vote):
    """The case's vote in a parsed booklet: by its title, else by meaning (session 10, step 8); or None."""
    return booklet.find_vote(parsed, vote) or vote_by_meaning(parsed, vote)


def route_part(pages, found, part, claim_text, search_text=None):
    """(part, [(page, verbatim text)]) of a found vote's part, or None. Session 11: a part that passed its own checks
    is used even when another part of the vote failed (Vote.valid; for a vote that passes every check, all parts are
    valid, as before). search_text (session 11, step 3, off): another text to rank paragraphs by in a long part."""
    if found is None or part not in found.valid:
        return None
    paragraphs = booklet.part_paragraphs(pages, found, part)
    if not paragraphs:
        return None
    if sum(len(display(t)) for _, t in paragraphs) > MAX_CHARS:
        paragraphs = most_similar(paragraphs, search_text or claim_text)
    return part, paragraphs


# ---------------------------------------------------------------- session 11, step 2: better fallbacks (off by default)

WIDE_TOP_K = 8
# PART lines of the two fallback levels (the prompt is the routed one with L1's sentence, under its own version name).
PART_LINES["vote-wide"] = ("paragraphs from all parts of the vote, the ones most similar to the claim; each paragraph "
                           "starts with the part it comes from in parentheses (voice: as that part's)")
PART_LINES["booklet-wide"] = ("paragraphs from the whole booklet, which may cover several votes, the ones most similar "
                              "to the claim (voice: as each paragraph's own part)")
PART_NAMES = {"summary": "summary", "detail": "detailed explanation", "committee": "committee's arguments",
              "parliament": "parliamentary debate", "council": "Federal Council and Parliament",
              "law": "text put to the vote"}
WIDE_PROMPT_VERSIONS = {"vote-wide": "A-v4-vote-wide", "booklet-wide": "A-v4-booklet-wide"}


_PYTHON = object()  # wide_route's default: find the vote with the Python parser


def wide_route(pages, vote, claim_text, levels, found=_PYTHON):
    """A better fallback for a case that cannot be routed (session 11, step 2): (level, [(page, text)], [part name or
    None]) or None (then embed-e5-small, as before).

    levels: the fallback levels switched on, a set of "vw" and "bw".
    - VW, vote-wide: the vote is found, but the claim names no part, or the named part is missing or empty. All
      paragraphs of the vote's valid parts, each with the name of its part; the WIDE_TOP_K most similar to the claim,
      in booklet order. If no part is valid but the vote's pages are known, the paragraphs of those pages, without
      part names.
    - BW, booklet-wide: the vote is not found. The paragraphs of the whole booklet; the WIDE_TOP_K most similar.
    """
    if found is _PYTHON:  # session 11, step 3: AP-structure may pass the vote it found instead (None: not found)
        found = find(parsed_booklet(pages), vote)
    if found is not None:
        if "vw" not in levels:
            return None
        paragraphs, names = vote_paragraphs(pages, found)
        if not paragraphs:
            return None
        return "vote-wide", *keep_most_similar(paragraphs, names, claim_text)
    if "bw" not in levels:
        return None
    paragraphs = [(p, t) for p in sorted(pages) for t in booklet.page_paragraphs(pages[p])]
    if not paragraphs:
        return None
    return "booklet-wide", *keep_most_similar(paragraphs, [None] * len(paragraphs), claim_text)


def vote_paragraphs(pages, found):
    """([(page, text)], [part name or None]) of a vote: its valid parts in booklet order (a text seen in an earlier
    part is not repeated), else the paragraphs of the vote's pages when the contents give them."""
    paragraphs, names, seen = [], [], set()
    for part in booklet.PARTS:
        if part not in found.valid:
            continue
        for page, text in booklet.part_paragraphs(pages, found, part):
            if text not in seen:
                seen.add(text)
                paragraphs.append((page, text))
                names.append(PART_NAMES[part])
    if paragraphs:
        order = sorted(range(len(paragraphs)), key=lambda i: paragraphs[i][0])  # booklet order (stable within a page)
        return [paragraphs[i] for i in order], [names[i] for i in order]
    for p in vote_pages(found):
        for text in booklet.page_paragraphs(pages.get(p, "")):
            paragraphs.append((p, text))
    return paragraphs, [None] * len(paragraphs)


def vote_pages(found):
    """The vote's pages from its contents entry: the older layout's block, or the summary pages and the pages from
    its first later section to its law text."""
    entry = found.entry
    if "block" in entry:
        a, b = entry["block"]
        return list(range(a, b + 1))
    pages = set()
    if "summary" in entry:
        pages |= set(range(entry["summary"][0], entry["summary"][1] + 1))
    later = [entry[k] for k in ("detail", "arguments", "law") if k in entry]
    if later:
        pages |= set(range(min(later), max(later) + 1))
    return sorted(pages)


def keep_most_similar(paragraphs, names, claim_text, top_k=WIDE_TOP_K):
    """The top_k paragraphs (and their part names) most similar to the claim, in their original order."""
    if len(paragraphs) <= top_k:
        return paragraphs, names
    scores = similarities(paragraphs, claim_text)
    best = sorted(sorted(range(len(paragraphs)), key=lambda i: -scores[i])[:top_k])
    return [paragraphs[i] for i in best], [names[i] for i in best]


def wide_texts(paragraphs, names):
    """The paragraphs as shown: each with its part's name in parentheses when it has one."""
    return [f"({n}) {display(t)}" if n else display(t) for (_, t), n in zip(paragraphs, names)]


def parsed_booklet(pages):
    """booklet.parse(pages), computed once per booklet text (the result is only read, never changed)."""
    # Session 11, step 4: a booklet read page by page (parse.Pages) is named by its PDF file's SHA-256, so that naming it
    # reads no page; every other booklet by the SHA-256 of its page texts, as before.
    key = getattr(pages, "key", None) or \
        hashlib.sha256("\f".join(f"{n}\n{t}" for n, t in sorted(pages.items())).encode("utf-8")).hexdigest()
    return memo.once(_booklets, key, lambda: _timed_parse(pages))


def _timed_parse(pages):
    from src import timing
    with timing.phase("booklet_parse"):
        return booklet.parse(pages)


_title_vectors = {}  # SHA-256 of a booklet's vote titles -> their e5 vectors (session 10, step 8)
# Session 10, step 8: a vote name the title match cannot place (e.g. in another language than the booklet) is placed
# by meaning if the closest title leads the second closest by at least this much (e5 cosine). With the names of the
# same votes in the other languages swapped in for all 880 dev and val cases, no lead of a wrong pick reached 0.0296;
# 0.04 keeps a margin (182 of 264 swapped names placed right, none wrong; the rest fall back as before). A name of a
# vote that is not in the booklet at all can be placed too (649 of 5,220 names of other dates' votes reached 0.04);
# in the dataset the vote always belongs to the booklet. Booklets with a single vote are never placed by meaning.
VOTE_MARGIN = 0.04


def vote_by_meaning(parsed, vote):
    """The vote whose title is closest in meaning to `vote` if it leads the next one by VOTE_MARGIN, else None.
    Only asked when booklet.find_vote finds nothing; if e5 cannot run (e.g. no model files), None, as before."""
    try:
        position, lead = vote_scores(parsed, vote)
    except Exception:
        return None
    if position is None or lead < VOTE_MARGIN:
        return None
    return parsed.votes[position]


def vote_scores(parsed, vote):
    """(position of the vote whose contents title is closest in meaning to `vote`, its lead over the second closest)
    by e5 cosine ("query: " + vote name, "passage: " + title, whitespace collapsed); (None, 0.0) without votes and
    (0, 0.0) for a booklet with a single vote: with nothing to lead, a name is never placed by meaning (any name,
    also one of a vote not in the booklet, would be closest to the only title)."""
    if parsed is None or not parsed.votes or not vote.strip():
        return None, 0.0
    if len(parsed.votes) == 1:
        return 0, 0.0
    titles = [" ".join(v.title.split()) for v in parsed.votes]
    key = hashlib.sha256("\n".join(titles).encode("utf-8")).hexdigest()
    vectors = memo.once(_title_vectors, key,
                        lambda: retrieval.embedder("e5-small").embed([f"passage: {t}" for t in titles]))
    scores = vectors @ retrieval.query_vector("e5-small", " ".join(vote.split()))
    order = sorted(range(len(titles)), key=lambda i: -scores[i])
    return order[0], float(scores[order[0]] - scores[order[1]])


SEARCH_MODEL = "e5-small"  # session 11, step 6: "e5-small-q8" (e5's own 8-bit export) is tried, off by default


def similarities(paragraphs, claim_text):
    """Cosine similarity (e5-small) between the claim and each paragraph as shown, in the paragraphs' order."""
    texts = [display(t) for _, t in paragraphs]
    key = hashlib.sha256("\n\n".join(texts).encode("utf-8")).hexdigest()
    vectors = memo.once(_vectors, key, lambda: retrieval.embedder(SEARCH_MODEL).embed([f"passage: {t}" for t in texts]))
    return vectors @ retrieval.query_vector(SEARCH_MODEL, claim_text)


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
