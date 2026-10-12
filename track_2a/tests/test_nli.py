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


class LabelFromProse(unittest.TestCase):
    def test_explicit_statement(self):
        answer = "The booklet supports the claim. Therefore, the label is 0 (entailment)."
        self.assertEqual(nli.parse_label_and_pages(answer), (0, [], ""))

    def test_conflicting_statements_are_a_failure(self):
        answer = "If not, the label is 1 (neutral). Here the booklet supports it, so the label is 0."
        self.assertEqual(nli.parse_label_and_pages(answer)[0], None)

    def test_no_statement_is_a_failure(self):
        for answer in ("The booklet deals with the subject of the claim at all (1).", "entailment", "<|inner_prefix|>"):
            self.assertIsNone(nli.parse_label_and_pages(answer)[0], answer)

    def test_json_still_preferred(self):
        self.assertEqual(nli.parse_label_and_pages('{"pages": [3], "label": 2} the label is 0'), (2, [3], ""))


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



class V5Min(unittest.TestCase):
    def test_v5_min_keeps_the_three_rules_and_has_no_format_instructions(self):
        prompt = nli.PROMPTS_B["v5-min"]
        self.assertIn("different ballot or subject", prompt)
        self.assertIn("cannot both be true", prompt)
        self.assertIn("Missing information is 1, never 2", prompt)
        self.assertNotIn("JSON", prompt)  # strict JSON (--schema-b) fixes the format
        self.assertEqual(nli.DEFAULT_PROMPT_B, "v3-topic-first")  # prepared, not the default

    def test_v5_ballot_is_v5_min_plus_one_sentence(self):
        ballot, minimal = nli.PROMPTS_B["v5-ballot"], nli.PROMPTS_B["v5-min"]
        self.assertEqual(ballot.replace(" " + nli.BALLOT_SENTENCE, "", 1), minimal)
        self.assertEqual(ballot.count(nli.BALLOT_SENTENCE), 1)
        self.assertIn("Use only the reference text. " + nli.BALLOT_SENTENCE + "\n0:", ballot)


if __name__ == "__main__":
    unittest.main()


class ShortPrompts(unittest.TestCase):  # session 10, step 5
    def test_short_prompts_keep_the_rules_and_the_readme_label_names(self):
        from src import nli
        a, b = nli.PROMPTS_A["A-v5-short"], nli.PROMPTS_B["v6-short"]
        self.assertIn(nli.L1_SENTENCE, a)
        for prompt in (a, b):
            for name in ("0 (Entailment)", "1 (Unrelated / Neutral)", "2 (Contradiction)"):
                self.assertIn(name, prompt)
            self.assertIn("Missing information is never a contradiction.", prompt)
        self.assertIn('{"paragraphs": [2, 5], "label": 0}', a)
        self.assertLess(len(a), len(nli.PROMPTS_A["A-v4-section-route-L1"]))
        self.assertLess(len(b), len(nli.PROMPTS_B["v3-topic-first"]))

    def test_settings_pick_the_short_prompt_for_routed_cases(self):
        from src import cli
        self.assertEqual(cli.paragraph_prompt_version(cli.Settings()), "A-v4-section-route-L1")
        self.assertEqual(cli.paragraph_prompt_version(cli.Settings(short_prompt_a=True)), "A-v5-short")
