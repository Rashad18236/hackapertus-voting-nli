"""Tests for session 15's task B changes (off by default): B1 retried with its format fixed (v7-same-ballot-f, step 3)
and B6, a second look on the ballot after an answer 2 (`--second-look-b6`, step 4)."""

import json
import unittest
from unittest import mock

from src import cli, llm, nli

CASE = {"id": "x-B", "vote": "Bundesgesetz V", "claim": {"text": "Der Bund zahlt 40 Millionen.", "language": "de"},
        "reference": {"text": "Bundesgesetz V\n\nDer Bund zahlt 40 Millionen Franken pro Jahr.", "language": "de"}}


def run(settings, answers, fail_second=False):
    """CASE through cli.predict; returns (response, raw, [(messages, max_tokens, schema) per call])."""
    seen, answers = [], list(answers)

    def chat(messages, max_tokens=256, json_mode=False, json_schema=None):
        seen.append((messages, max_tokens, json_schema))
        if fail_second and len(seen) == 2:
            raise llm.LLMError("down", attempts=2)
        return llm.LLMResult(text=answers.pop(0), input_tokens=10 * len(seen), output_tokens=3, elapsed_ms=1)
    with mock.patch.object(llm, "chat", chat):
        resp, status, raw = cli.predict(CASE, ".", settings)
    return resp, raw, seen


class B1Fixed(unittest.TestCase):
    def test_only_the_format_changes(self):
        b1, f = nli.PROMPTS_B["v7-same-ballot"], nli.PROMPTS_B["v7-same-ballot-f"]
        self.assertEqual(f, b1.replace("at most 8 words", "at most 6 words"))
        spec = nli.B_VERSIONS["v7-same-ballot-f"]
        self.assertEqual(spec["max_tokens"], 64)
        props = spec["schema"]["properties"]
        self.assertEqual((props["passage_ballot"]["maxLength"], props["claim_ballot"]["maxLength"]), (40, 40))
        self.assertEqual(list(props), list(nli.B_VERSIONS["v7-same-ballot"]["schema"]["properties"]))

    def test_sent_with_its_schema_and_budget_and_label_read_as_given(self):
        resp, raw, seen = run(cli.Settings(prompt_b="v7-same-ballot-f"),
                              ['{"passage_ballot": "a", "claim_ballot": "b", "same_ballot": false, "label": 2}'])
        self.assertEqual((seen[0][0][0]["content"], seen[0][1]), (nli.PROMPTS_B["v7-same-ballot-f"], 64))
        self.assertEqual(seen[0][2], nli.B_VERSIONS["v7-same-ballot-f"]["schema"])
        self.assertEqual(resp["label"], 2)  # Apertus's label, never checked against same_ballot


class B6(unittest.TestCase):
    def test_off_by_default(self):
        self.assertFalse(cli.Settings().second_look_b6)
        resp, raw, seen = run(cli.Settings(), ['{"label": 2}'])
        self.assertEqual((len(seen), resp["label"]), (1, 2))
        self.assertNotIn("second_look_b6", raw)

    def test_a_contradiction_gets_one_look_at_the_ballot(self):
        for same, label in ((False, 1), (True, 2)):
            resp, raw, seen = run(cli.Settings(second_look_b6=True),
                                  ['{"label": 2}', json.dumps({"same_ballot": same})])
            self.assertEqual((len(seen), resp["label"]), (2, label))
            messages, budget, schema = seen[1]
            self.assertEqual(messages, nli.build_messages_b6("Bundesgesetz V", "Bundesgesetz V", CASE["claim"]["text"]))
            self.assertEqual(len(messages), 1)
            self.assertIn(nli.B6_QUESTION, messages[0]["content"])
            self.assertNotIn("40 Millionen Franken", messages[0]["content"])  # the reference's body is not sent
            self.assertEqual((budget, schema), (cli.B6_MAX_TOKENS, nli.ANSWER_SCHEMA_B6))
            self.assertEqual(resp["metrics"]["input_tokens"], 10 + 20)  # both calls count
            self.assertEqual(raw["second_look_b6"]["version"], nli.B6_VERSION)

    def test_only_after_a_contradiction(self):
        for first in ('{"label": 0}', '{"label": 1}', 'not json'):
            resp, raw, seen = run(cli.Settings(second_look_b6=True), [first])
            self.assertEqual(len(seen), 1, first)
            self.assertNotIn("second_look_b6", raw)

    def test_unreadable_or_failed_second_look_keeps_the_first_answer(self):
        resp, raw, seen = run(cli.Settings(second_look_b6=True), ['{"label": 2}', '{"same_ballot": "no"}'])
        self.assertEqual((len(seen), resp["label"]), (2, 2))
        self.assertIn("parse_reason", raw["second_look_b6"])
        resp, raw, seen = run(cli.Settings(second_look_b6=True), ['{"label": 2}'], fail_second=True)
        self.assertEqual((len(seen), resp["label"]), (2, 2))
        self.assertIn("error", raw["second_look_b6"])

    def test_parse_same_ballot(self):
        self.assertEqual(nli.parse_same_ballot('{"same_ballot": false}'), (False, ""))
        self.assertEqual(nli.parse_same_ballot('{"same_ballot": true}')[0], True)
        self.assertIsNone(nli.parse_same_ballot('{"same_ballot": 0}')[0])
        self.assertIsNone(nli.parse_same_ballot("")[0])


if __name__ == "__main__":
    unittest.main()
