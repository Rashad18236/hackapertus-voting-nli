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


class CitedPieces(unittest.TestCase):
    def test_pieces_are_taken_in_turn_across_cited_pages_at_most_five(self):
        shown = {3: "a" * 999 + " " + "b" * 999 + " " + "c" * 10, 7: "x" * 999 + " " + "y" * 5, 9: "z"}
        got = evidence.items("cited-pieces", [], shown, "claim", cited_pages=[7, 3, 9])
        self.assertEqual([(g["page"], g["text"][0]) for g in got], [(7, "x"), (3, "a"), (9, "z"), (7, "y"), (3, "b")])

    def test_only_cited_pages_that_were_shown_once_each(self):
        shown = {1: "one", 2: "two", 3: "three"}
        got = evidence.items("cited-pieces", [], shown, "claim", cited_pages=[2, 5, 2])
        self.assertEqual(got, [{"page": 2, "text": "two"}])

    def test_every_piece_is_at_most_1000_characters_and_verbatim(self):
        text = " ".join(f"word{i}" for i in range(600))
        got = evidence.pieces({4: text}, [4])
        self.assertTrue(all(len(g["text"]) <= 1000 and g["text"] in text for g in got))
        self.assertEqual(len(got), 5)


if __name__ == "__main__":
    unittest.main()
