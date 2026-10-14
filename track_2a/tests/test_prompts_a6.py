"""Tests for session 13's step 1 (off by default): the rewritten routed prompts A1-A5 (`--prompt-a`, src/nli.py
ROUTED_VERSIONS) and A6, a second look after a neutral answer that cites paragraphs (`--second-look-a6`)."""

import json
import unittest
from unittest import mock

import numpy as np

from src import cli, llm, nli
from src.contexts import embed_e5_small, retrieval, section_route
from tests.test_booklet import booklet_pages
from tests.test_cli import OneVectorEmbedder
from tests.test_reading import sent_paragraphs
from tests.test_section_route import COUNCIL_CLAIM, case

NEW_VERSIONS = ["A-v6-says", "A-v6-residual", "A-v6-mismatch", "A-v6-opposite", "A-v6-words"]


def run(settings, answers):
    """The council claim through cli.predict; returns (response, raw, [(messages, max_tokens, schema) per call])."""
    seen, answers = [], list(answers)

    def chat(messages, max_tokens=256, json_mode=False, json_schema=None):
        seen.append((messages, max_tokens, json_schema))
        return llm.LLMResult(text=answers.pop(0), input_tokens=100 * len(seen), output_tokens=5, elapsed_ms=1)
    with mock.patch.object(cli.parse, "load_pages", return_value=booklet_pages()), \
         mock.patch.object(cli.Path, "is_file", return_value=True), \
         mock.patch.object(llm, "chat", chat), \
         mock.patch.object(embed_e5_small, "select_chunks", return_value=[(14, "chunk")]), \
         mock.patch.object(retrieval, "embedder", return_value=OneVectorEmbedder()), \
         mock.patch.object(retrieval, "query_vector", return_value=np.ones(4) / 2.0):
        section_route._vectors.clear()
        resp, status, raw = cli.predict(case(COUNCIL_CLAIM), ".", settings)
    return resp, raw, seen


class Prompts(unittest.TestCase):
    def test_today_is_unchanged_by_default(self):
        self.assertEqual((cli.Settings().prompt_a, cli.Settings().second_look_a6), ("", False))
        _, raw, seen = run(cli.Settings(), ['{"paragraphs": [1], "label": 0}'])
        self.assertEqual(raw["prompt_version"], "A-v4-section-route-L1")
        self.assertEqual(seen[0][0][0]["content"], nli.PROMPTS_A["A-v4-section-route-L1"])
        self.assertEqual((seen[0][1], seen[0][2]), (128, nli.ANSWER_SCHEMA_A_PARAGRAPHS))

    def test_every_version_starts_with_today_s_first_paragraph(self):
        for version in NEW_VERSIONS:
            self.assertTrue(nli.PROMPTS_A[version].startswith(nli.HEADER_A + "\n\n"), version)
        self.assertTrue(nli.HEADER_A.endswith("never outside knowledge."))

    def test_schemas_list_the_fields_in_the_order_the_text_asks_for_them(self):
        expected = {"A-v6-says": ["claim_says", "text_says", "paragraphs", "label"],
                    "A-v6-residual": ["paragraphs", "label"],
                    "A-v6-mismatch": ["paragraphs", "mismatch", "label"],
                    "A-v6-opposite": ["paragraphs", "opposite_claim", "text_states"],
                    "A-v6-words": ["paragraphs", "label"]}
        for version, fields in expected.items():
            schema = nli.ROUTED_VERSIONS[version]["schema"]
            self.assertEqual(list(schema["properties"]), fields, version)
            self.assertEqual(schema["required"], fields, version)
            self.assertFalse(schema["additionalProperties"], version)
            example = json.loads(nli.PROMPTS_A[version].rsplit("\n", 1)[1])
            self.assertEqual(list(example), fields, version)  # the prompt's example has the same order

    def test_the_version_s_prompt_schema_and_budget_are_sent(self):
        for version in NEW_VERSIONS:
            _, raw, seen = run(cli.Settings(prompt_a=version), ['{"paragraphs": [1], "label": 0}'])
            self.assertEqual(raw["prompt_version"], version)
            self.assertEqual(seen[0][0][0]["content"], nli.PROMPTS_A[version])
            self.assertEqual(seen[0][1], nli.ROUTED_VERSIONS[version]["max_tokens"])
            self.assertEqual(seen[0][2], nli.ROUTED_VERSIONS[version]["schema"])

    def test_labels_are_read_from_the_version_s_own_field(self):
        cases = [("A-v6-says", '{"claim_says": "x", "text_says": "nothing", "paragraphs": [], "label": 1}', 1, []),
                 ("A-v6-says", '{"claim_says": "x", "text_says": "nothing", "paragraphs": [2], "label": 2}', 2, [2]),
                 ("A-v6-mismatch", '{"paragraphs": [3], "mismatch": "none", "label": 2}', 2, [3]),
                 ("A-v6-opposite", '{"paragraphs": [1, 2], "opposite_claim": "y", "text_states": "opposite"}', 2, [1, 2]),
                 ("A-v6-opposite", '{"paragraphs": [], "opposite_claim": "y", "text_states": "neither"}', 1, []),
                 ("A-v6-opposite", '{"paragraphs": [4], "opposite_claim": "y", "text_states": "claim"}', 0, [4]),
                 ("A-v6-words", '{"paragraphs": [1], "label": "contradicted"}', 2, [1]),
                 ("A-v6-words", '{"paragraphs": [1], "label": "supported"}', 0, [1]),
                 ("A-v6-words", '{"paragraphs": [], "label": "not_covered"}', 1, [])]
        for version, answer, label, numbers in cases:
            self.assertEqual(nli.parse_routed_answer(answer, version), (label, numbers, ""), (version, answer))
        # Python never checks the label against another field: a "mismatch" of none with label 2 stays 2 (above).

    def test_unreadable_answers_are_unreadable(self):
        self.assertIsNone(nli.parse_routed_answer('{"paragraphs": [1], "label": 0}', "A-v6-opposite")[0])
        self.assertIsNone(nli.parse_routed_answer('{"paragraphs": [1], "label": 2}', "A-v6-words")[0])
        self.assertIsNone(nli.parse_routed_answer("no json", "A-v6-words")[0])
        resp, raw, _ = run(cli.Settings(prompt_a="A-v6-words"), ['{"paragraphs": [1], "label": 7}'])
        self.assertEqual(resp["label"], cli.FALLBACK_LABEL)
        self.assertIn("parse_reason", raw)

    def test_a_word_label_gets_today_s_evidence(self):
        resp, _, _ = run(cli.Settings(prompt_a="A-v6-words"), ['{"paragraphs": [2], "label": "contradicted"}'])
        today, _, _ = run(cli.Settings(), ['{"paragraphs": [2], "label": 2}'])
        self.assertEqual((resp["label"], resp["evidence"]), (2, today["evidence"]))
        self.assertTrue(resp["evidence"])


class SecondLookA6(unittest.TestCase):
    def test_off_by_default_no_second_call(self):
        resp, raw, seen = run(cli.Settings(), ['{"paragraphs": [2], "label": 1}'])
        self.assertEqual((len(seen), resp["label"]), (1, 1))
        self.assertNotIn("second_look_a6", raw)

    def test_neutral_with_a_citation_gets_one_second_look_whose_finding_is_final(self):
        for finding, label in (("same", 0), ("different", 2), ("nothing", 1)):
            resp, raw, seen = run(cli.Settings(second_look_a6=True),
                                  ['{"paragraphs": [2], "label": 1}', json.dumps({"finding": finding})])
            self.assertEqual(len(seen), 2)
            self.assertEqual(resp["label"], label, finding)
            self.assertEqual(seen[1][0][0]["content"], nli.PROMPTS_A["A-v6-second-look"])
            self.assertEqual(seen[1][2], nli.ANSWER_SCHEMA_A6)
            self.assertEqual(resp["metrics"]["input_tokens"], 100 + 200)  # both calls count
            self.assertEqual(bool(resp["evidence"]), label in (0, 2))

    def test_the_excerpt_is_the_cited_paragraph_and_its_neighbours_numbered_as_first_shown(self):
        _, raw, seen = run(cli.Settings(second_look_a6=True),
                           ['{"paragraphs": [2], "label": 1}', '{"finding": "different"}'])
        first = sent_paragraphs(seen[0][0])
        user = seen[1][0][1]["content"]
        self.assertTrue(user.startswith("EXCERPT:\n[1] ") and "\n\nCLAIM:\n" + COUNCIL_CLAIM in user)
        self.assertNotIn("VOTE:", user)
        excerpt = user.split("EXCERPT:\n", 1)[1].split("\n\nCLAIM:", 1)[0].splitlines()
        shown = [n for n in (1, 2, 3) if n <= len(first)]
        self.assertEqual(excerpt, [f"[{n}] {first[n - 1]}" for n in shown])
        self.assertEqual(raw["second_look_a6"]["cited"], [2])

    def test_evidence_comes_from_the_first_answer_s_paragraphs(self):
        resp, _, _ = run(cli.Settings(second_look_a6=True),
                         ['{"paragraphs": [2], "label": 1}', '{"finding": "different"}'])
        today, _, _ = run(cli.Settings(), ['{"paragraphs": [2], "label": 2}'])
        self.assertEqual(resp["evidence"], today["evidence"])

    def test_no_second_look_after_0_or_2_or_a_neutral_without_citation(self):
        for first in ('{"paragraphs": [2], "label": 0}', '{"paragraphs": [2], "label": 2}',
                      '{"paragraphs": [], "label": 1}', '{"paragraphs": [99], "label": 1}'):
            resp, raw, seen = run(cli.Settings(second_look_a6=True), [first, '{"finding": "same"}'])
            self.assertEqual(len(seen), 1, first)

    def test_an_unreadable_or_failed_second_look_keeps_the_first_answer(self):
        resp, raw, seen = run(cli.Settings(second_look_a6=True), ['{"paragraphs": [2], "label": 1}', "garbage"])
        self.assertEqual((len(seen), resp["label"], resp["metrics"]["input_tokens"]), (2, 1, 300))
        self.assertIn("parse_reason", raw["second_look_a6"])

    def test_it_works_on_top_of_a_new_prompt(self):
        resp, _, seen = run(cli.Settings(prompt_a="A-v6-opposite", second_look_a6=True),
                            ['{"paragraphs": [1], "opposite_claim": "y", "text_states": "neither"}',
                             '{"finding": "same"}'])
        self.assertEqual((len(seen), resp["label"]), (2, 0))

    def test_excerpt_budget(self):
        paragraphs = ["a" * 900, "b" * 900, "c" * 900, "d" * 900]
        self.assertEqual(cli.a6_excerpt(paragraphs, [2]), [(1, "a" * 900), (2, "b" * 900)])  # 3rd would pass 2,000
        self.assertEqual(cli.a6_excerpt(paragraphs, [3, 1]), [(1, "a" * 900), (3, "c" * 900)])
        self.assertEqual(cli.a6_excerpt(["x" * 2500, "y"], [1]), [(1, "x" * 2000)])
        self.assertEqual(cli.a6_excerpt(["x", "y"], [0, 5]), [])
        self.assertEqual(cli.a6_excerpt(["x", "y", "z"], [2]), [(1, "x"), (2, "y"), (3, "z")])

    def test_never_in_task_b(self):
        seen = []

        def chat(messages, max_tokens=256, json_mode=False, json_schema=None):
            seen.append(messages)
            return llm.LLMResult(text='{"label": 1}', input_tokens=10, output_tokens=2, elapsed_ms=1)
        b_case = {"id": "b", "vote": "V", "claim": {"text": "c", "language": "de"},
                  "reference": {"text": "r", "language": "de"}}
        with mock.patch.object(llm, "chat", chat):
            resp, _, _ = cli.predict(b_case, ".", cli.Settings(second_look_a6=True))
        self.assertEqual((len(seen), resp["label"]), (1, 1))


if __name__ == "__main__":
    unittest.main()
