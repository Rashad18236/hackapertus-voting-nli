"""Tests for answer parsing in src/nli.py."""

import unittest

from src import nli

REF = "Der Bundesrat empfiehlt,\ndie Initiative abzulehnen. Sie kostet 5 Mio. Franken."


class ParseLabel(unittest.TestCase):
    def test_clean_json(self):
        self.assertEqual(nli.parse_label('{"label": 0}'), (0, ""))

    def test_code_fence_and_prose(self):
        self.assertEqual(nli.parse_label('Here:\n```json\n{"label": "2"}\n```')[0], 2)

    def test_label_name_accepted(self):
        self.assertEqual(nli.parse_label('{"label": "Contradiction"}')[0], 2)

    def test_failures_never_guess(self):
        for answer in ("entailment", "", '{"label": 5}', '{"label": null}', '{"evidence": "x"}', "{broken"):
            label, reason = nli.parse_label(answer)
            self.assertIsNone(label, answer)
            self.assertTrue(reason, answer)


class ParseLabelAndPages(unittest.TestCase):
    def test_pages(self):
        self.assertEqual(nli.parse_label_and_pages('{"label": 0, "pages": [7, "3", true, "x"]}'), (0, [7, 3], ""))

    def test_missing_pages_is_not_a_failure(self):
        self.assertEqual(nli.parse_label_and_pages('{"label": 1}'), (1, [], ""))

    def test_failure_never_guesses(self):
        label, pages, reason = nli.parse_label_and_pages('{"pages": [3]}')
        self.assertIsNone(label)
        self.assertTrue(reason)


class FindVerbatim(unittest.TestCase):
    def test_exact(self):
        self.assertEqual(nli.find_verbatim("Sie kostet 5 Mio. Franken.", REF), "Sie kostet 5 Mio. Franken.")

    def test_whitespace_difference_returns_reference_text(self):
        self.assertEqual(nli.find_verbatim("Der Bundesrat empfiehlt, die Initiative abzulehnen.", REF),
                         "Der Bundesrat empfiehlt,\ndie Initiative abzulehnen.")

    def test_case_difference_returns_reference_text(self):
        self.assertEqual(nli.find_verbatim("Die Initiative abzulehnen.", REF), "die Initiative abzulehnen.")

    def test_paraphrase_is_none(self):
        self.assertIsNone(nli.find_verbatim("Le Conseil fédéral recommande le rejet.", REF))


if __name__ == "__main__":
    unittest.main()
