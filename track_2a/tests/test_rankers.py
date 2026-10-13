"""Session 12: model S's code (src/static_embed.py) and the ranker switch (src/rankers.py), on synthetic data."""

import json
import struct
import tempfile
import unittest
from pathlib import Path

import numpy as np

from src import rankers, static_embed, taskb_context
from src.contexts import embed_e5_small, section_route


def write_safetensors(path, matrix):
    data = np.asarray(matrix, dtype="<f4").tobytes()
    header = json.dumps({"embedding.weight": {"dtype": "F32", "shape": list(matrix.shape),
                                              "data_offsets": [0, len(data)]}}).encode()
    path.write_bytes(struct.pack("<Q", len(header)) + header + data)


def write_tokenizer(path, words):
    from tokenizers import Tokenizer, normalizers, pre_tokenizers
    from tokenizers.models import WordPiece
    vocab = {"[UNK]": 0, **{w: i + 1 for i, w in enumerate(words)}}
    tok = Tokenizer(WordPiece(vocab, unk_token="[UNK]"))
    tok.normalizer = normalizers.BertNormalizer(lowercase=True)
    tok.pre_tokenizer = pre_tokenizers.BertPreTokenizer()
    tok.save(str(path))


class StaticModel(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.matrix = np.array([[0, 0, 0, 0], [1, 0, 5, 5], [0, 1, 5, 5], [3, 4, 9, 9]], dtype=np.float32)
        write_safetensors(self.dir / "model.safetensors", self.matrix)
        write_tokenizer(self.dir / "tokenizer.json", ["alpha", "beta", "gamma"])

    def test_convert_keeps_the_first_columns(self):
        static_embed.convert(self.dir / "model.safetensors", self.dir / "embedding_2.npy", dims=2)
        self.assertTrue(np.array_equal(np.load(self.dir / "embedding_2.npy"), self.matrix[:, :2]))

    def test_mean_of_token_vectors_normalised(self):
        static_embed.convert(self.dir / "model.safetensors", self.dir / "embedding_2.npy", dims=2)
        model = static_embed.StaticEmbedder(self.dir, "embedding_2.npy")
        v = model.embed(["Alpha beta", "gamma", "", "!!"])
        expected = np.array([0.5, 0.5]) / np.linalg.norm([0.5, 0.5])
        self.assertTrue(np.allclose(v[0], expected))
        self.assertTrue(np.allclose(v[1], [0.6, 0.8]))
        self.assertTrue(np.array_equal(v[2], [0, 0]))  # no tokens: the zero vector
        self.assertEqual(v.shape, (4, 2))


class Rankers(unittest.TestCase):
    def tearDown(self):
        rankers.ACTIVE["name"] = "e5"

    def test_none_keeps_the_first(self):
        self.assertEqual(rankers.best("none", ["a", "b", "c", "d"], "claim", 2), [0, 1])

    def test_bm25_prefers_shared_words_and_keeps_order(self):
        texts = ["Le Conseil fédéral recommande", "Steuern und Abgaben", "Die Kantone zahlen Steuern", "Andere Dinge"]
        self.assertEqual(rankers.best("BM25", texts, "Die Kantone zahlen Steuern", 2), [1, 2])

    def test_fusion_uses_both_orders(self):
        self.assertEqual(rankers.fused([3.0, 2.0, 1.0], [1.0, 2.0, 3.0]),
                         [1 / 61 + 1 / 63, 1 / 62 + 1 / 62, 1 / 63 + 1 / 61])

    def test_uses_model(self):
        self.assertEqual(rankers.uses_model("e5"), "e5-small")
        self.assertEqual(rankers.uses_model("S+BM25"), "static-s")
        self.assertIsNone(rankers.uses_model("BM25"))
        self.assertIsNone(rankers.uses_model("none"))

    def test_long_part_without_a_model_keeps_its_first_paragraphs(self):
        rankers.ACTIVE["name"] = "none"
        paragraphs = [(1, f"Absatz {i} " + "x" * 50) for i in range(12)]
        self.assertEqual(section_route.most_similar(paragraphs, "claim", 8), paragraphs[:8])

    def test_fallback_without_a_model_ranks_by_words(self):
        rankers.ACTIVE["name"] = "none"
        pages = {1: "Nichts hier.", 2: "Die Kantone zahlen Steuern.", 3: "Auch nichts."}
        text, shown = embed_e5_small.select(pages, "Vote", "Kantone zahlen Steuern")
        self.assertIn("=== PAGE 2 ===", text)

    @staticmethod
    def long_reference(special=None):
        """A title line and 10 paragraphs (four full lines and a short last line each), over 3,000 characters."""
        paragraphs = []
        for i in range(10):
            first = special if i == 7 and special else f"Absatz {i} beginnt hier"
            lines = [first + " " + "wort " * 14] + ["wort " * 18] * 3 + ["Ende des Absatzes."]
            paragraphs.append("\n".join(line.strip() for line in lines))
        return "Titel der Vorlage\n" + "\n".join(paragraphs)

    def test_task_b_without_a_model_sends_the_whole_reference(self):
        rankers.ACTIVE["name"] = "none"
        reference = self.long_reference()
        self.assertTrue(taskb_context.is_long(reference, "cut4-t"))
        self.assertEqual(taskb_context.cut_text(reference, "claim", "cut4-t"), reference)
        self.assertEqual(taskb_context.cut_text(reference, "claim", "cut4-r"), reference)

    def test_task_b_cut4_r_with_bm25_keeps_four_paragraphs(self):
        rankers.ACTIVE["name"] = "BM25"
        reference = self.long_reference(special="Die Kantone zahlen Steuern")
        self.assertEqual(len(taskb_context.split(reference)[1]), 10)
        cut = taskb_context.cut_text(reference, "Kantone zahlen Steuern", "cut4-r")
        self.assertTrue(cut.startswith("Titel der Vorlage\n\n"))
        self.assertIn("Die Kantone zahlen Steuern", cut)
        self.assertEqual(cut.count("Ende des Absatzes."), 4)


class TaskBBM25(unittest.TestCase):
    """Step 3, B-BM25 (cut4-bm25): BM25 on the claim; across languages on Apertus's translation of the claim."""

    def test_cross_language_reference_is_ranked_with_apertus_translation(self):
        from unittest import mock
        from src import cli, llm
        from tests.test_cli import fake_chat
        reference = Rankers.long_reference(special="Die Kantone zahlen Steuern")
        case = {"id": "b2", "vote": "Vorlage", "claim": {"text": "Les cantons paient des impôts", "language": "fr"},
                "reference": {"text": reference, "language": "de"}}
        seen = []
        answers = ['{"translation": "Die Kantone zahlen Steuern"}', '{"label": 0}']
        with mock.patch.object(llm, "chat", fake_chat(answers, seen)):
            resp, status, raw = cli.predict(case, ".", cli.Settings(context_b="cut4-bm25"))
        self.assertEqual(status, "ok")
        self.assertEqual(len(seen), 2)
        self.assertIn("TARGET: German", seen[0][1]["content"])
        self.assertIn("Die Kantone zahlen Steuern", seen[1][1]["content"])  # the paragraph BM25 found
        self.assertIn("Les cantons paient des impôts", seen[1][1]["content"])  # the claim as it is
        self.assertEqual(resp["metrics"]["input_tokens"], 100)  # both calls count
        self.assertEqual(raw["ap_calls"][0]["version"], "AP-translate-v1")

    def test_same_language_needs_no_call(self):
        from unittest import mock
        from src import cli, llm
        from tests.test_cli import fake_chat
        reference = Rankers.long_reference(special="Die Kantone zahlen Steuern")
        case = {"id": "b3", "vote": "Vorlage", "claim": {"text": "Die Kantone zahlen Steuern", "language": "de"},
                "reference": {"text": reference, "language": "de"}}
        seen = []
        with mock.patch.object(llm, "chat", fake_chat(['{"label": 0}'], seen)):
            resp, status, raw = cli.predict(case, ".", cli.Settings(context_b="cut4-bm25"))
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0][1]["content"].count("Ende des Absatzes."), 4)


class TaskAFallbackBM25(unittest.TestCase):
    """Step 5, bm25-ap (off by default): the fallback's chunks by BM25; across languages on Apertus's translation."""

    def run_case(self, claim_language, answers):
        from unittest import mock
        from src import cli, llm
        from tests.test_cli import fake_chat
        pages = {1: "Einleitung ohne Bezug.", 2: "Die Kantone zahlen die Steuern selbst.", 3: "Anderes Thema hier."}
        case = {"id": "a1", "vote": "Vorlage", "claim": {"text": "Les cantons paient les impôts", "language": claim_language},
                "booklet": {"path": "booklets/x.pdf", "language": "de"}}
        seen = []
        with mock.patch.object(cli.parse, "load_pages", return_value=pages), \
                mock.patch.object(cli.Path, "is_file", return_value=True), \
                mock.patch.object(llm, "chat", fake_chat(answers, seen)):
            resp, status, raw = cli.predict(case, ".", cli.Settings(fallback_a="bm25-ap", ap_part_a="off"))
        return resp, status, raw, seen

    def test_cross_language_claim_is_translated_first(self):
        resp, status, raw, seen = self.run_case("fr", ['{"translation": "Die Kantone zahlen die Steuern"}',
                                                       '{"pages": [2], "label": 0}'])
        self.assertEqual((status, raw["fallback"], len(seen)), ("ok", "bm25-ap", 2))
        self.assertIn("TARGET: German", seen[0][1]["content"])
        self.assertIn("=== PAGE 2 ===", seen[1][1]["content"])
        self.assertIn("Les cantons paient les impôts", seen[1][1]["content"])
        self.assertEqual(resp["evidence"][0]["page"], 2)
        self.assertEqual(resp["metrics"]["input_tokens"], 100)

    def test_failed_translation_ranks_with_the_claim(self):
        from src import llm
        resp, status, raw, seen = self.run_case("fr", [llm.LLMError("down"), '{"pages": [2], "label": 1}'])
        self.assertEqual((status, resp["label"], len(seen)), ("ok", 1, 2))
        self.assertIn("error", raw["ap_calls"][0])


class AskStructure(unittest.TestCase):
    """Step 6 (ask-after-parser, off by default): the parser gives no valid part, Apertus reads the contents."""

    def test_no_valid_part_asks_apertus_then_routes_or_falls_back(self):
        from unittest import mock
        from src import cli, llm
        from tests.test_cli import fake_chat
        from tests.test_section_route import COUNCIL_CLAIM, VOTE, booklet_pages, case
        from src import booklet as booklet_module
        pages = booklet_pages()
        empty = booklet_module.Booklet(votes=[])  # the parser finds no vote at all
        seen = []
        entries = ('{"votes": [{"title": "Volksinitiative «Für mehr Velowege»", "summary": 4, "detail": 8, '
                   '"arguments": 12, "law": 16}]}')
        with mock.patch.object(cli.parse, "load_pages", return_value=pages), \
                mock.patch.object(cli.Path, "is_file", return_value=True), \
                mock.patch.object(embed_e5_small, "select_chunks", return_value=[(14, "chunk")]), \
                mock.patch.object(section_route, "parsed_booklet", return_value=empty), \
                mock.patch.object(llm, "chat", fake_chat([entries, '{"paragraphs": [1], "label": 0}'], seen)):
            resp, status, raw = cli.predict(case(COUNCIL_CLAIM), ".", cli.Settings(ap_structure_a="ask-after-parser"))
        self.assertEqual(len(seen), 2)
        self.assertEqual(raw["ap_calls"][0]["version"], "AP-structure-v1")
        self.assertTrue(raw["ap_structure"]["vote_found"])
        self.assertEqual(resp["metrics"]["input_tokens"], 100)
        if raw.get("route") == "council":  # Apertus's entries passed the parser's checks
            self.assertIn("PART:", seen[1][1]["content"])
        else:  # else the case ran as its fallback, still with a model call
            self.assertIn("=== PAGE 14 ===", seen[1][1]["content"])

    def test_the_default_never_asks(self):
        from src import cli
        self.assertEqual(cli.Settings().ap_structure_a, "off")
        self.assertFalse(cli.ap_in_prepare(cli.Settings(ap_structure_a="ask-after-parser")))


class FallbackRobustness(unittest.TestCase):
    def test_a_bm25_error_goes_on_to_embed_e5_small(self):
        from unittest import mock
        from src import cli, llm
        from tests.test_cli import fake_chat
        pages = {1: "Einleitung.", 2: None}  # a page without text makes the chunking raise
        case = {"id": "a2", "vote": "Vorlage", "claim": {"text": "Die Kantone zahlen", "language": "de"},
                "booklet": {"path": "booklets/x.pdf", "language": "de"}}
        seen = []
        with mock.patch.object(cli.parse, "load_pages", return_value=pages), \
                mock.patch.object(cli.Path, "is_file", return_value=True), \
                mock.patch.object(embed_e5_small, "select_chunks", return_value=[(1, "Einleitung.")]), \
                mock.patch.object(llm, "chat", fake_chat(['{"pages": [1], "label": 1}'], seen)):
            resp, status, raw = cli.predict(case, ".", cli.Settings(fallback_a="bm25-ap", ap_part_a="off"))
        self.assertEqual((status, raw["fallback"], len(seen)), ("ok", "embed-e5-small", 1))
        self.assertIn("bm25_error", raw)


class MemoryGuard(unittest.TestCase):
    """Step 2: no embedding model under a low memory limit, without its files, or when it fails to load."""

    def tearDown(self):
        rankers.ACTIVE["name"] = "e5"
        rankers.CASE["guard"] = None
        rankers._unusable.clear()

    def test_low_memory_limit_marks_the_model_for_the_whole_run(self):
        from unittest import mock
        with mock.patch.object(rankers, "model_files", return_value=[]):
            marked = rankers.run_guard(rankers.MIN_MEMORY["e5-small"] - 1)
        self.assertIn("memory limit", marked["e5-small"])
        self.assertNotIn("static-s", marked)  # S needs less
        self.assertEqual(rankers.effective("e5"), "none")
        self.assertEqual(rankers.effective("S"), "S")

    def test_missing_files_mark_the_model(self):
        from unittest import mock
        with mock.patch.object(rankers, "model_files", return_value=[Path("/nonexistent/model.onnx")]):
            self.assertEqual(set(rankers.run_guard(None)), {"e5-small", "static-s"})

    def test_enough_memory_and_files_mark_nothing(self):
        from unittest import mock
        with mock.patch.object(rankers, "model_files", return_value=[]):
            self.assertEqual(rankers.run_guard(4 * rankers.GIB), {})
            self.assertEqual(rankers.run_guard(None), {})

    def test_task_b_selector_t_without_e5_sends_the_whole_reference(self):
        rankers._unusable["e5-small"] = "memory limit test"
        rankers.ACTIVE["name"] = "S"  # task A's ranker does not matter: T needs e5
        reference = Rankers.long_reference()
        self.assertEqual(taskb_context.cut_text(reference, "claim", "cut4-t"), reference)
        self.assertEqual(rankers.CASE["guard"], "memory limit test")

    def test_a_model_that_fails_to_load_is_replaced_by_none(self):
        from unittest import mock
        from src.contexts import retrieval

        def broken():
            raise MemoryError("no room")
        with mock.patch.dict(retrieval.MODELS, {"static-s": (broken, "", "")}), \
                mock.patch.dict(retrieval._embedders, {}, clear=True):
            rankers.ACTIVE["name"] = "S"
            paragraphs = [(1, f"Absatz {i} " + "x" * 50) for i in range(12)]
            self.assertEqual(section_route.most_similar(paragraphs, "claim", 8), paragraphs[:8])
            self.assertIn("MemoryError", rankers.CASE["guard"])
            self.assertEqual(rankers.effective("S"), "none")  # later cases skip the model at once

    def test_e5_failing_in_the_fallback_ranks_by_words(self):
        from unittest import mock
        with mock.patch.object(embed_e5_small, "select_chunks", side_effect=FileNotFoundError("model.onnx")):
            pages = {1: "Nichts hier.", 2: "Die Kantone zahlen Steuern.", 3: "Auch nichts."}
            text, shown = embed_e5_small.select(pages, "Vote", "Kantone zahlen Steuern")
        self.assertIn("=== PAGE 2 ===", text)
        self.assertIn("FileNotFoundError", rankers.CASE["guard"])

    def test_cli_records_the_guard_in_the_raw_answer(self):
        from unittest import mock
        from src import cli
        from src.contexts import retrieval

        def broken():
            raise OSError("model file unreadable")
        reference = Rankers.long_reference()
        case = {"id": "b1", "vote": "Vorlage", "claim": {"text": "claim", "language": "de"},
                "reference": {"text": reference, "language": "de"}}
        with mock.patch.dict(retrieval.MODELS, {"static-s": (broken, "", "")}), \
                mock.patch.dict(retrieval._embedders, {}, clear=True):
            prepared = cli.prepare(case, ".", cli.Settings(context_b="cut4-r", ranker="S"))
        self.assertIn("OSError", prepared.raw["ranker_guard"])
        self.assertIn(reference, prepared.messages[1]["content"])  # the whole reference


if __name__ == "__main__":
    unittest.main()
