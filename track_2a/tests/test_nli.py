"""Tests for answer parsing in src/nli.py."""

import unittest

from src import nli

REF = "Der Bundesrat empfiehlt,\ndie Initiative abzulehnen. Sie kostet 5 Mio. Franken."


class ParseAnswer(unittest.TestCase):
    def test_clean_json(self):
        p = nli.parse_answer('{"label": 0, "evidence": "Sie kostet 5 Mio. Franken."}', REF)
        self.assertEqual((p["label"], p["evidence"], p["parse_failure"]), (0, "Sie kostet 5 Mio. Franken.", False))

    def test_code_fence_and_prose(self):
        p = nli.parse_answer('Here:\n```json\n{"label": "2", "evidence": "Sie kostet 5 Mio. Franken."}\n```', REF)
        self.assertEqual(p["label"], 2)

    def test_whitespace_difference_returns_reference_text(self):
        p = nli.parse_answer('{"label": 0, "evidence": "Der Bundesrat empfiehlt, die Initiative abzulehnen."}', REF)
        self.assertEqual(p["evidence"], "Der Bundesrat empfiehlt,\ndie Initiative abzulehnen.")

    def test_case_difference_returns_reference_text(self):
        p = nli.parse_answer('{"label": 0, "evidence": "Die Initiative abzulehnen."}', REF)
        self.assertEqual(p["evidence"], "die Initiative abzulehnen.")

    def test_paraphrase_is_dropped_but_label_kept(self):
        p = nli.parse_answer('{"label": 2, "evidence": "Le Conseil fédéral recommande le rejet."}', REF)
        self.assertEqual((p["label"], p["evidence"], p["reason"]), (2, None, "evidence not verbatim"))

    def test_neutral_has_no_evidence(self):
        p = nli.parse_answer('{"label": 1, "evidence": "Sie kostet 5 Mio. Franken."}', REF)
        self.assertEqual((p["label"], p["evidence"]), (1, None))

    def test_failures_never_guess(self):
        for answer in ("entailment", "", '{"label": 5}', '{"label": null}', '{"evidence": "x"}', "{broken"):
            p = nli.parse_answer(answer, REF)
            self.assertTrue(p["parse_failure"], answer)
            self.assertIsNone(p["label"], answer)

    def test_label_name_accepted(self):
        self.assertEqual(nli.parse_answer('{"label": "Contradiction", "evidence": ""}', REF)["label"], 2)


if __name__ == "__main__":
    unittest.main()
