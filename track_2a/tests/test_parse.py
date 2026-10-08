"""Tests for src/parse.py (no real PDF needed: extraction is faked)."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src import parse


class EvidenceItems(unittest.TestCase):
    PAGES = {1: "short page", 2: "word " * 1500, 3: "third"}  # page 2 is 7,500 characters

    def test_order_limits_and_splitting(self):
        items = parse.evidence_items(self.PAGES, [3, 2, 99, 3, 1])
        # 3 first; 2 is split into two pieces (<= 5,000 chars each); 99 unknown; 3 repeated; then 1
        self.assertEqual([i["page"] for i in items], [3, 2, 2, 1])
        self.assertTrue(all(len(i["text"]) <= 5000 for i in items))
        self.assertEqual(sum(len(i["text"].split()) for i in items if i["page"] == 2), 1500)

    def test_at_most_five_items(self):
        pages = {n: f"page {n}" for n in range(1, 10)}
        self.assertEqual(len(parse.evidence_items(pages, list(range(1, 10)))), 5)

    def test_prompt_text_has_page_markers(self):
        text = parse.booklet_prompt_text({2: "b", 1: "a"})
        self.assertEqual(text, "=== PAGE 1 ===\na\n\n=== PAGE 2 ===\nb")


class Cache(unittest.TestCase):
    def test_cache_is_keyed_by_content_not_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            a, b, c = tmp / "a.pdf", tmp / "b.pdf", tmp / "c.pdf"
            a.write_bytes(b"same content")
            b.write_bytes(b"same content")
            c.write_bytes(b"other content")
            with mock.patch.object(parse, "extract_pages", return_value=["p1", "p2"]) as extract:
                first = parse.load_pages(a, cache_dir=tmp / "cache")
                second = parse.load_pages(b, cache_dir=tmp / "cache")  # same bytes: from cache
                parse.load_pages(c, cache_dir=tmp / "cache")           # new bytes: parsed again
            self.assertEqual(first, {1: "p1", 2: "p2"})
            self.assertEqual(second, first)
            self.assertEqual(extract.call_count, 2)

    def test_unwritable_cache_does_not_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "a.pdf"
            pdf.write_bytes(b"x")
            with mock.patch.object(parse, "extract_pages", return_value=["p1"]):
                self.assertEqual(parse.load_pages(pdf, cache_dir="/proc/not-writable"), {1: "p1"})


if __name__ == "__main__":
    unittest.main()
