"""Tests for session 9's task A label-error versions (phase D, off by default): L1 (one more sentence in the routed
prompt) and L2 (a second look after a neutral answer), in src/cli.py and src/nli.py."""

import unittest
from unittest import mock

import numpy as np

from src import cli, llm, nli
from src.contexts import embed_e5_small, retrieval, section_route
from tests.test_booklet import booklet_pages
from tests.test_cli import OneVectorEmbedder
from tests.test_section_route import COUNCIL_CLAIM, case


def run(settings, answers):
    """Run the council claim through cli.predict; returns (response, raw, the messages of every call)."""
    seen, answers = [], list(answers)

    def chat(messages, max_tokens=256, json_mode=False, json_schema=None):
        seen.append(messages)
        return llm.LLMResult(text=answers.pop(0), input_tokens=100 * len(seen), output_tokens=5, elapsed_ms=1)
    with mock.patch.object(cli.parse, "load_pages", return_value=booklet_pages()), \
         mock.patch.object(cli.Path, "is_file", return_value=True), \
         mock.patch.object(llm, "chat", chat), \
         mock.patch.object(embed_e5_small, "select_chunks", return_value=[(14, "chunk")]), \
         mock.patch.object(retrieval, "embedder", return_value=OneVectorEmbedder()), \
         mock.patch.object(retrieval, "query_vector", return_value=np.ones(4) / 2.0):  # every similarity is 1.0
        section_route._vectors.clear()
        resp, status, raw = cli.predict(case(COUNCIL_CLAIM), ".", settings)
    return resp, raw, seen


class L1(unittest.TestCase):
    def test_without_l1_the_prompt_is_the_session_6_one(self):
        _, raw, seen = run(cli.Settings(label_rule_a=False), ['{"paragraphs": [1], "label": 0}'])
        self.assertEqual(raw["prompt_version"], "A-v4-section-route")
        self.assertEqual(seen[0][0]["content"], nli.PROMPTS_A["A-v4-section-route"])
        self.assertNotIn(nli.L1_SENTENCE, seen[0][0]["content"])

    def test_l1_is_the_default_since_session_9(self):
        self.assertTrue(cli.Settings().label_rule_a)

    def test_l1_adds_the_sentence_after_the_rule(self):
        _, raw, seen = run(cli.Settings(), ['{"paragraphs": [1], "label": 2}'])
        self.assertEqual(raw["prompt_version"], "A-v4-section-route-L1")
        system = seen[0][0]["content"]
        self.assertIn(nli._RULE_B + "\n" + nli.L1_SENTENCE + "\n\nFirst give", system)
        self.assertEqual(system.replace("\n" + nli.L1_SENTENCE, ""), nli.PROMPTS_A["A-v4-section-route"])


class L2(unittest.TestCase):
    def test_off_by_default(self):
        self.assertFalse(cli.Settings().second_look_a)
        resp, raw, seen = run(cli.Settings(), ['{"paragraphs": [], "label": 1}'])
        self.assertEqual((len(seen), resp["label"]), (1, 1))
        self.assertNotIn("second_look", raw)

    def test_neutral_above_threshold_gets_a_second_call_that_can_replace_it(self):
        resp, raw, seen = run(cli.Settings(second_look_a=True),
                              ['{"paragraphs": [], "label": 1}', '{"paragraphs": [2], "label": 2}'])
        self.assertEqual(len(seen), 2)
        self.assertEqual(seen[1][0]["content"], nli.PROMPTS_A["A-v4-second-look"])
        self.assertEqual(seen[1][1]["content"].count("\n["), 3)  # three numbered paragraphs
        self.assertIn("\n[3] ", seen[1][1]["content"])
        self.assertNotIn("\n[4] ", seen[1][1]["content"])
        self.assertEqual(resp["label"], 2)
        self.assertEqual(resp["metrics"]["input_tokens"], 100 + 200)  # both calls counted
        self.assertEqual(resp["metrics"]["output_tokens"], 10)
        shown = [tuple(p) for p in raw["second_look"]["paragraphs"]]
        self.assertEqual(resp["evidence"][0]["page"], shown[1][0])  # paragraph 2 of the three shown
        self.assertTrue(raw["second_look"]["asked"])

    def test_second_neutral_keeps_neutral_but_counts_tokens(self):
        resp, raw, seen = run(cli.Settings(second_look_a=True),
                              ['{"paragraphs": [], "label": 1}', '{"paragraphs": [], "label": 1}'])
        self.assertEqual((len(seen), resp["label"], resp["evidence"]), (2, 1, []))
        self.assertEqual(resp["metrics"]["input_tokens"], 300)

    def test_below_threshold_no_second_call(self):
        resp, raw, seen = run(cli.Settings(second_look_a=True, second_look_threshold=1.5),
                              ['{"paragraphs": [], "label": 1}'])
        self.assertEqual((len(seen), resp["label"]), (1, 1))
        self.assertEqual(raw["second_look"], {"similarity": 1.0, "asked": False})

    def test_no_second_call_after_entailment_or_contradiction(self):
        for answer in ('{"paragraphs": [1], "label": 0}', '{"paragraphs": [1], "label": 2}'):
            with self.subTest(answer=answer):
                resp, raw, seen = run(cli.Settings(second_look_a=True), [answer])
                self.assertEqual(len(seen), 1)
                self.assertNotIn("second_look", raw)


class SectionTopK(unittest.TestCase):
    """Session 9, E1 (information only): a routed case cut to its k most similar paragraphs."""

    def test_top_k_cuts_the_routed_paragraphs(self):
        _, full_raw, _ = run(cli.Settings(), ['{"paragraphs": [1], "label": 0}'])
        self.assertGreater(len(full_raw["paragraphs_sent"]), 1)
        resp, raw, seen = run(cli.Settings(section_top_k_a=1), ['{"paragraphs": [1], "label": 0}'])
        self.assertEqual(len(raw["paragraphs_sent"]), 1)
        self.assertNotIn("\n[2] ", seen[0][1]["content"])
        self.assertEqual(resp["label"], 0)


if __name__ == "__main__":
    unittest.main()
