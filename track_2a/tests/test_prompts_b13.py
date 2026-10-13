"""Tests for session 13's step 2 (off by default): task B prompts B1 (v7-same-ballot), B2 (v7-unrelated), B4
(v7-claim-first) and B3, selector T with the reference's first line (context_b "cut4-tf")."""

import json
import unittest
from unittest import mock

import numpy as np

from src import cli, llm, nli, rankers, taskb_context

CASE = {"id": "x-B", "vote": "V", "claim": {"text": "Der Bund zahlt 40 Millionen.", "language": "de"},
        "reference": {"text": "Titel\nDer Bund zahlt 40 Millionen Franken pro Jahr.", "language": "de"}}


def run(settings, answer):
    seen = []

    def chat(messages, max_tokens=256, json_mode=False, json_schema=None):
        seen.append((messages, max_tokens, json_schema))
        return llm.LLMResult(text=answer, input_tokens=10, output_tokens=3, elapsed_ms=1)
    with mock.patch.object(llm, "chat", chat):
        resp, status, raw = cli.predict(CASE, ".", settings)
    return resp, raw, seen


class PromptsB(unittest.TestCase):
    def test_today_is_unchanged(self):
        _, raw, seen = run(cli.Settings(), '{"label": 0}')
        self.assertEqual(raw["prompt_version"], "v3-topic-first")
        self.assertEqual((seen[0][1], seen[0][2]), (32, None))

    def test_versions_send_their_prompt_schema_and_budget(self):
        for version, budget in (("v7-same-ballot", 160), ("v7-unrelated", 32), ("v7-claim-first", 128)):
            spec = nli.B_VERSIONS.get(version)
            _, raw, seen = run(cli.Settings(prompt_b=version), '{"label": 2}')
            self.assertEqual(seen[0][0][0]["content"], nli.PROMPTS_B[version])
            self.assertEqual(seen[0][1], budget)
            self.assertEqual(seen[0][2], spec["schema"] if spec else None)

    def test_schemas_list_the_fields_in_the_prompt_s_order(self):
        for version, fields in (("v7-same-ballot", ["passage_ballot", "claim_ballot", "same_ballot", "label"]),
                                ("v7-claim-first", ["claim_says", "label"])):
            schema = nli.B_VERSIONS[version]["schema"]
            self.assertEqual((list(schema["properties"]), schema["required"]), (fields, fields))
            self.assertFalse(schema["additionalProperties"])
            self.assertEqual(list(json.loads(nli.PROMPTS_B[version].rsplit("\n", 1)[1])), fields)

    def test_the_label_field_is_read_and_never_checked_against_same_ballot(self):
        resp, _, _ = run(cli.Settings(prompt_b="v7-same-ballot"),
                         '{"passage_ballot": "a", "claim_ballot": "b", "same_ballot": false, "label": 2}')
        self.assertEqual(resp["label"], 2)  # Apertus's label, even with same_ballot false
        resp, _, _ = run(cli.Settings(prompt_b="v7-claim-first"), '{"claim_says": "x", "label": 0}')
        self.assertEqual(resp["label"], 0)

    def test_b2_and_b4_keep_v3_s_other_blocks(self):
        v3 = nli.PROMPTS_B["v3-topic-first"]
        self.assertTrue(nli.PROMPTS_B["v7-unrelated"].endswith('{"label": <0, 1 or 2>}'))
        self.assertTrue(nli.PROMPTS_B["v7-claim-first"].startswith(v3[:v3.index("Answer with one JSON object")]))


class _Recorder:
    def __init__(self):
        self.texts = []

    def embed(self, texts):
        self.texts.extend(texts)
        return np.array([[1.0, 0.0] if "Milliarden" in t else [0.0, 1.0] for t in texts])


class SelectorTF(unittest.TestCase):
    def tearDown(self):
        rankers.reset()

    def test_each_paragraph_is_embedded_with_the_first_line(self):
        paragraphs = ["Die Gemeinden verwalten ihre Strassen. " * 12, "Der Bund zahlt 1,2 Milliarden Franken.",
                      "Die Kantone regeln den Rest."]
        recorder = _Recorder()
        with mock.patch.object(taskb_context.retrieval, "embedder", return_value=recorder), \
             mock.patch.object(taskb_context.retrieval, "query_vector", return_value=np.array([1.0, 0.0])):
            scores = taskb_context.selector_scores("TF", paragraphs, "Der Bund zahlt.", "Titel der Vorlage")
        self.assertEqual([float(x) for x in scores], [0.0, 1.0, 0.0])
        self.assertEqual(recorder.texts, [f"passage: Titel der Vorlage: {p[:taskb_context.T_CHARS]}" for p in paragraphs])
        self.assertEqual(taskb_context.ranking_model("cut4-tf"), "e5-small")

    def test_cut4_tf_passes_the_first_line_to_selector_tf(self):
        text = "Titel der Vorlage\n" + "\n\n".join(("Absatz %d. " % i) + "Wort " * 120 + "\nEnde." for i in range(8))
        self.assertTrue(taskb_context.is_long(text, "cut4-tf"))
        with mock.patch.object(taskb_context, "selector_scores", return_value=list(range(9))) as scores:
            first, kept = taskb_context.cut_paragraphs(text, "c", "cut4-tf")
        self.assertEqual((scores.call_args.args[0], scores.call_args.args[3]), ("TF", "Titel der Vorlage"))
        self.assertEqual(len(kept), taskb_context.CUT4_TOP_K)

if __name__ == "__main__":
    unittest.main()
