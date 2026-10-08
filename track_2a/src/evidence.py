"""Task A evidence settings (Settings.evidence_a in src/cli.py).

- "cited" (default): the text of the pages the model cited, split at 5,000
  characters, at most five items.
- "cited-then-retrieved" (session 4): the same items first, then the other
  pages the model was shown, most similar to the claim first (e5-small, a
  page's best chunk), until there are five items.

Why the second exists: the starter's scorer (evaluate.py, commit 559b598)
counts a gold entailment or contradiction case as found when any of the first
five evidence items matches the gold passage, and it does not penalise extra
items. Filling the free slots with the next most likely pages can only add
matches. Both settings give evidence only for labels 0 and 2.

Team decision (session 5): evidence holds only pages Apertus cited, so
"cited-then-retrieved" stays off; it is kept for the record.
"""

from src import parse
from src.contexts import retrieval

MODES = ("cited", "cited-then-retrieved")
MAX_ITEMS = 5


def items(mode, cited_items, shown, claim_text):
    """Evidence items for a label-0/2 answer: the cited items, padded if the mode says so."""
    if mode == "cited":
        return cited_items
    if mode != "cited-then-retrieved":
        raise ValueError(f"unknown evidence mode {mode!r}")
    cited_pages = {item["page"] for item in cited_items}
    extra = [p for p in retrieval.rank_pages(shown, claim_text) if p not in cited_pages]
    room = MAX_ITEMS - len(cited_items)
    return cited_items + (parse.evidence_items(shown, extra, max_items=room) if room > 0 else [])
