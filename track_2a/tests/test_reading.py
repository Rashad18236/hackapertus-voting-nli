"""Tests for session 10's step 6 versions of task A (off by default): CS, the coupled answer schema, and SL, a second
look after a neutral answer that cites paragraphs (src/cli.py, src/nli.py)."""

import unittest
from unittest import mock

import numpy as np

from src import cli, llm, nli
from src.contexts import embed_e5_small, retrieval, section_route
from tests.test_booklet import booklet_pages
from tests.test_cli import OneVectorEmbedder
from tests.test_section_route import COUNCIL_CLAIM, case


def run(settings, answers):
    """The council claim through cli.predict; returns (response, raw, [(messages, schema) of every call])."""
    seen, answers = [], list(answers)

    def chat(messages, max_tokens=256, json_mode=False, json_schema=None):
        seen.append((messages, json_schema))
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


def sent_paragraphs(messages):
    user = messages[1]["content"]
    block = user.split("REFERENCE TEXT:\n", 1)[1].split("\n\nVOTE:", 1)[0]
    return [line.split("] ", 1)[1] for line in block.splitlines() if line.startswith("[")]


class CoupledSchema(unittest.TestCase):
    def test_off_by_default_and_the_plain_schema_is_sent(self):
        self.assertFalse(cli.Settings().coupled_schema_a)
        _, _, seen = run(cli.Settings(), ['{"paragraphs": [1], "label": 0}'])
        self.assertEqual(seen[0][1], nli.ANSWER_SCHEMA_A_PARAGRAPHS)

    def test_cs_sends_the_coupled_schema_with_the_same_prompt(self):
        _, raw, seen = run(cli.Settings(coupled_schema_a=True), ['{"paragraphs": [1], "label": 0}'])
        self.assertEqual(seen[0][1], nli.ANSWER_SCHEMA_A_COUPLED)
        self.assertEqual(raw["prompt_version"], "A-v4-section-route-L1")
        neutral, cited = nli.ANSWER_SCHEMA_A_COUPLED["anyOf"]
        self.assertEqual((neutral["properties"]["label"]["enum"], neutral["properties"]["paragraphs"]["maxItems"]), ([1], 0))
        self.assertEqual((cited["properties"]["label"]["enum"], cited["properties"]["paragraphs"]["minItems"]), ([0, 2], 1))


class SecondLookCited(unittest.TestCase):
    def test_off_by_default(self):
        self.assertFalse(cli.Settings().second_look_cited_a)
        resp, raw, seen = run(cli.Settings(second_look_a6=False), ['{"paragraphs": [2], "label": 1}'])
        self.assertEqual((len(seen), resp["label"], resp["evidence"]), (1, 1, []))
        self.assertNotIn("second_look_cited", raw)

    def test_neutral_with_a_citation_is_asked_again_with_only_the_cited_paragraphs(self):
        settings = cli.Settings(second_look_cited_a=True, second_look_a6=False)  # SL alone (A6 is on by default)
        resp, raw, seen = run(settings, ['{"paragraphs": [3, 1, 3, 99], "label": 1}', '{"paragraphs": [2], "label": 2}'])
        first, second = sent_paragraphs(seen[0][0]), sent_paragraphs(seen[1][0])
        self.assertEqual(second, [first[0], first[2]])  # paragraphs 1 and 3, in their order; 99 is not a paragraph
        self.assertEqual(seen[1][0][0]["content"], nli.PROMPTS_A["A-v4-second-look-cited"])
        self.assertEqual(resp["label"], 2)  # Apertus's second answer replaces the neutral one
        self.assertEqual(raw["second_look_cited"]["cited"], [1, 3])
        self.assertEqual(resp["metrics"]["input_tokens"], 100 + 200)
        self.assertTrue(resp["evidence"])
        self.assertTrue(all(item["text"] in "\n".join(t for _, t in section_route.route(
            booklet_pages(), case(COUNCIL_CLAIM)["vote"], COUNCIL_CLAIM)[1]) for item in resp["evidence"]))

    def test_a_neutral_second_answer_keeps_the_first(self):
        resp, raw, seen = run(cli.Settings(second_look_cited_a=True, second_look_a6=False),
                              ['{"paragraphs": [2], "label": 1}', '{"paragraphs": [], "label": 1}'])
        self.assertEqual((len(seen), resp["label"], resp["evidence"]), (2, 1, []))
        self.assertEqual(resp["metrics"]["input_tokens"], 300)  # both calls count

    def test_neutral_without_a_citation_gets_no_second_call(self):
        resp, raw, seen = run(cli.Settings(second_look_cited_a=True), ['{"paragraphs": [], "label": 1}'])
        self.assertEqual((len(seen), resp["label"]), (1, 1))


if __name__ == "__main__":
    unittest.main()
