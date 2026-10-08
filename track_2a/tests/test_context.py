"""Tests for src/context.py: page selection for task A, and embedding selection with a
fake embedder (no model files needed)."""

import unittest
from unittest import mock

import numpy as np

from src import context


class Full(unittest.TestCase):
    def test_full_returns_every_page_in_order(self):
        pages = {3: "c", 1: "a", 2: "b"}
        self.assertEqual(list(context.select_pages(pages, "any vote", "full")), [1, 2, 3])

    def test_unknown_mode_is_an_error(self):
        with self.assertRaises(ValueError):
            context.select_pages({1: "a"}, "v", "nonsense")



class VoteSection(unittest.TestCase):
    # A miniature two-ballot booklet: front matter, a section on hunting (pages 3-7),
    # a section on fighter jets (pages 8-10). Page 5 is an "arguments" page whose
    # header does not name the ballot; gap filling must keep it.
    PAGES = {
        1: "Votation populaire Modification de la loi sur la chasse Arrêté fédéral relatif aux avions de combat",
        2: "Sommaire et informations pratiques",
        3: "3 Premier objet : loi sur la chasse Modification de la loi sur la chasse Contexte et projet",
        4: "4 Premier objet : loi sur la chasse Les loups et la régulation des espèces protégées",
        5: "5 Arguments du comité référendaire",
        6: "6 Premier objet : loi sur la chasse Arguments du Conseil fédéral",
        7: "7 Texte soumis au vote",
        8: "8 Second objet : avions de combat Arrêté fédéral relatif aux avions de combat",
        9: "9 Second objet : avions de combat Coûts et calendrier",
        10: "10 Arguments du comité",
    }
    VOTE = "Modification de la loi sur la chasse"

    def test_selects_the_ballot_section(self):
        sel = context.vote_section(self.PAGES, self.VOTE)
        self.assertTrue({3, 4, 5, 6, 7} <= set(sel))      # the whole section, page 5 by gap filling
        self.assertNotIn(9, sel)                         # the other ballot's detail pages stay out

    def test_select_pages_keeps_original_page_numbers(self):
        sel = context.select_pages(self.PAGES, self.VOTE, "vote-section")
        self.assertEqual(sel[4], self.PAGES[4])
        self.assertEqual(list(sel), sorted(sel))

    def test_no_match_falls_back_to_all_pages(self):
        self.assertEqual(context.vote_section(self.PAGES, "Völlig andere Vorlage zum Thema Velowege"), sorted(self.PAGES))
        self.assertEqual(context.vote_section(self.PAGES, "   "), sorted(self.PAGES))

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


class Select(unittest.TestCase):
    """context.select: the prompt text plus the full pages it was taken from (evidence comes from these)."""

    PAGES = {1: "intro", 2: "a long page about the tax and more", 3: "train timetable"}

    def test_page_modes_send_whole_pages(self):
        text, shown = context.select(self.PAGES, "any vote", "claim", "full")
        self.assertEqual(shown, self.PAGES)
        self.assertTrue(text.startswith("=== PAGE 1 ===\nintro"))

    def test_embedding_mode_shows_chunks_but_keeps_whole_pages_for_evidence(self):
        with mock.patch.object(context, "select_chunks", return_value=[(2, "about the tax")]):
            text, shown = context.select(self.PAGES, "any vote", "tax", "embed-e5-small")
        self.assertEqual(text, "=== PAGE 2 ===\nabout the tax")
        self.assertEqual(shown, {2: self.PAGES[2]})


if __name__ == "__main__":
    unittest.main()
