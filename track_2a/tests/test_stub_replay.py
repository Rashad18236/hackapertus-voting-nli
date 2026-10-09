"""The fake model's request hash and replay mode (scripts/stub_llm.py), used by scripts/prompt_snapshot.py."""

import json
import sys
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import stub_llm  # noqa: E402


def post(url, payload):
    request = urllib.request.Request(url + "/chat/completions", data=json.dumps(payload).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read())["choices"][0]["message"]["content"]


class Replay(unittest.TestCase):
    def test_hash_ignores_key_order_and_spacing_but_not_content(self):
        a = {"model": "m", "messages": [{"role": "user", "content": "x"}], "max_tokens": 5}
        b = {"max_tokens": 5, "messages": [{"content": "x", "role": "user"}], "model": "m"}
        self.assertEqual(stub_llm.request_hash(a), stub_llm.request_hash(b))
        self.assertNotEqual(stub_llm.request_hash(a), stub_llm.request_hash({**a, "max_tokens": 6}))

    def test_saved_answer_for_a_known_request_fixed_answer_otherwise(self):
        known = {"model": "m", "messages": [{"role": "user", "content": "known"}], "temperature": 0}
        other = {"model": "m", "messages": [{"role": "user", "content": "other"}], "temperature": 0}
        server, url = stub_llm.start(replay={stub_llm.request_hash(known): '{"label": 2}'}, keep_payloads=True)
        try:
            self.assertEqual(post(url, known), '{"label": 2}')
            self.assertEqual(post(url, other), '{"label": 0}')
            calls = server.config.calls
            self.assertEqual([c["kind"] for c in calls], ["replay", "ok"])
            self.assertEqual(calls[0]["request_sha256"], stub_llm.request_hash(known))
            self.assertEqual(calls[1]["payload"], other)
        finally:
            server.shutdown()


if __name__ == "__main__":
    unittest.main()
