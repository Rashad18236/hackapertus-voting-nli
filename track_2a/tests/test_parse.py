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


def synthetic_pdf(pages):
    """A small PDF built in memory: one page per (text, two_font_programs) pair, each set in Helvetica with a font
    descriptor that names one embedded font program, or two (/FontFile and /FontFile3) when asked."""
    import io

    from pypdf import PdfWriter
    from pypdf.generic import ArrayObject, DecodedStreamObject, DictionaryObject, NameObject, NumberObject

    writer = PdfWriter()

    def stream(data):
        obj = DecodedStreamObject()
        obj.set_data(data)
        return writer._add_object(obj)

    for text, two_programs in pages:
        page = writer.add_blank_page(width=300, height=200)
        descriptor = DictionaryObject({
            NameObject("/Type"): NameObject("/FontDescriptor"), NameObject("/FontName"): NameObject("/Helvetica"),
            NameObject("/Flags"): NumberObject(32), NameObject("/FontBBox"): ArrayObject([NumberObject(0)] * 4),
            NameObject("/ItalicAngle"): NumberObject(0), NameObject("/Ascent"): NumberObject(718),
            NameObject("/Descent"): NumberObject(-207), NameObject("/CapHeight"): NumberObject(718),
            NameObject("/StemV"): NumberObject(88), NameObject("/FontFile"): stream(b"program")})
        if two_programs:
            descriptor[NameObject("/FontFile3")] = stream(b"program")
        font = DictionaryObject({
            NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"), NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
            NameObject("/FontDescriptor"): writer._add_object(descriptor)})
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
        page[NameObject("/Contents")] = stream(f"BT /F1 12 Tf 20 100 Td ({text}) Tj ET".encode())
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


class UnreadablePages(unittest.TestCase):
    """Session 11, parser coverage: a page pypdf refuses no longer makes the whole booklet unreadable."""

    def write(self, pages):
        folder = Path(tempfile.mkdtemp())
        path = folder / "synthetic.pdf"
        path.write_bytes(synthetic_pdf(pages))
        return path

    def test_two_font_programs_in_one_descriptor_are_read(self):
        # General cause: a font descriptor naming /FontFile and /FontFile3 (seen in 2016-2018 booklets).
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError

        path = self.write([("Erste Seite", False), ("Zweite Seite", True)])
        with self.assertRaises(PdfReadError):  # pypdf alone refuses the second page
            PdfReader(str(path)).pages[1].extract_text()
        self.assertEqual([t.strip() for t in parse.extract_pages(path)], ["Erste Seite", "Zweite Seite"])

    def test_a_page_that_still_fails_gets_empty_text(self):
        path = self.write([("Eins", False), ("Zwei", False), ("Drei", False)])
        from pypdf import PageObject

        original = PageObject.extract_text

        def flaky(page, *args, **kwargs):
            if "Zwei" in page.get_contents().get_data().decode():
                raise ValueError("broken page")
            return original(page, *args, **kwargs)

        with mock.patch.object(PageObject, "extract_text", flaky):
            texts = parse.extract_pages(path)
        self.assertEqual([t.strip() for t in texts], ["Eins", "", "Drei"])

    def test_readable_pages_are_read_as_before(self):
        from pypdf import PdfReader

        path = self.write([("Gleich", False)])
        self.assertEqual(parse.extract_pages(path), [PdfReader(str(path)).pages[0].extract_text()])
