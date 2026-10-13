"""Task A evidence settings (Settings.evidence_a in src/cli.py).

- "cited": the text of the pages the model cited, split at 5,000 characters,
  at most five items (the default until session 6).
- "cited-then-retrieved" (session 4): the same items first, then the other
  pages the model was shown, most similar to the claim first (e5-small, a
  page's best chunk), until there are five items.
- H (session 13, step 3; off by default, Settings.evidence_hedge_a): for routed answers, today's items, then the
  paragraph before the first cited one when that one opens its page, then the whole cited page (see hedge()).
- "cited-pieces" (session 6, default): only the pages the model cited, each split into
  the pipeline's pieces of at most 1,000 characters (as the embedding chunks,
  src/contexts/embed_e5_small.py). Each piece is its own item with its page.
  Pieces are taken in turn across the cited pages, in the model's order: the
  first piece of each page, then the second of each, and so on, at most five.

Why the second exists: the starter's scorer (evaluate.py, commit 559b598)
counts a gold entailment or contradiction case as found when any of the first
five evidence items matches the gold passage, and it does not penalise extra
items. Filling the free slots with the next most likely pages can only add
matches. Both settings give evidence only for labels 0 and 2.

Team decision (session 5): evidence holds only pages Apertus cited, so
"cited-then-retrieved" stays off; it is kept for the record.

Why "cited-pieces" exists: the scorer compares each item with the gold
passage by rapidfuzz's partial ratio, which matches when the shorter text lies
almost entirely inside the longer one. A whole page matches only if it holds
the whole passage or lies inside it; a page that also holds other text, or a
passage running over a page break, fails. A 1,000-character piece lying inside
the passage matches. It uses no page the model did not cite.
"""

from src import parse
from src.contexts import retrieval

MODES = ("cited", "cited-then-retrieved", "cited-pieces")
MAX_ITEMS = 5
PIECE_CHARS = 1000  # the pipeline's chunk size (src/contexts/embed_e5_small.py)


def items(mode, cited_items, shown, claim_text, cited_pages=()):
    """Evidence items for a label-0/2 answer.

    cited_items: the cited pages as whole-page items (parse.evidence_items);
    cited_pages: the page numbers as the model gave them (used by "cited-pieces").
    """
    if mode == "cited":
        return cited_items
    if mode == "cited-pieces":
        return pieces(shown, cited_pages)
    if mode != "cited-then-retrieved":
        raise ValueError(f"unknown evidence mode {mode!r}")
    cited_pages = {item["page"] for item in cited_items}
    extra = [p for p in retrieval.rank_pages(shown, claim_text) if p not in cited_pages]
    room = MAX_ITEMS - len(cited_items)
    return cited_items + (parse.evidence_items(shown, extra, max_items=room) if room > 0 else [])


def pieces(shown, cited_pages, max_items=MAX_ITEMS, piece_chars=PIECE_CHARS):
    """Pieces of the cited pages, taken in turn across the pages; pages not shown or repeated are skipped."""
    pages = [p for p in dict.fromkeys(cited_pages) if p in shown]
    per_page = [parse._split(shown[p].strip(), piece_chars) for p in pages]
    items = []
    for i in range(max((len(t) for t in per_page), default=0)):
        for page, texts in zip(pages, per_page):
            if i < len(texts):
                if len(items) == max_items:
                    return items
                items.append({"page": page, "text": texts[i]})
    return items


def hedge(items, paragraphs, cited, page_texts=None, max_items=MAX_ITEMS):
    """H (session 13, step 3; off by default): a routed answer's evidence with two more items for the page check
    that the organisers have not settled (the quote's page, any gold page, or the first gold page).

    items: today's items (kept first, in their order); paragraphs: the routed part as sent, [(page, text)];
    cited: the paragraph numbers as the answer gave them; page_texts: {page: text} of the part's pages.
    1. If the first cited paragraph is the first paragraph of its page and the part continues from an earlier page
       (the part's paragraph before it lies on an earlier page), that earlier paragraph, with its own page.
    2. If slots remain, the whole text of the first cited paragraph's page (at most 5,000 characters, its page).
    At most max_items items; a text already present is left out; every item's text lies on its page."""
    items = list(items)[:max_items]
    valid = [n for n in cited if isinstance(n, int) and not isinstance(n, bool) and 1 <= n <= len(paragraphs)]
    if not valid:
        return items
    present = {item["text"] for item in items}

    def add(page, text):
        if len(items) < max_items and text and text not in present:
            items.append({"page": page, "text": text})
            present.add(text)
    index = valid[0] - 1
    page = paragraphs[index][0]
    if index > 0 and paragraphs[index - 1][0] < page:
        before_page, before_text = paragraphs[index - 1]
        add(before_page, before_text[:parse.MAX_ITEM_CHARS])
    whole = (page_texts or {}).get(page)
    if whole and whole.strip():
        add(page, whole.strip()[:parse.MAX_ITEM_CHARS])
    return items

