"""Booklet PDF -> text per page, with 1-based page numbers.

Uses pypdf (BSD licence), a pure-Python PDF reader. We avoid PyMuPDF because
of its AGPL licence.

Parsed booklets are cached as JSON under a writable cache directory (default
/tmp/booklet-cache, the only writable place besides /output in the container).
The cache key is the file's SHA-256, so the result depends only on the file's
content, never on which case asked first: predictions do not depend on order.
"""

import hashlib
import json
import os
from pathlib import Path

from pypdf import PdfReader

CACHE_DIR = Path(os.environ.get("BOOKLET_CACHE_DIR", "/tmp/booklet-cache"))
MAX_ITEM_CHARS = 5000  # official limit for one evidence item (about one page)


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def extract_pages(pdf_path):
    """Return a list of page texts; element i is PDF page i + 1. No caching."""
    reader = PdfReader(str(pdf_path))
    return [(page.extract_text() or "") for page in reader.pages]


def load_pages(pdf_path, cache_dir=CACHE_DIR):
    """Return {page number (1-based): text}, using the cache when possible."""
    key = _sha256(pdf_path)
    cache_file = Path(cache_dir) / f"{key}.json"
    if cache_file.exists():
        stored = json.loads(cache_file.read_text(encoding="utf-8"))
        return {int(k): v for k, v in stored.items()}
    pages = {i: text for i, text in enumerate(extract_pages(pdf_path), start=1)}
    try:
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        tmp = cache_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(pages, ensure_ascii=False), encoding="utf-8")
        tmp.replace(cache_file)  # atomic, so a half-written cache is never read
    except OSError:
        pass  # caching is an optimisation; a read-only disk must not fail the case
    return pages


def booklet_prompt_text(pages):
    """The whole booklet with a clear marker before each page."""
    return "\n\n".join(f"=== PAGE {n} ===\n{text.strip()}" for n, text in sorted(pages.items()))


def evidence_items(pages, page_numbers, max_items=5, max_chars=MAX_ITEM_CHARS):
    """Evidence items for the given pages, in the given order.

    Each item is {"page": n, "text": page text}. A page longer than max_chars
    is split at whitespace into pieces of at most max_chars, all with the same
    page number. Unknown or repeated page numbers are skipped. At most
    max_items items are returned (only the first five are scored).
    """
    items, seen = [], set()
    for n in page_numbers:
        if n in seen or n not in pages:
            continue
        seen.add(n)
        for piece in _split(pages[n].strip(), max_chars):
            if len(items) == max_items:
                return items
            items.append({"page": n, "text": piece})
    return items


def _split(text, max_chars):
    """Split text into pieces of at most max_chars characters, at whitespace where possible."""
    pieces = []
    while len(text) > max_chars:
        cut = text.rfind(" ", 0, max_chars + 1)
        if cut <= 0:
            cut = max_chars
        pieces.append(text[:cut].strip())
        text = text[cut:].strip()
    if text:
        pieces.append(text)
    return pieces
