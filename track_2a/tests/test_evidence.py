"""Tests for src/evidence.py (task A evidence settings) with a fake embedder."""

import unittest
from unittest import mock

import numpy as np

from src import evidence
from src.contexts import retrieval

VOCAB = ["apple", "tax", "train", "vote"]


class WordCountEmbedder:
    def embed(self, texts):
        out = []
        for t in texts:
            w = t.lower().split()
            v = np.array([w.count(x) for x in VOCAB], dtype=float) + 1e-6
            out.append(v / np.linalg.norm(v))
        return np.array(out)


class Padding(unittest.TestCase):
    SHOWN = {1: "apple apple", 2: "tax tax", 3: "tax train", 4: "vote", 5: "train", 6: "apple tax", 7: "x"}

    def setUp(self):
        retrieval._page_cache.clear()
        retrieval._query_cache.clear()
        patcher = mock.patch.object(retrieval, "embedder", return_value=WordCountEmbedder())
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_cited_mode_returns_the_cited_items_unchanged(self):
        cited = [{"page": 4, "text": "vote"}]
        self.assertEqual(evidence.items("cited", cited, self.SHOWN, "tax"), cited)

    def test_padding_keeps_cited_first_then_most_similar_pages_up_to_five(self):
        cited = [{"page": 4, "text": "vote"}]
        got = evidence.items("cited-then-retrieved", cited, self.SHOWN, "tax")
        self.assertEqual(len(got), 5)
        self.assertEqual(got[0], cited[0])
        self.assertEqual(got[1]["page"], 2)  # "tax tax" is the most similar page
        self.assertEqual(len({g["page"] for g in got}), 5)  # no page twice

    def test_five_cited_items_leave_no_room(self):
        cited = [{"page": p, "text": self.SHOWN[p]} for p in (1, 2, 3, 4, 5)]
        self.assertEqual(evidence.items("cited-then-retrieved", cited, self.SHOWN, "tax"), cited)


if __name__ == "__main__":
    unittest.main()
