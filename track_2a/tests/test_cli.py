"""Tests for src/cli.py: one valid response per request, no matter what fails.

The model call is replaced by a fake, so these tests need no endpoint or key.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src import cli, llm
from src.contexts import embed_e5_small, retrieval


class OneVectorEmbedder:
    """Stands in for an embedding model: every text gets the same unit vector."""

    def embed(self, texts):
        import numpy as np
        return np.ones((len(texts), 4)) / 2.0


def b_case(case_id):
    return {"id": case_id, "vote": "v", "claim": {"text": "c", "language": "de"},
            "reference": {"text": "r", "language": "fr"}}


def a_case(case_id):
    return {"id": case_id, "vote": "v", "claim": {"text": "c", "language": "de"},
            "booklet": {"path": "booklets/x.pdf", "language": "it"}}


def fake_chat(answers, seen=None):
    """Return a chat() replacement that gives the next answer each call (an exception is raised).

    If seen is a list, the messages of every call are appended to it.
    """
    answers = list(answers)

    def chat(messages, max_tokens=256, json_mode=False, json_schema=None):
        if seen is not None:
            seen.append(messages)
        answer = answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return llm.LLMResult(text=answer, input_tokens=50, output_tokens=5, elapsed_ms=10)
    return chat


def run_cli(lines, answers, extra_args=(), seen=None):
    with tempfile.TemporaryDirectory() as tmp:
        inp, out = Path(tmp) / "cases.jsonl", Path(tmp) / "out" / "predictions.jsonl"
        inp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        with mock.patch.object(llm, "chat", fake_chat(answers, seen)), \
             mock.patch("sys.argv", ["cli", "--input", str(inp), "--output", str(out), *extra_args]), \
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

    def test_task_a_evidence_from_pages(self):
        pages = {1: "intro", 2: "word " * 1500, 3: "details"}
        lines = [json.dumps(a_case("a-entail")), json.dumps(a_case("a-neutral")), json.dumps(a_case("a-nopages"))]
        answers = ['{"label": 0, "pages": [2, 99]}', '{"label": 1, "pages": [3]}', '{"label": 2, "pages": []}']
        with mock.patch.object(cli.parse, "load_pages", return_value=pages), \
             mock.patch.object(cli.Path, "is_file", return_value=True):
            code, out = run_cli(lines, answers, ["--context-a", "full", "--evidence-a", "cited"])  # every page shown
            _, pieces = run_cli(lines, answers, ["--context-a", "full"])  # default evidence: cited-pieces
        by_id = {p["id"]: p for p in out}
        self.assertEqual(code, 0)
        ev = by_id["a-entail"]["evidence"]
        self.assertEqual([e["page"] for e in ev], [2, 2])  # long page split, unknown page 99 skipped
        self.assertTrue(all(len(e["text"]) <= 5000 for e in ev))
        self.assertEqual(by_id["a-neutral"]["evidence"], [])   # neutral: no evidence
        self.assertEqual(by_id["a-nopages"]["label"], 2)       # label kept, evidence empty
        self.assertEqual(by_id["a-nopages"]["evidence"], [])
        ev = {p["id"]: p for p in pieces}["a-entail"]["evidence"]
        self.assertEqual([e["page"] for e in ev], [2] * 5)   # 7,500 characters: 1,000-character pieces, at most five
        self.assertTrue(all(len(e["text"]) <= 1000 for e in ev))

    def test_every_context_mode_sends_the_answer_schema(self):
        for mode in cli.context.MODES:
            if mode == "closed-book":  # shows no page; tested in ClosedBook
                continue
            with self.subTest(mode=mode):
                seen = {}

                def chat(messages, max_tokens=256, json_mode=False, json_schema=None):
                    seen["schema"], seen["max_tokens"] = json_schema, max_tokens
                    return llm.LLMResult(text='{"pages": [1], "label": 0}', input_tokens=9, output_tokens=3,
                                         elapsed_ms=1)
                with mock.patch.object(llm, "chat", chat), \
                     mock.patch.object(cli.parse, "load_pages", return_value={1: "page one"}), \
                     mock.patch.object(cli.Path, "is_file", return_value=True), \
                     mock.patch.object(embed_e5_small, "select_chunks", return_value=[(1, "page one")]), \
                     mock.patch.object(retrieval, "embedder", return_value=OneVectorEmbedder()):
                    resp, status, raw = cli.predict(a_case("s"), ".", cli.Settings(context_a=mode))
                self.assertEqual(seen["schema"], cli.nli.ANSWER_SCHEMA_A)  # the default for every mode
                self.assertEqual(seen["max_tokens"], 128)
                self.assertEqual((resp["label"], status, raw["pages_sent"]), (0, "ok", 1))
                self.assertEqual(resp["evidence"], [{"page": 1, "text": "page one"}])

    def test_embedding_context_sends_only_selected_chunks(self):
        pages = {1: "intro", 2: "details on the tax", 3: "other ballot"}
        seen = []
        with mock.patch.object(cli.parse, "load_pages", return_value=pages), \
             mock.patch.object(cli.Path, "is_file", return_value=True), \
             mock.patch.object(embed_e5_small, "select_chunks", return_value=[(2, "details on the tax")]):
            code, out = run_cli([json.dumps(a_case("a"))], ['{"pages": [2], "label": 0}'],
                                ["--context-a", "embed-e5-small"], seen)
        self.assertEqual(code, 0)
        system, user = seen[0][0]["content"], seen[0][1]["content"]
        self.assertIn("only excerpts of the booklet", system)
        self.assertIn("=== PAGE 2 ===\ndetails on the tax", user)
        self.assertNotIn("other ballot", user)
        self.assertEqual(out[0]["evidence"], [{"page": 2, "text": "details on the tax"}])  # whole page text

    def test_context_selection_failure_falls_back(self):
        with mock.patch.object(cli.parse, "load_pages", return_value={1: "text"}), \
             mock.patch.object(cli.Path, "is_file", return_value=True), \
             mock.patch.object(embed_e5_small, "select_chunks", side_effect=FileNotFoundError("model.onnx")):
            code, out = run_cli([json.dumps(a_case("a"))], [], ["--context-a", "embed-e5-small"])
        self.assertEqual(code, 0)
        self.assertEqual((out[0]["label"], out[0]["evidence"]), (1, []))

    def test_input_equals_output_is_refused(self):
        with mock.patch("sys.argv", ["cli", "--input", "same.jsonl", "--output", "same.jsonl"]):
            with self.assertRaises(SystemExit):
                cli.main()


class ClosedBook(unittest.TestCase):
    """Session 9, E2 (information only): no booklet text, the label kept, no evidence."""

    def test_closed_book_sends_only_vote_and_claim(self):
        seen = {}

        def chat(messages, max_tokens=256, json_mode=False, json_schema=None):
            seen["messages"], seen["schema"] = messages, json_schema
            return llm.LLMResult(text='{"pages": [], "label": 2}', input_tokens=9, output_tokens=3, elapsed_ms=1)
        with mock.patch.object(llm, "chat", chat), \
             mock.patch.object(cli.parse, "load_pages", return_value={1: "page one"}), \
             mock.patch.object(cli.Path, "is_file", return_value=True):
            resp, status, raw = cli.predict(a_case("s"), ".", cli.Settings(context_a="closed-book"))
        self.assertEqual(seen["messages"][1]["content"], "VOTE: v\n\nCLAIM:\nc")
        self.assertEqual(seen["messages"][0]["content"], cli.nli.PROMPTS_A["A-v0-closed-book"])
        self.assertEqual(seen["schema"], cli.nli.ANSWER_SCHEMA_A)
        self.assertEqual((resp["label"], resp["evidence"], raw["pages_sent"]), (2, [], 0))


class TaskBSettings(unittest.TestCase):
    def test_task_b_schema_and_max_tokens(self):
        for settings, expected in ((cli.Settings(), (None, 32)),
                                   (cli.Settings(schema_b=True, max_tokens_b=10), (cli.nli.ANSWER_SCHEMA_B, 10))):
            seen = {}

            def chat(messages, max_tokens=256, json_mode=False, json_schema=None):
                seen["schema"], seen["max_tokens"] = json_schema, max_tokens
                return llm.LLMResult(text='{"label": 2}', input_tokens=9, output_tokens=3, elapsed_ms=1)
            with mock.patch.object(llm, "chat", chat):
                resp, status, _ = cli.predict(b_case("b"), ".", settings)
            self.assertEqual((seen["schema"], seen["max_tokens"]), expected)
            self.assertEqual((resp["label"], status, resp["evidence"]), (2, "ok", []))

    def test_task_b_raw_records_retries_429s_and_endpoint(self):
        ident = {"model": "m", "headers": {"server": "s"}}
        results = [llm.LLMResult(text='{"label": 0}', input_tokens=9, output_tokens=3, elapsed_ms=1, attempts=2,
                                 http_429=1, endpoint=ident),
                   llm.LLMError("HTTP 429", attempts=3, http_429=3, endpoint=ident)]
        for result, label in zip(results, (0, cli.FALLBACK_LABEL)):
            def chat(*args, **kwargs):
                if isinstance(result, Exception):
                    raise result
                return result
            with mock.patch.object(llm, "chat", chat):
                resp, _, raw = cli.predict(b_case("b"), ".", cli.Settings())
            self.assertEqual(resp["label"], label)
            self.assertEqual((raw["attempts"], raw["http_429"], raw["endpoint"]),
                             (result.attempts, result.http_429, ident))

    def test_task_b_schema_allows_only_the_label(self):
        schema = cli.nli.ANSWER_SCHEMA_B
        self.assertEqual(schema["required"], ["label"])
        self.assertEqual(schema["properties"], {"label": {"type": "integer", "enum": [0, 1, 2]}})
        self.assertFalse(schema["additionalProperties"])


class Defaults(unittest.TestCase):
    def test_task_a_default_is_section_route_with_cited_pieces_evidence(self):
        settings = cli.Settings()
        self.assertEqual((settings.context_a, settings.evidence_a, settings.schema_a), ("section-route", "cited-pieces", True))
        self.assertEqual(cli.context.fallback(settings.context_a), "embed-e5-small")


class ReadLines(unittest.TestCase):
    """Session 8 (P2, P3): the input is decoded line by line; a byte order mark is ignored."""

    def test_bom_line_endings_and_a_bad_byte(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cases.jsonl"
            # \xe2\x80\xa8 is U+2028 (line separator): str.splitlines() would cut the line there, bytes do not.
            path.write_bytes(b'\xef\xbb\xbf{"id": "a"}\r\n{"id": "b\xff"}\n\n{"id": "c\xe2\x80\xa8d"}\r')
            lines = cli.read_lines(path)
        self.assertEqual(lines, ['{"id": "a"}', '{"id": "b\ufffd"}', "", '{"id": "c\u2028d"}'])


if __name__ == "__main__":
    unittest.main()
