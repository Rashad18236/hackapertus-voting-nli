"""Tests for src/contexts/retrieval.py (the session-4 embedding variants) with a fake embedder."""

import unittest
from unittest import mock

import numpy as np

from src import context
from src.contexts import retrieval

VOCAB = ["apple", "tax", "train", "vote"]


class WordCountEmbedder:
    """Word counts over VOCAB, normalised: texts sharing words are similar. Counts its calls."""

    def __init__(self):
        self.texts = []

    def embed(self, texts):
        self.texts += texts
        vectors = []
        for text in texts:
            words = text.lower().split()
            v = np.array([words.count(w) for w in VOCAB], dtype=float) + 1e-6
            vectors.append(v / np.linalg.norm(v))
        return np.array(vectors)


class Selection(unittest.TestCase):
    PAGES = {1: "apple apple", 2: "tax tax", 3: "train vote", 4: "tax train", 5: "apple vote"}

    def setUp(self):
        retrieval._page_cache.clear()
        retrieval._query_cache.clear()
        self.embedder = WordCountEmbedder()
        patcher = mock.patch.object(retrieval, "embedder", return_value=self.embedder)
        patcher.start()
        self.addCleanup(patcher.stop)

    def select(self, **kw):
        settings = dict(model="granite-97m-r2", scope="booklet", k=2, neighbours=0, cross_rule="same")
        settings.update(kw)
        return retrieval.select(self.PAGES, "vote", "tax", **settings)

    def test_top_k_in_page_order_with_whole_pages_for_evidence(self):
        text, shown = self.select()
        self.assertEqual(text, "=== PAGE 2 ===\ntax tax\n\n=== PAGE 4 ===\ntax train")
        self.assertEqual(shown, {2: "tax tax", 4: "tax train"})

    def test_neighbours_add_the_chunks_around_each_hit(self):
        _, shown = self.select(neighbours=1)
        self.assertEqual(sorted(shown), [1, 2, 3, 4, 5])

    def test_cross_language_double_k(self):
        _, same = self.select(cross_rule="double", cross_language=False)
        _, cross = self.select(cross_rule="double", cross_language=True)
        self.assertEqual((len(same), len(cross)), (2, 4))

    def test_cross_language_whole_section(self):
        with mock.patch.object(retrieval.vote_section, "section_pages", return_value=[3, 4]):
            text, shown = self.select(cross_rule="section", cross_language=True)
        self.assertEqual(shown, {3: "train vote", 4: "tax train"})
        self.assertTrue(text.startswith("=== PAGE 3 ===\ntrain vote"))

    def test_section_scope_embeds_only_section_pages_once(self):
        with mock.patch.object(retrieval.vote_section, "section_pages", return_value=[2, 3]):
            self.select(scope="section")
            self.select(scope="section")
        passages = [t for t in self.embedder.texts if t != "tax"]
        self.assertEqual(sorted(passages), ["tax tax", "train vote"])  # pages 2 and 3, each embedded once

    def test_result_does_not_depend_on_what_ran_before(self):
        fresh = self.select()
        retrieval._page_cache.clear()
        retrieval._query_cache.clear()
        with mock.patch.object(retrieval.vote_section, "section_pages", return_value=[5]):
            self.select(scope="section")  # fills the cache with page 5 first
        self.assertEqual(self.select(), fresh)

    def test_prefixes_follow_each_model_card(self):
        retrieval.page_chunks("e5-small", "tax tax")
        retrieval.page_chunks("granite-97m-r2", "apple")
        self.assertIn("passage: tax tax", self.embedder.texts)
        self.assertIn("apple", self.embedder.texts)

    def test_unknown_cross_rule_is_an_error(self):
        with self.assertRaises(ValueError):
            self.select(cross_rule="sometimes")


class Registry(unittest.TestCase):
    def test_new_variants_are_registered_with_fixed_settings(self):
        for name, scope, model in (("vote-section-embed-e5-small", "section", "e5-small"),
                                   ("embed-granite-97m-r2", "booklet", "granite-97m-r2"),
                                   ("vote-section-embed-granite-97m-r2", "section", "granite-97m-r2")):
            settings = context.VARIANTS[name].SETTINGS
            self.assertEqual((settings["scope"], settings["model"], settings["k"]), (scope, model, 8))


if __name__ == "__main__":
    unittest.main()
