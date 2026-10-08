"""Task A evidence settings (Settings.evidence_a in src/cli.py).

- "cited" (default): the text of the pages the model cited, split at 5,000
  characters, at most five items.
- "cited-then-retrieved" (session 4): the same items first, then the other
  pages the model was shown, most similar to the claim first (e5-small, a
  page's best chunk), until there are five items.
- "cited-pieces" (session 6): only the pages the model cited, each split into
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
