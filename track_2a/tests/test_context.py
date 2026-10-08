"""Tests for src/context.py (the registry of task A context variants) and the "full" variant."""

import unittest
from unittest import mock

from src import context, nli
from src.contexts import embed_e5_small


class Registry(unittest.TestCase):
    def test_every_variant_names_a_known_prompt(self):
        for mode in context.MODES:
            self.assertIn(context.prompt_version(mode), nli.PROMPTS_A, mode)

    def test_file_name_matches_variant_name(self):
        for name, module in context.VARIANTS.items():
            self.assertEqual(module.__name__, "src.contexts." + name.replace("-", "_"))

    def test_unknown_mode_is_an_error(self):
        with self.assertRaises(ValueError):
            context.select({1: "a"}, "v", "claim", "nonsense")


class Select(unittest.TestCase):
    """context.select: the prompt text plus the full pages it was taken from (evidence comes from these)."""

    PAGES = {3: "train timetable", 1: "intro", 2: "a long page about the tax and more"}

    def test_full_sends_every_page_in_order(self):
        text, shown = context.select(self.PAGES, "any vote", "claim", "full")
        self.assertEqual(list(shown), [1, 2, 3])
        self.assertTrue(text.startswith("=== PAGE 1 ===\nintro"))

    def test_embedding_mode_shows_chunks_but_keeps_whole_pages_for_evidence(self):
        with mock.patch.object(embed_e5_small, "select_chunks", return_value=[(2, "about the tax")]):
            text, shown = context.select(self.PAGES, "any vote", "tax", "embed-e5-small")
        self.assertEqual(text, "=== PAGE 2 ===\nabout the tax")
        self.assertEqual(shown, {2: self.PAGES[2]})


if __name__ == "__main__":
    unittest.main()
