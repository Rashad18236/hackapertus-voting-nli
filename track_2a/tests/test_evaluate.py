"""Tests for src/evaluate.py with cases small enough to check on paper.

Run from track_2a/:  python3 -m pytest tests   (or: python3 -m unittest discover tests)
"""

import unittest

from src import evaluate as ev

NAMES = {0: "entailment", 1: "neutral", 2: "contradiction"}


def pred(case_id, label, tokens=100, ms=1000, name=None):
    return {"id": case_id, "label": label, "label_name": name or NAMES.get(label), "evidence": [],
            "metrics": {"input_tokens": tokens, "output_tokens": 10, "inference_time_ms": ms}}


def case_b(case_id, claim="de", source="de"):
    return {"id": case_id, "vote": "v", "claim": {"text": "c", "language": claim},
            "reference": {"text": "r", "language": source}}


def case_a(case_id, claim="de", source="de"):
    return {"id": case_id, "vote": "v", "claim": {"text": "c", "language": claim},
            "booklet": {"path": "booklets/x.pdf", "language": source}}


class LabelScores(unittest.TestCase):
    def test_hand_worked_example(self):
        # gold  0 0 1 2
        # pred  0 1 1 None
        # class 0: tp 1, fp 0, fn 1 -> P 1,   R 1/2, F1 2/3
        # class 1: tp 1, fp 1, fn 0 -> P 1/2, R 1,   F1 2/3
        # class 2: tp 0, fp 0, fn 1 -> P 0,   R 0,   F1 0
        # Macro-F1 = (2/3 + 2/3 + 0) / 3 = 4/9; accuracy 2/4
        s = ev.label_scores([0, 0, 1, 2], [0, 1, 1, None])
        self.assertAlmostEqual(s["per_class"]["entailment"]["precision"], 1.0)
        self.assertAlmostEqual(s["per_class"]["entailment"]["recall"], 0.5)
        self.assertAlmostEqual(s["per_class"]["neutral"]["precision"], 0.5)
        self.assertAlmostEqual(s["per_class"]["neutral"]["f1"], 2 / 3)
        self.assertAlmostEqual(s["per_class"]["contradiction"]["f1"], 0.0)
        self.assertAlmostEqual(s["macro_f1"], 4 / 9)
        self.assertAlmostEqual(s["accuracy"], 0.5)
        self.assertEqual(s["invalid"], 1)
        self.assertEqual(s["confusion"]["contradiction"]["invalid"], 1)

    def test_always_neutral(self):
        # gold 0 1 2, pred 1 1 1: neutral P 1/3, R 1, F1 1/2; others 0 -> Macro-F1 1/6
        self.assertAlmostEqual(ev.label_scores([0, 1, 2], [1, 1, 1])["macro_f1"], 1 / 6)

    def test_absent_class_is_not_averaged(self):
        # gold 0 0, pred 0 None: only class 0 occurs. tp 1, fn 1 -> P 1, R 1/2, F1 2/3.
        # Macro-F1 averages over present classes only (starter rule): 2/3, not 2/9.
        self.assertAlmostEqual(ev.label_scores([0, 0], [0, None])["macro_f1"], 2 / 3)

    def test_valid_label(self):
        self.assertEqual(ev.valid_label(pred("a", 2)), 2)
        self.assertIsNone(ev.valid_label(pred("a", 2, name="neutral")))  # name does not match
        for bad in (None, 3, -1, "0", True, 1.0):
            self.assertIsNone(ev.valid_label({"label": bad, "label_name": "neutral"}), bad)
        self.assertIsNone(ev.valid_label(None))


class CostAndTime(unittest.TestCase):
    def test_p95_nearest_rank(self):
        self.assertEqual(ev.p95(list(range(1, 21))), 19)  # ceil(0.95 * 20) = 19th value
        self.assertEqual(ev.p95([30, 10, 20]), 30)        # ceil(2.85) = 3rd value
        self.assertIsNone(ev.p95([]))

    def test_sums_and_means(self):
        c = ev.cost_scores([pred("a", 0, tokens=100, ms=1000), pred("b", 1, tokens=300, ms=3000)])
        self.assertEqual(c["input_tokens_sum"], 400)
        self.assertEqual(c["input_tokens_mean"], 200)
        self.assertEqual(c["time_ms_mean"], 2000)


class WholeEvaluation(unittest.TestCase):
    def test_tasks_breakdowns_and_invalid_responses(self):
        cases = {c["id"]: c for c in [
            case_b("b1", "de", "de"), case_b("b2", "fr", "de"), case_b("b3", "it", "fr"),
            case_a("a1", "de", "it"),
        ]}
        expected = [{"id": "b1", "label": 0}, {"id": "b2", "label": 1}, {"id": "b3", "label": 2},
                    {"id": "a1", "label": 2}]
        preds = [pred("b1", 0), pred("b2", 1, name="contradiction"),  # b2: name mismatch -> invalid
                 pred("a1", 2), pred("a1", 2),                         # a1 duplicated -> invalid
                 pred("zz", 1)]                                         # unknown; b3 missing
        r = ev.evaluate(preds, expected, cases)
        self.assertEqual(r["issues"], {"missing": 1, "duplicated ids": 1, "unknown ids": 1})
        b = r["tasks"]["B"]
        # Task B: only b1 right. Class 0 F1 1; classes 1 and 2 present in gold with F1 0 -> 1/3
        self.assertAlmostEqual(b["labels"]["macro_f1"], 1 / 3)
        self.assertEqual(b["labels"]["invalid"], 2)
        # b1 de->de same-language; b2 de->fr and b3 fr->it cross-lingual (source->claim)
        self.assertEqual(b["same_vs_cross"]["same-language"]["n"], 1)
        self.assertEqual(b["same_vs_cross"]["cross-lingual"]["n"], 2)
        self.assertEqual(b["by_language_pair"]["de->de"]["accuracy"], 1.0)
        self.assertEqual(b["by_language_pair"]["fr->it"]["invalid"], 1)
        self.assertEqual(b["by_claim_language"]["fr"]["n"], 1)
        self.assertEqual(b["by_source_language"]["de"]["n"], 2)
        # Task A: the only case is a duplicate -> invalid -> Macro-F1 0
        self.assertEqual(r["tasks"]["A"]["labels"]["macro_f1"], 0.0)

    def test_gold_against_itself(self):
        cases = {c["id"]: c for c in [case_b("a"), case_b("b", "fr"), case_b("c", "it", "fr")]}
        expected = [{"id": "a", "label": 0}, {"id": "b", "label": 1}, {"id": "c", "label": 2}]
        r = ev.evaluate([pred(e["id"], e["label"]) for e in expected], expected, cases)
        self.assertEqual(r["tasks"]["B"]["labels"]["macro_f1"], 1.0)


if __name__ == "__main__":
    unittest.main()
