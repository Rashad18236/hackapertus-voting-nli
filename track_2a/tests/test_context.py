"""Tests for src/context.py with a fake embedder (no model files needed)."""

import unittest

import numpy as np

from src import context

VOCAB = ["apple", "tax", "train", "vote"]


class FakeEmbedder:
    """Word counts over VOCAB, normalised: texts sharing words are similar."""

    def __init__(self):
        self.calls = 0

    def embed(self, texts):
        self.calls += 1
        vectors = []
        for text in texts:
            words = text.lower().split()
            v = np.array([words.count(w) for w in VOCAB], dtype=float) + 1e-6
            vectors.append(v / np.linalg.norm(v))
        return np.array(vectors)


class Chunking(unittest.TestCase):
    def test_long_page_gives_several_chunks_with_its_page(self):
        chunks = context.chunk_pages({2: "word " * 500, 1: "short"}, max_chars=1000)
        self.assertEqual([n for n, _ in chunks], [1, 2, 2, 2])
        self.assertTrue(all(len(text) <= 1000 for _, text in chunks))

    def test_empty_page_gives_no_chunk(self):
        self.assertEqual(context.chunk_pages({1: "  ", 2: "text"}), [(2, "text")])


class Selection(unittest.TestCase):
    def setUp(self):
        context._chunk_cache.clear()

    def test_top_k_in_page_order(self):
        pages = {1: "apple apple", 2: "tax tax", 3: "train vote", 4: "tax train"}
        selected = context.select_chunks(pages, "tax", FakeEmbedder(), top_k=2)
        self.assertEqual(selected, [(2, "tax tax"), (4, "tax train")])

    def test_booklet_embedded_once(self):
        pages = {1: "apple", 2: "tax"}
        embedder = FakeEmbedder()
        context.select_chunks(pages, "tax", embedder)
        context.select_chunks(pages, "apple", embedder)
        self.assertEqual(embedder.calls, 3)  # chunks once, plus one query per claim

    def test_prompt_text_has_page_markers(self):
        text = context.excerpts_prompt_text([(3, "a"), (7, "b")])
        self.assertEqual(text, "=== PAGE 3 ===\na\n\n=== PAGE 7 ===\nb")


if __name__ == "__main__":
    unittest.main()
