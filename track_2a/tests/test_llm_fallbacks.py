"""src/llm.py's fallbacks (session 9, A1), against the fake model over HTTP (scripts/stub_llm.py).

(a) an endpoint that refuses response_format; (b) an endpoint that refuses the model name; both together;
the limit of three extra requests per run; tokens and time of every request counted.
"""

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import stub_llm  # noqa: E402
from src import llm  # noqa: E402

SCHEMA = {"type": "object", "properties": {"label": {"type": "integer"}}, "required": ["label"]}
MESSAGES = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]
GOOD = "swiss-ai/apertus-v1.5-8b"


class Fallbacks(unittest.TestCase):
    def start(self, model="swiss-ai/Apertus-v1.5-8B", **config):
        self.server, url = stub_llm.start(keep_payloads=True, **config)
        self.addCleanup(self.server.shutdown)
        env = {"BASE_URL": url, "API_KEY": "stub", "MODEL": model, "NO_PROXY": "127.0.0.1", "no_proxy": "127.0.0.1"}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        llm.reset_run_state()
        self.addCleanup(llm.reset_run_state)

    def calls(self):
        return self.server.config.calls

    def test_a_refused_response_format_is_dropped_for_the_rest_of_the_run(self):
        for status in (400, 422):
            with self.subTest(status=status):
                self.start(reject_response_format=status)
                first = llm.chat(MESSAGES, json_schema=SCHEMA)
                self.assertEqual(first.fallbacks, ["no response_format"])
                self.assertEqual(first.attempts, 2)
                self.assertEqual((first.input_tokens, first.output_tokens), (7 + 100, 10))  # both requests counted
                second = llm.chat(MESSAGES, json_schema=SCHEMA)
                self.assertEqual((second.fallbacks, second.attempts), ([], 1))
                self.assertEqual([c["kind"] for c in self.calls()], ["rejected_response_format", "ok", "ok"])
                self.assertNotIn("response_format", self.calls()[2]["payload"])
                self.server.shutdown()

    def test_b_a_refused_model_name_is_replaced_by_the_listed_apertus_8b(self):
        self.start(model="swiss-ai/Apertus-v1.5-8B-Instruct", models=["other/model", GOOD + "-thinking", GOOD])
        first = llm.chat(MESSAGES)
        self.assertEqual((first.fallbacks, first.attempts), ([f"model {GOOD}"], 2))
        second = llm.chat(MESSAGES)
        self.assertEqual((second.fallbacks, second.attempts), ([], 1))
        self.assertEqual([c["model"] for c in self.calls()], ["swiss-ai/Apertus-v1.5-8B-Instruct", GOOD, GOOD])
        self.assertEqual(self.server.config.models_requests, 1)  # /models read once

    def test_b_without_a_listed_apertus_8b_the_call_fails_and_models_is_not_read_again(self):
        self.start(model="wrong", models=["other/model"])
        with self.assertRaises(llm.LLMError):
            llm.chat(MESSAGES)
        with self.assertRaises(llm.LLMError):
            llm.chat(MESSAGES)
        self.assertEqual(self.server.config.models_requests, 1)

    def test_a_and_b_together_use_the_three_extra_requests(self):
        # The fake model refuses the model name with HTTP 400 and also refuses response_format.
        self.start(model="wrong", models=[GOOD], model_error_status=400, reject_response_format=400, delay=0.1)
        result = llm.chat(MESSAGES, json_schema=SCHEMA)
        self.assertEqual(result.fallbacks, ["no response_format", f"model {GOOD}"])
        self.assertEqual(result.attempts, 3)
        self.assertEqual(llm._run["extra_requests"], 3)
        self.assertGreaterEqual(result.elapsed_ms, 300)  # three requests of at least 0.1 s each, all in the time
        self.assertEqual([c["kind"] for c in self.calls()], ["unknown_model", "unknown_model", "ok"])
        self.assertNotIn("response_format", self.calls()[2]["payload"])
        self.assertEqual(self.calls()[2]["model"], GOOD)

    def test_no_more_than_three_extra_requests_per_run(self):
        self.start(model="wrong", models=[GOOD])
        llm._run["extra_requests"] = 2  # as if two had been used: (b) needs two more, so it is not tried
        with self.assertRaises(llm.LLMError):
            llm.chat(MESSAGES)
        self.assertEqual(self.server.config.models_requests, 0)
        self.assertEqual(len(self.calls()), 1)

    def test_normal_endpoint_uses_no_fallback(self):
        self.start()
        result = llm.chat(MESSAGES, json_schema=SCHEMA)
        self.assertEqual((result.fallbacks, result.attempts), ([], 1))
        self.assertIn("response_format", self.calls()[0]["payload"])
        self.assertEqual(llm._run["extra_requests"], 0)


class PickModel(unittest.TestCase):
    def test_apertus_v15_8b_ignoring_case_shortest_first(self):
        self.assertEqual(llm.pick_model(["a/b", "swiss-ai/Apertus-v1.5-8B-thinking", "swiss-ai/APERTUS-V1.5-8B"]),
                         "swiss-ai/APERTUS-V1.5-8B")
        self.assertIsNone(llm.pick_model(["swiss-ai/apertus-v1.5-70b", "swiss-ai/apertus-v1-8b",
                                          "swiss-ai/apertus-v1.5-18b"]))


class MinInterval(unittest.TestCase):
    def test_default_no_pause_and_bad_values_ignored(self):
        for value, expected in ((None, 0.0), ("1.5", 1.5), ("x", 0.0), ("-2", 0.0)):
            env = {} if value is None else {"LLM_MIN_INTERVAL": value}
            with mock.patch.dict(os.environ, env, clear=False):
                if value is None:
                    os.environ.pop("LLM_MIN_INTERVAL", None)
                self.assertEqual(llm.min_interval(), expected)


if __name__ == "__main__":
    unittest.main()
