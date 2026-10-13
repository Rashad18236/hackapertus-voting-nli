"""Tests for the robustness experiments: strategies (src/strategies.py), their hooks in src/cli.py, BM25 and the
hybrid ranking (src/contexts/bm25.py), translation pieces (src/translate.py) and language detection (src/langid.py).
No model and no translation model: the judge, llm.chat and translate.translate are replaced."""

import json
import unittest
from unittest import mock

from src import cli, langid, llm, strategies, translate
from src.contexts import bm25
from tests.test_booklet import booklet_pages
from tests.test_section_route import COUNCIL_CLAIM, VOTE


def result(text="", input_tokens=10, output_tokens=2):
    return llm.LLMResult(text=text, input_tokens=input_tokens, output_tokens=output_tokens, elapsed_ms=1)


def fake_judge(labels, seen=None):
    """A judge that answers labels in turn (a callable label(claim, texts) is also accepted)."""
    labels = list(labels)

    def judge(claim, texts):
        if seen is not None:
            seen.append((claim, list(texts)))
        label = labels.pop(0)
        if isinstance(label, Exception):
            raise label
        return strategies.Judgement(label, [1] if label in (0, 2) else [], result(f'{{"label": {label}}}'))
    return judge


class CombinationRules(unittest.TestCase):
    def test_tournament_needs_both_sides(self):
        self.assertEqual(strategies.combine_tournament(0, 0), 0)
        self.assertEqual(strategies.combine_tournament(2, 2), 2)
        self.assertIsNone(strategies.combine_tournament(0, 1))
        self.assertIsNone(strategies.combine_tournament(None, None))

    def test_negation_only_replaces_a_neutral(self):
        expected = {(1, 0): 2, (1, 2): 0, (1, 1): 1, (1, None): 1,  # neutral: the negation's implied label
                    (0, 2): 0, (0, 0): 0, (0, 1): 0, (2, 0): 2, (2, 2): 2, (2, 1): 2, (None, 0): None}
        for (original, negated), final in expected.items():
            with self.subTest(original=original, negated=negated):
                self.assertEqual(strategies.combine_negation(original, negated), final)

    def test_parts(self):
        self.assertEqual(strategies.combine_parts([0, 0, 0]), 0)
        self.assertEqual(strategies.combine_parts([0, 2, 1]), 2)
        self.assertEqual(strategies.combine_parts([0, 1]), 1)
        self.assertEqual(strategies.combine_parts([0, None]), 1)
        self.assertEqual(strategies.combine_parts([]), 1)


class Xlang(unittest.TestCase):
    def fake_translate(self, texts, src, tgt):
        return [f"{tgt}:{t}" for t in texts]

    def test_same_language_is_one_call(self):
        out = strategies.run("xlang", fake_judge([0]), "c", ["p"], "de", "de")
        self.assertEqual((out.label, len(out.record["calls"])), (0, 1))

    def test_both_sides_agree(self):
        seen = []
        with mock.patch.object(translate, "translate", self.fake_translate):
            out = strategies.run("xlang", fake_judge([2, 2], seen), "claim", ["p1", "p2"], "de", "fr")
        self.assertEqual(out.label, 2)
        self.assertEqual(seen, [("fr:claim", ["p1", "p2"]), ("claim", ["de:p1", "de:p2"])])
        self.assertEqual((out.input_tokens, out.output_tokens), (20, 4))
        self.assertEqual(out.numbers, [1])

    def test_disagreement_goes_to_a_tie_break_on_the_original_pair(self):
        seen = []
        with mock.patch.object(translate, "translate", self.fake_translate):
            out = strategies.run("xlang", fake_judge([0, 1, 1], seen), "claim", ["p"], "de", "fr")
        self.assertEqual(out.label, 1)
        self.assertEqual(seen[-1], ("claim", ["p"]))
        self.assertEqual([c["role"] for c in out.record["calls"]], ["side_s", "side_c", "tie_break"])

    def test_missing_translation_model_runs_as_today(self):
        def broken(texts, src, tgt):
            raise translate.TranslationError("no model")
        with mock.patch.object(translate, "translate", broken):
            out = strategies.run("xlang", fake_judge([0]), "claim", ["p"], "de", "fr")
        self.assertEqual((out.label, len(out.record["calls"])), (0, 1))
        self.assertIn("translation_error", out.record)


class NegationAndDecompose(unittest.TestCase):
    def test_negation_entailed_turns_a_neutral_into_a_contradiction(self):
        seen = []
        with mock.patch.object(llm, "chat", return_value=result('{"claim": "not c"}', 5, 3)):
            out = strategies.run("negation", fake_judge([1, 0], seen), "c", ["p"], "de", "de")
        self.assertEqual(out.label, 2)
        self.assertEqual(seen[1][0], "not c")
        self.assertEqual((out.input_tokens, out.output_tokens), (25, 7))  # base + rewrite + negated

    def test_unreadable_negation_keeps_the_first_answer(self):
        with mock.patch.object(llm, "chat", return_value=result("sorry")):
            out = strategies.run("negation", fake_judge([1]), "c", ["p"], "de", "de")
        self.assertEqual(out.label, 1)

    def test_short_claims_are_not_split(self):
        out = strategies.run("decompose", fake_judge([0]), "short", ["p"], "de", "de")
        self.assertEqual(len(out.record["calls"]), 1)

    def test_parts_are_judged_one_by_one(self):
        claim = "x" * 200
        answer = json.dumps({"claims": ["a", "b", "c"]})
        with mock.patch.object(llm, "chat", return_value=result(answer)):
            out = strategies.run("decompose", fake_judge([0, 0, 2]), claim, ["p"], "de", "de")
        self.assertEqual(out.label, 2)
        self.assertEqual(out.record["parts"], ["a", "b", "c"])

    def test_a_failed_call_reports_what_was_spent(self):
        with mock.patch.object(llm, "chat", side_effect=llm.LLMError("down")), \
             self.assertRaises(strategies.StrategyFailed) as ctx:
            strategies.run("negation", fake_judge([1]), "c", ["p"], "de", "de")  # base answers, the rewrite fails
        self.assertEqual((ctx.exception.input_tokens, ctx.exception.output_tokens), (10, 2))


class CliHooks(unittest.TestCase):
    def test_task_b_negation_sums_tokens_and_answers_once(self):
        answers = iter([result('{"label": 1}', 100, 5), result('{"claim": "neg"}', 30, 8),
                        result('{"label": 0}', 100, 5)])
        case = {"id": "b", "vote": "v", "claim": {"text": "c", "language": "de"},
                "reference": {"text": "r", "language": "de"}}
        with mock.patch.object(llm, "chat", lambda *a, **k: next(answers)):
            resp, status, raw = cli.predict(case, ".", cli.Settings(strategy_b="negation"))
        self.assertEqual((resp["label"], status), (2, "ok"))
        self.assertEqual(resp["metrics"]["input_tokens"], 230)
        self.assertEqual(resp["metrics"]["output_tokens"], 18)
        self.assertEqual(raw["strategy"]["name"], "negation")

    def test_task_a_failed_strategy_falls_back_to_one_call_and_keeps_its_tokens(self):
        calls = []

        def chat(messages, max_tokens=256, json_mode=False, json_schema=None):
            calls.append(messages)
            if len(calls) == 2:  # the negation rewrite fails
                raise llm.LLMError("down")
            return result('{"paragraphs": [1], "label": 0}', 40, 6)
        case = {"id": "a", "vote": VOTE, "claim": {"text": COUNCIL_CLAIM, "language": "de"},
                "booklet": {"path": "booklets/x.pdf", "language": "de"}}
        with mock.patch.object(llm, "chat", chat), \
             mock.patch.object(cli.parse, "load_pages", return_value=booklet_pages()), \
             mock.patch.object(cli.Path, "is_file", return_value=True):
            resp, status, raw = cli.predict(case, ".", cli.Settings(strategy_a="negation"))
        self.assertEqual((resp["label"], status), (0, "ok"))
        self.assertEqual(len(calls), 3)  # base, failed rewrite, the normal single call
        self.assertEqual(resp["metrics"]["input_tokens"], 80)
        self.assertTrue(resp["evidence"])
        self.assertIn("error", raw["strategy"])


class Bm25(unittest.TestCase):
    CHUNKS = [(1, "Der Bund zahlt 40 Millionen Franken für Velowege."),
              (2, "Die Kantone regeln den Unterricht an Schulen."),
              (3, "Velowege werden ausgebaut; der Bund zahlt.")]

    def test_ranks_by_shared_words(self):
        scores = bm25.bm25_scores(self.CHUNKS, "Wie viele Millionen zahlt der Bund für Velowege?")
        self.assertEqual(max(range(3), key=lambda i: scores[i]), 0)
        self.assertEqual(scores[1], 0.0)

    def test_stem_matches_inflections(self):
        self.assertEqual(bm25.tokens("Initiative Initiativen")[0], bm25.tokens("Initiativen")[0])

    def test_hybrid_fuses_both_rankings_in_page_order(self):
        with mock.patch.object(bm25.embed_e5_small, "chunk_scores", return_value=(self.CHUNKS, [0.1, 0.9, 0.2])), \
             mock.patch.object(bm25, "translated_claim", return_value="Bund zahlt Millionen Velowege"):
            kept = bm25.hybrid_chunks({1: "", 2: "", 3: ""}, "claim", top_k=2)
        self.assertEqual([p for p, _ in kept], [1, 2])  # e5's best (2) and BM25's best (1), in page order


class SectionRouteWithOtherFallbacks(unittest.TestCase):
    def test_routed_cases_are_unchanged_and_others_use_the_new_fallback(self):
        from src import context
        from src.contexts import bm25_mt, section_route, section_route_bm25_mt
        pages = booklet_pages()
        self.assertEqual(section_route_bm25_mt.route(pages, VOTE, COUNCIL_CLAIM),
                         section_route.route(pages, VOTE, COUNCIL_CLAIM))
        self.assertEqual(section_route_bm25_mt.select(pages, VOTE, COUNCIL_CLAIM),
                         section_route.select(pages, VOTE, COUNCIL_CLAIM))
        unroutable = "Die Schweiz hat 26 Kantone."
        with mock.patch.object(bm25, "translated_claim", side_effect=lambda pages, claim: claim):
            self.assertEqual(section_route_bm25_mt.select(pages, VOTE, unroutable),
                             bm25_mt.select(pages, VOTE, unroutable))
        self.assertEqual(context.fallback("section-route-bm25-mt"), "bm25-mt")


class TranslateAndLangid(unittest.TestCase):
    def test_pieces_keep_whole_sentences_and_respect_the_limit(self):
        text = "Erster Satz. " * 30 + "x" * 900
        pieces = translate.pieces(text, max_chars=100)
        self.assertTrue(all(len(p) <= 100 for p in pieces))
        self.assertEqual(" ".join(pieces).replace(" ", ""), text.replace(" ", ""))

    def test_same_language_needs_no_model(self):
        self.assertEqual(translate.translate(["a"], "de", "de"), ["a"])

    def test_detect(self):
        self.assertEqual(langid.detect("Der Bundesrat ist der Ansicht, dass die Initiative zu weit geht."), "de")
        self.assertEqual(langid.detect("Le Conseil fédéral estime que les cantons sont responsables."), "fr")
        self.assertEqual(langid.detect("Il Consiglio federale ritiene che la proposta non sia necessaria."), "it")


if __name__ == "__main__":
    unittest.main()
