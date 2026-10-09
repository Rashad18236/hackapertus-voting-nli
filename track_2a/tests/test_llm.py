"""Tests for the retry rule in src/llm.py (no network: requests.post is faked)."""

import unittest
from unittest import mock

import requests

from src import llm

ENV = {"BASE_URL": "http://example.invalid", "API_KEY": "k"}


class FakeResponse:
    def __init__(self, status, body=None, headers=None):
        self.status_code = status
        self._body = body
        self.text = "error page" if body is None else str(body)
        self.headers = headers or {}

    def json(self):
        if self._body is None:
            raise ValueError("not JSON")
        return self._body


def ok(tokens_in=100, tokens_out=5):
    return FakeResponse(200, {"choices": [{"message": {"content": '{"label": 1}'}}],
                              "usage": {"prompt_tokens": tokens_in, "completion_tokens": tokens_out}})


def run(responses, sleeps=None):
    calls = list(responses)

    def post(*args, **kwargs):
        item = calls.pop(0)
        if isinstance(item, Exception):
            raise item
        return item
    with mock.patch.dict("os.environ", ENV, clear=False), \
         mock.patch.object(requests, "post", side_effect=post) as fake, \
         mock.patch.object(llm.time, "sleep", side_effect=(sleeps.append if sleeps is not None else None)):
        try:
            return llm.chat([{"role": "user", "content": "x"}]), fake.call_count
        except llm.LLMError as e:
            return e, fake.call_count


class JsonMode(unittest.TestCase):
    def test_response_format_only_when_asked(self):
        for flag, expected in ((False, None), (True, {"type": "json_object"})):
            with mock.patch.dict("os.environ", ENV, clear=False), \
                 mock.patch.object(requests, "post", return_value=ok()) as fake:
                llm.chat([{"role": "user", "content": "x"}], json_mode=flag)
            self.assertEqual(fake.call_args.kwargs["json"].get("response_format"), expected)


class JsonSchema(unittest.TestCase):
    def test_schema_payload_and_precedence(self):
        schema = {"type": "object"}
        with mock.patch.dict("os.environ", ENV, clear=False), \
             mock.patch.object(requests, "post", return_value=ok()) as fake:
            llm.chat([{"role": "user", "content": "x"}], json_mode=True, json_schema=schema)
        fmt = fake.call_args.kwargs["json"]["response_format"]
        self.assertEqual(fmt["type"], "json_schema")
        self.assertEqual(fmt["json_schema"]["schema"], schema)
        self.assertTrue(fmt["json_schema"]["strict"])


class Retry(unittest.TestCase):
    def test_success_needs_one_call(self):
        result, calls = run([ok()])
        self.assertEqual((calls, result.attempts, result.input_tokens), (1, 1, 100))

    def test_5xx_is_retried_once(self):
        result, calls = run([FakeResponse(504), ok()])
        self.assertEqual((calls, result.attempts), (2, 2))

    def test_timeout_is_retried_once(self):
        result, calls = run([requests.Timeout(), ok()])
        self.assertEqual((calls, result.attempts), (2, 2))

    def test_second_failure_raises(self):
        result, calls = run([FakeResponse(502), FakeResponse(504)])
        self.assertIsInstance(result, llm.LLMError)
        self.assertEqual(calls, 2)

    def test_4xx_and_connection_errors_are_not_retried(self):
        result, calls = run([FakeResponse(401, {"error": "bad key"})])
        self.assertIsInstance(result, llm.LLMError)
        self.assertEqual(calls, 1)
        result, calls = run([requests.ConnectionError("http://secret-url")])
        self.assertIsInstance(result, llm.LLMError)
        self.assertNotIn("secret-url", str(result))
        self.assertEqual(calls, 1)

    def test_tokens_of_a_failed_attempt_are_counted(self):
        failed_with_usage = FakeResponse(500, {"usage": {"prompt_tokens": 70, "completion_tokens": 0}})
        result, calls = run([failed_with_usage, ok(100, 5)])
        self.assertEqual((result.input_tokens, result.output_tokens), (170, 5))


class RateLimit(unittest.TestCase):
    """HTTP 429: up to two retries; Retry-After if present, else 2 s then 4 s; never more than 10 s."""

    def test_429_is_retried_twice_with_2_then_4_seconds(self):
        sleeps = []
        result, calls = run([FakeResponse(429), FakeResponse(429), ok()], sleeps)
        self.assertEqual((calls, result.attempts, sleeps), (3, 3, [2, 4]))

    def test_third_429_raises(self):
        result, calls = run([FakeResponse(429)] * 3)
        self.assertIsInstance(result, llm.LLMError)
        self.assertIn("429", str(result))
        self.assertEqual(calls, 3)

    def test_retry_after_is_used_and_capped_at_10_seconds(self):
        sleeps = []
        run([FakeResponse(429, headers={"Retry-After": "3"}), FakeResponse(429, headers={"Retry-After": "60"}), ok()],
            sleeps)
        self.assertEqual(sleeps, [3.0, 10.0])

    def test_waiting_time_counts_in_elapsed_ms(self):
        clock = iter([100.0, 107.5])  # perf_counter at start and end: 7.5 s, waits included
        with mock.patch.object(llm.time, "perf_counter", side_effect=lambda: next(clock)):
            result, _ = run([FakeResponse(429), FakeResponse(429), ok()])
        self.assertEqual(result.elapsed_ms, 7500)

    def test_tokens_of_rate_limited_attempts_are_counted(self):
        limited = FakeResponse(429, {"usage": {"prompt_tokens": 40, "completion_tokens": 0}})
        result, _ = run([limited, ok(100, 5)])
        self.assertEqual((result.input_tokens, result.output_tokens), (140, 5))

    def test_5xx_and_429_retries_are_counted_separately(self):
        result, calls = run([FakeResponse(503), FakeResponse(429), FakeResponse(429), ok()])
        self.assertEqual((calls, result.attempts), (4, 4))


if __name__ == "__main__":
    unittest.main()
