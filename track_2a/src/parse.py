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
import threading
from collections.abc import Mapping
from pathlib import Path

from src import memo

CACHE_DIR = Path(os.environ.get("BOOKLET_CACHE_DIR", "/tmp/booklet-cache"))
MAX_ITEM_CHARS = 5000  # official limit for one evidence item (about one page)


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def extract_pages(pdf_path):
    """Return a list of page texts; element i is PDF page i + 1. No caching.

    Session 11: a page whose text pypdf refuses to extract no longer fails the whole booklet. First the page's
    font descriptors are repaired (_repair_fonts) and the page is read again; if it still fails, the page gets
    empty text, like a page without a text layer. Pages that pypdf reads are read exactly as before.
    """
    from pypdf import PdfReader  # imported on first use (session 10): the first task B request need not wait for it

    from src import timing

    with timing.phase("pdf_read"):
        return _extract(PdfReader, pdf_path)


def _extract(PdfReader, pdf_path):
    reader = PdfReader(str(pdf_path))
    return [_page_text(page) for page in reader.pages]


def _page_text(page):
    """One page's text: as pypdf extracts it; after _repair_fonts if pypdf refuses the page; else empty text."""
    try:
        return page.extract_text() or ""
    except Exception:
        pass
    try:
        _repair_fonts(page.get("/Resources"), set())
        return page.extract_text() or ""
    except Exception:
        return ""


_FONT_FILES = ("/FontFile", "/FontFile2", "/FontFile3")


def _repair_fonts(resources, seen):
    """Keep one embedded font program per font descriptor (session 11, parser coverage).

    General cause: some booklets (2016-2018) have font descriptors that name two embedded programs of the same
    font (/FontFile and /FontFile3). pypdf 6 refuses such a page ("More than one /FontFile found"), which made
    every page and so the whole booklet unreadable. The text does not depend on which program is kept (both
    tried on such a booklet: identical text); the first one present is kept. Only the reader's copy in memory
    changes, never the file. Fonts inside form XObjects are repaired too.
    """
    from pypdf.generic import NameObject

    if resources is None:
        return
    resources = resources.get_object()
    for font in (resources.get("/Font") or {}).values():
        font = font.get_object()
        for item in [font] + [d.get_object() for d in (font.get("/DescendantFonts") or [])]:
            descriptor = item.get("/FontDescriptor")
            if descriptor is None:
                continue
            descriptor = descriptor.get_object()
            present = [k for k in _FONT_FILES if k in descriptor]
            for extra in present[1:]:
                del descriptor[NameObject(extra)]
    for xobject in (resources.get("/XObject") or {}).values():
        xobject = xobject.get_object()
        if id(xobject) not in seen:
            seen.add(id(xobject))
            _repair_fonts(xobject.get("/Resources"), seen)


_pages = {}  # (cache folder, booklet SHA-256) -> {page: text}; session 10: also kept in memory


LAZY_PAGES = False  # session 11, step 4 (off): read a page only when it is first asked for (Pages)


def load_pages(pdf_path, cache_dir=CACHE_DIR):
    """Return {page number (1-based): text}, using the cache when possible. A booklet is parsed once per run,
    also when two threads ask for it at the same time (src/memo.py); every caller gets its own dict.
    With LAZY_PAGES and no cache file: a Pages mapping that reads each page when it is first asked for (shared
    by the callers of this process; nothing in src/ changes a booklet's pages)."""
    key = _sha256(pdf_path)
    if LAZY_PAGES and not (Path(cache_dir) / f"{key}.json").exists():
        return memo.once(_pages, (str(cache_dir), key, "lazy"), lambda: Pages(pdf_path, key))
    return dict(memo.once(_pages, (str(cache_dir), key), lambda: _load_pages(pdf_path, key, cache_dir)))


class Pages(Mapping):
    """{page number: text} of a booklet, each page read from the PDF when first asked for (session 11, step 4).

    The text of a page is exactly what extract_pages gives for it (the same reading and repair, page by page).
    key: the PDF file's SHA-256, so that caches of parsed booklets need not read every page to name the booklet.
    Asking whether a page exists, or how many pages there are, reads no page."""

    def __init__(self, pdf_path, key):
        from pypdf import PdfReader

        self.key = key
        self._reader = PdfReader(str(pdf_path))
        self._count = len(self._reader.pages)
        self._texts = {}
        self._lock = threading.Lock()

    def __getitem__(self, number):
        if not (isinstance(number, int) and 1 <= number <= self._count):
            raise KeyError(number)
        with self._lock:
            if number not in self._texts:
                from src import timing
                with timing.phase("pdf_read"):
                    self._texts[number] = _page_text(self._reader.pages[number - 1])
            return self._texts[number]

    def __contains__(self, number):
        return isinstance(number, int) and 1 <= number <= self._count

    def __iter__(self):
        return iter(range(1, self._count + 1))

    def __len__(self):
        return self._count


def _load_pages(pdf_path, key, cache_dir):
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
