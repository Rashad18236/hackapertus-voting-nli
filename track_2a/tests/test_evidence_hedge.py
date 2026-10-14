"""Tests for H (session 13, step 3; off by default): src/evidence.py hedge() and its path in src/cli.py."""

import unittest

from src import cli, evidence
from tests.test_prompts_a6 import run

PARTS = [(4, "Letzter Absatz auf Seite 4."), (5, "Erster Absatz auf Seite 5."), (5, "Zweiter Absatz auf Seite 5."),
         (6, "Erster Absatz auf Seite 6.")]
PAGES = {4: "Anderes.\nLetzter Absatz auf Seite 4.", 5: "Erster Absatz auf Seite 5.\nZweiter Absatz auf Seite 5.",
         6: "Erster Absatz auf Seite 6."}


class Hedge(unittest.TestCase):
    def test_previous_page_paragraph_then_whole_page_after_today_s_items(self):
        today = [{"page": 5, "text": "Erster Absatz auf Seite 5."}]
        items = evidence.hedge(today, PARTS, [2], PAGES)
        self.assertEqual(items, today + [{"page": 4, "text": "Letzter Absatz auf Seite 4."},
                                         {"page": 5, "text": PAGES[5]}])

    def test_a_paragraph_that_does_not_open_its_page_gets_only_the_whole_page(self):
        today = [{"page": 5, "text": "Zweiter Absatz auf Seite 5."}]
        self.assertEqual(evidence.hedge(today, PARTS, [3], PAGES), today + [{"page": 5, "text": PAGES[5]}])

    def test_the_part_s_first_paragraph_has_no_earlier_paragraph(self):
        today = [{"page": 4, "text": "Letzter Absatz auf Seite 4."}]
        self.assertEqual(evidence.hedge(today, PARTS, [1], PAGES), today + [{"page": 4, "text": PAGES[4].strip()}])

    def test_at_most_five_no_repeats_and_today_first(self):
        today = [{"page": 5, "text": f"t{i}"} for i in range(4)]
        items = evidence.hedge(today, PARTS, [2], PAGES)
        self.assertEqual(items[:4], today)
        self.assertEqual(len(items), 5)
        full = [{"page": 5, "text": f"t{i}"} for i in range(5)]
        self.assertEqual(evidence.hedge(full, PARTS, [2], PAGES), full)
        same = [{"page": 6, "text": PAGES[6]}]
        self.assertEqual(evidence.hedge(same, PARTS, [4], PAGES),  # page 6's whole text repeats the item: left out
                         same + [{"page": 5, "text": "Zweiter Absatz auf Seite 5."}])

    def test_every_item_lies_on_its_page_and_unknown_numbers_add_nothing(self):
        for item in evidence.hedge([], PARTS, [2], PAGES):
            self.assertIn(item["text"], PAGES[item["page"]])
        self.assertEqual(evidence.hedge([], PARTS, [9, 0], PAGES), [])
        self.assertEqual(evidence.hedge([], PARTS, [2], None), [{"page": 4, "text": "Letzter Absatz auf Seite 4."}])


class HedgeInCli(unittest.TestCase):
    def test_on_by_default_and_labels_and_requests_unchanged(self):
        self.assertTrue(cli.Settings().evidence_hedge_a)
        today, _, seen_today = run(cli.Settings(evidence_hedge_a=False), ['{"paragraphs": [2], "label": 2}'])
        hedged, _, seen_h = run(cli.Settings(evidence_hedge_a=True), ['{"paragraphs": [2], "label": 2}'])
        self.assertEqual(seen_today, seen_h)  # same request
        self.assertEqual(hedged["label"], today["label"])
        self.assertEqual(hedged["evidence"][:len(today["evidence"])], today["evidence"])
        self.assertGreaterEqual(len(hedged["evidence"]), len(today["evidence"]))
        self.assertLessEqual(len(hedged["evidence"]), 5)

    def test_neutral_answers_get_no_evidence(self):
        hedged, _, _ = run(cli.Settings(evidence_hedge_a=True),  # A6 (on by default) looks again and keeps neutral
                           ['{"paragraphs": [2], "label": 1}', '{"finding": "nothing"}'])
        self.assertEqual(hedged["evidence"], [])


if __name__ == "__main__":
    unittest.main()
