"""Tests for src/cli.py: one valid response per request, no matter what fails.

The model call is replaced by a fake, so these tests need no endpoint or key.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src import cli, llm


def b_case(case_id):
    return {"id": case_id, "vote": "v", "claim": {"text": "c", "language": "de"},
            "reference": {"text": "r", "language": "fr"}}


def a_case(case_id):
    return {"id": case_id, "vote": "v", "claim": {"text": "c", "language": "de"},
            "booklet": {"path": "booklets/x.pdf", "language": "it"}}


def fake_chat(answers):
    """Return a chat() replacement that gives the next answer each call (an exception is raised)."""
    answers = list(answers)

    def chat(messages, max_tokens=256):
        answer = answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return llm.LLMResult(text=answer, input_tokens=50, output_tokens=5, elapsed_ms=10)
    return chat


def run_cli(lines, answers):
    with tempfile.TemporaryDirectory() as tmp:
        inp, out = Path(tmp) / "cases.jsonl", Path(tmp) / "out" / "predictions.jsonl"
        inp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        with mock.patch.object(llm, "chat", fake_chat(answers)), \
             mock.patch("sys.argv", ["cli", "--input", str(inp), "--output", str(out)]), \
             mock.patch.object(cli.env, "load_env_file"):
            code = cli.main()
        return code, [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]


class NeverDropACase(unittest.TestCase):
    def test_mixed_tasks_and_failures(self):
        lines = [
            json.dumps(b_case("ok")),
            json.dumps(a_case("doc")),                      # task A placeholder, no model call
            json.dumps(b_case("garbled")),                  # unparseable answer
            json.dumps(b_case("timeout")),                  # model call fails
            json.dumps({**a_case("both"), "reference": {"text": "r", "language": "fr"}}),  # two sources
            json.dumps({"id": "nosource", "claim": {"text": "c", "language": "de"}}),
            "{not json",                                    # no id: cannot be answered
        ]
        answers = ['{"label": 2}', "I think it is true.", llm.LLMError("HTTP 504")]
        code, out = run_cli(lines, answers)
        self.assertEqual(code, 0)
        by_id = {p["id"]: p for p in out}
        self.assertEqual(sorted(by_id), ["both", "doc", "garbled", "nosource", "ok", "timeout"])
        self.assertEqual((by_id["ok"]["label"], by_id["ok"]["label_name"]), (2, "contradiction"))
        self.assertEqual(by_id["ok"]["metrics"]["input_tokens"], 50)
        for case_id in ("doc", "garbled", "timeout", "both", "nosource"):
            self.assertEqual((by_id[case_id]["label"], by_id[case_id]["label_name"]), (1, "neutral"), case_id)
        for p in out:
            self.assertEqual(p["evidence"], [])
            self.assertEqual(sorted(p["metrics"]), ["inference_time_ms", "input_tokens", "output_tokens"])

    def test_input_equals_output_is_refused(self):
        with mock.patch("sys.argv", ["cli", "--input", "same.jsonl", "--output", "same.jsonl"]):
            with self.assertRaises(SystemExit):
                cli.main()


if __name__ == "__main__":
    unittest.main()
