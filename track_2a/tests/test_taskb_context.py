"""Tests for the task B context variants B-cut and B-para (src/taskb_context.py) and their path in src/cli.py."""

import unittest
from unittest import mock

import numpy as np

from src import cli, llm, taskb_context
from src.contexts import retrieval

TITLE = "Bundesgesetz über die Velowege"


class KeywordEmbedder:
    """Stands in for e5: a text mentioning "Steuer" points one way, every other text the other way."""

    def embed(self, texts):
        return np.array([[1.0, 0.0] if "Steuer" in t else [0.0, 1.0] for t in texts])


def reference(n_paragraphs, chars, tag):
    """A title line, then n paragraphs of about `chars` characters separated by blank lines; paragraphs 3 and 9
    mention "Steuer". Like the dataset's references, there are no blank lines. `tag` makes the texts unique (section_route caches vectors by text)."""
    paragraphs = []
    for i in range(1, n_paragraphs + 1):
        word = "Steuer" if i in (3, 9) else "Velo"
        # a full line, then a short line that ends the sentence (the end of a paragraph for page_paragraphs)
        paragraphs.append(f"Absatz {i} {tag} {word} " + ("Wort " * (chars // 5)).strip() + f"\nEnde von Absatz {i}.")
    return TITLE + "\n" + "\n".join(paragraphs)


def patched():
    return (mock.patch.object(retrieval, "embedder", return_value=KeywordEmbedder()),
            mock.patch.object(retrieval, "query_vector", return_value=np.array([1.0, 0.0])))


class CutAndPara(unittest.TestCase):
    def test_short_reference_is_unchanged(self):
        text = reference(3, 300, "kurz")
        self.assertFalse(taskb_context.is_long(text))
        self.assertEqual(taskb_context.cut_text(text, "Die Steuer steigt."), text)  # the same request as by default
        first, paragraphs = taskb_context.split(text)
        self.assertEqual(first, TITLE)
        self.assertEqual(len(paragraphs), 3)

    def test_long_reference_keeps_title_and_most_similar_paragraphs_in_order(self):
        text = reference(12, 900, "lang")
        self.assertTrue(taskb_context.is_long(text))
        emb, query = patched()
        with emb, query:
            first, kept = taskb_context.cut_paragraphs(text, "Die Steuer steigt.")
            cut = taskb_context.cut_text(text, "Die Steuer steigt.")
            numbered = taskb_context.para_texts(text, "Die Steuer steigt.")
        self.assertEqual(first, TITLE)
        self.assertEqual(len(kept), taskb_context.TOP_K)
        numbers = [int(p.split()[1]) for p in kept]
        self.assertEqual(numbers, [1, 2, 3, 4, 5, 6, 7, 9])  # both "Steuer" paragraphs, then ties in order; text order
        self.assertTrue(cut.startswith(TITLE + "\n\n"))
        for p in kept:
            self.assertIn(p, cut)  # verbatim
        self.assertLess(len(cut), len(text))
        self.assertEqual(numbered[0], TITLE)
        self.assertEqual(len(numbered), 1 + taskb_context.TOP_K)

    def test_cut4_keeps_four_paragraphs_of_a_reference_over_3000_characters(self):  # session 10, step 5
        text = reference(6, 600, "vier")
        self.assertTrue(3000 < len(text) <= 8000)
        self.assertFalse(taskb_context.is_long(text))  # B-cut leaves it whole
        self.assertTrue(taskb_context.is_long(text, "cut4"))
        emb, query = patched()
        with emb, query:
            first, kept = taskb_context.cut_paragraphs(text, "Die Steuer steigt.", "cut4")
            cut = taskb_context.cut_text(text, "Die Steuer steigt.", "cut4")
        self.assertEqual([int(p.split()[1]) for p in kept], [1, 2, 3, 4])  # "Steuer" (3) first, then ties in order
        self.assertEqual(cut, "\n\n".join([first] + kept))
        self.assertEqual(taskb_context.cut_text(text, "Die Steuer steigt.", "cut"), text)

    def test_text_without_paragraphs_is_sent_whole(self):
        self.assertEqual(taskb_context.para_texts("Nur ein Titel", "c"), ["Nur ein Titel"])
        self.assertEqual(taskb_context.split(""), ("", []))


class CliModes(unittest.TestCase):
    def predict(self, mode, answer, reference_text):
        seen = {}

        def chat(messages, max_tokens=256, json_mode=False, json_schema=None):
            seen.update(messages=messages, schema=json_schema, max_tokens=max_tokens)
            return llm.LLMResult(text=answer, input_tokens=9, output_tokens=3, elapsed_ms=1)
        case = {"id": "b", "vote": TITLE, "claim": {"text": "Die Steuer steigt.", "language": "de"},
                "reference": {"text": reference_text, "language": "de"}}
        emb, query = patched()
        with mock.patch.object(llm, "chat", chat), emb, query:
            resp, status, raw = cli.predict(case, ".", cli.Settings(context_b=mode))
        return resp, status, raw, seen

    def test_unified_uses_task_a_default_prompt_and_schema(self):  # session 10, step 9 (B-U)
        text = reference(12, 900, "cli-unified")
        resp, status, raw, seen = self.predict("unified", '{"paragraphs": [2], "label": 2}', text)
        self.assertEqual((resp["label"], status, resp["evidence"]), (2, "ok", []))
        self.assertEqual(raw["prompt_version"], "A-v4-section-route-L1")
        self.assertEqual(seen["messages"][0]["content"], cli.nli.PROMPTS_A["A-v4-section-route-L1"])
        self.assertEqual(seen["schema"], cli.nli.ANSWER_SCHEMA_A_PARAGRAPHS)
        self.assertIn("[1] " + TITLE, seen["messages"][1]["content"])

    def test_default_is_selector_t(self):
        # session 11, step 6 (TASK B RULE); session 10: the whole reference; session 9, phase C: cut
        self.assertEqual(cli.Settings().context_b, "cut4-t")

    def test_cut_uses_task_b_prompt_and_schema(self):
        text = reference(12, 900, "cli-cut")
        resp, status, raw, seen = self.predict("cut", '{"label": 2}', text)
        emb, query = patched()
        with emb, query:
            cut = taskb_context.cut_text(text, "Die Steuer steigt.")
        self.assertEqual((resp["label"], status, resp["evidence"]), (2, "ok", []))
        self.assertEqual(seen["messages"], cli.nli.build_messages_b(cut, "Die Steuer steigt.", cli.Settings().prompt_b))
        self.assertEqual((seen["schema"], seen["max_tokens"]), (None, cli.Settings().max_tokens_b))
        self.assertLess(raw["chars_sent"], len(text))

    def test_para_uses_paragraph_prompt_and_schema_and_keeps_evidence_empty(self):
        text = reference(12, 900, "cli-para")
        resp, status, raw, seen = self.predict("para", '{"paragraphs": [2], "label": 0}', text)
        self.assertEqual((resp["label"], status, resp["evidence"]), (0, "ok", []))
        self.assertEqual(seen["schema"], cli.nli.ANSWER_SCHEMA_A_PARAGRAPHS)
        self.assertEqual(seen["max_tokens"], cli.Settings().max_tokens_a)
        self.assertIn("[1] " + TITLE, seen["messages"][1]["content"])
        self.assertEqual((raw["prompt_version"], raw["paragraphs_sent"]), ("A-v4-section-route", 9))

    def test_error_while_cutting_sends_the_whole_reference(self):
        text = reference(12, 900, "cli-error")
        with mock.patch.object(taskb_context, "cut_text", side_effect=FileNotFoundError("model.onnx")):
            resp, status, raw, seen = self.predict("cut", '{"label": 1}', text)
        self.assertEqual((resp["label"], status), (1, "ok"))
        self.assertIn("context_b_error", raw)
        self.assertEqual(seen["messages"], cli.nli.build_messages_b(text, "Die Steuer steigt.", cli.Settings().prompt_b))


if __name__ == "__main__":
    unittest.main()


class Selectors(unittest.TestCase):
    """Session 11, step 6 (off by default): other ways to pick B-cut4's 4 paragraphs."""

    PARAGRAPHS = [f"Absatz {i}: " + "Die Gemeinden verwalten ihre Strassen und Plätze selbst. " * 3 for i in range(8)]

    def reference(self):
        paragraphs = list(self.PARAGRAPHS)
        paragraphs[5] = "Der Bund zahlt 1,2 Milliarden Franken pro Jahr an die Kantone für die Velowege im Land."
        return "Titel der Vorlage\n" + "\n\n".join(p + "\n" + "x" * 400 + "." for p in paragraphs)

    def test_lexical_score_counts_shared_4_grams_and_numbers(self):
        claim = "Der Bund zahlt 1,2 Milliarden Franken."
        self.assertGreater(taskb_context.lexical_score(claim, "Der Bund zahlt 1,2 Milliarden Franken pro Jahr."),
                           taskb_context.lexical_score(claim, "Die Gemeinden verwalten ihre Strassen selbst."))
        self.assertGreaterEqual(taskb_context.lexical_score("Es sind 26 Kantone.", "Die 26 Kantone"), 1.0)

    def test_selector_l_keeps_the_matching_paragraph_without_a_model(self):
        text = self.reference()
        self.assertTrue(taskb_context.is_long(text, "cut4-l"))
        with mock.patch.object(taskb_context.retrieval, "embedder", side_effect=AssertionError("no model")):
            first, kept = taskb_context.cut_paragraphs(text, "Der Bund zahlt 1,2 Milliarden Franken.", "cut4-l")
        self.assertEqual(first, "Titel der Vorlage")
        self.assertEqual(len(kept), taskb_context.CUT4_TOP_K)
        self.assertTrue(any("1,2 Milliarden" in p for p in kept))

    def test_selector_h_uses_l_for_one_language_and_e5_across_languages(self):
        text = self.reference()
        with mock.patch.object(taskb_context, "selector_scores", wraps=taskb_context.selector_scores) as scores, \
             mock.patch.object(taskb_context.retrieval, "embedder", return_value=_Ones()), \
             mock.patch.object(taskb_context.retrieval, "query_vector", return_value=__import__("numpy").ones(4) / 2):
            taskb_context.cut_paragraphs(text, "Der Bund zahlt 1,2 Milliarden.", "cut4-h", same_language=True)
            taskb_context.cut_paragraphs(text, "La Confédération paie 1,2 milliard.", "cut4-h", same_language=False)
        self.assertEqual([c.args[0] for c in scores.call_args_list], ["L", "T"])

    def test_t_is_the_default_and_needs_the_model_only_for_long_references(self):
        settings = cli.Settings()
        self.assertEqual(settings.context_b, "cut4-t")
        short = {"id": "s-B", "reference": {"text": "x" * 100, "language": "de"}, "claim": {"text": "c", "language": "de"}}
        long = {"id": "l-B", "reference": {"text": "x" * 4000, "language": "de"}, "claim": {"text": "c", "language": "de"}}
        self.assertFalse(cli.needs_local_model(short, settings))
        self.assertTrue(cli.needs_local_model(long, settings))


class _Ones:
    def embed(self, texts):
        import numpy as np
        return np.ones((len(texts), 4)) / 2.0
