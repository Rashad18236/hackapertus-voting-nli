"""Tests for src/evaluate.py with cases small enough to check on paper.

Run from track_2a/:  python3 -m pytest tests   (or: python3 -m unittest discover tests)
"""

import unittest

from src import evaluate as ev


def pred(case_id, label, evidence=(), tokens=100, ms=1000, **extra):
    return {"id": case_id, "label": label, "evidence": [{"text": t} for t in evidence],
            "metrics": {"input_tokens": tokens, "output_tokens": 10, "inference_time_ms": ms}, **extra}


def gold(case_id, label, cl="de", rl="de", evidence=None):
    return {"id": case_id, "label": label, "evidence": evidence,
            "claim_language": cl, "reference_language": rl}


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
        self.assertEqual(s["confusion"]["entailment"]["neutral"], 1)

    def test_perfect(self):
        s = ev.label_scores([0, 1, 2], [0, 1, 2])
        self.assertEqual(s["macro_f1"], 1.0)

    def test_always_neutral(self):
        # gold 0 1 2, pred 1 1 1: neutral P 1/3, R 1, F1 1/2; others 0 -> Macro-F1 1/6
        s = ev.label_scores([0, 1, 2], [1, 1, 1])
        self.assertAlmostEqual(s["macro_f1"], 1 / 6)

    def test_valid_label(self):
        self.assertEqual(ev.valid_label(2), 2)
        for bad in (None, 3, -1, "0", True, 1.0):
            self.assertIsNone(ev.valid_label(bad), bad)


class Evidence(unittest.TestCase):
    def test_normalise(self):
        self.assertEqual(ev.normalise_evidence("Abstim-\nmung  ist\tGUT "), "abstimmung ist gut")
        # A hyphen that is not at a line break stays.
        self.assertEqual(ev.normalise_evidence("Covid-19 Gesetz"), "covid-19 gesetz")

    def test_overlap_f1(self):
        # pred 4 words, gold 6 words, common: der, lehnt, ab = 3
        # P 3/4, R 3/6, F1 = 2 * 0.375 / 1.25 = 0.6
        self.assertAlmostEqual(ev.overlap_f1("der Rat lehnt ab", "Der Bundesrat lehnt die Initiative ab"), 0.6)
        self.assertEqual(ev.overlap_f1("", "anything"), 0.0)
        self.assertEqual(ev.overlap_f1("a b", "c d"), 0.0)

    def test_exact_match_after_normalising(self):
        golds = [gold("a", 0, evidence="Der Bundesrat empfiehlt die Ab-\nlehnung."),
                 gold("b", 2, evidence="Das Gesetz tritt 2025 in Kraft."),
                 gold("c", 1)]  # no gold evidence: not scored
        preds = {"a": pred("a", 0, ["der Bundesrat  empfiehlt die Ablehnung."]),
                 "b": pred("b", 2, ["Das Gesetz tritt in Kraft."])}
        s = ev.evidence_scores(golds, preds)
        self.assertEqual(s["n_with_gold_evidence"], 2)
        self.assertAlmostEqual(s["exact_match"], 0.5)
        # b: pred 5 words, gold 6 words, all 5 shared -> P 1, R 5/6, F1 10/11
        self.assertAlmostEqual(s["overlap_f1"], (1.0 + 10 / 11) / 2)

    def test_no_gold_evidence_gives_none(self):
        s = ev.evidence_scores([gold("a", 0)], {"a": pred("a", 0, ["x"])})
        self.assertIsNone(s["exact_match"])


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
    def test_missing_and_failed_predictions_are_wrong(self):
        golds = [gold("a", 0), gold("b", 1, cl="fr"), gold("c", 2, cl="it", rl="fr")]
        preds = [pred("a", 0), pred("b", None, parse_failure=True), pred("z", 1)]  # c missing, z extra
        r = ev.evaluate(preds, golds)
        self.assertEqual(r["missing_predictions"], 1)
        self.assertEqual(r["parse_failures"], 1)
        self.assertEqual(r["extra_predictions"], 1)
        self.assertEqual(r["labels"]["invalid"], 2)
        # only "a" right: class 0 F1 1, others 0 -> Macro-F1 1/3
        self.assertAlmostEqual(r["labels"]["macro_f1"], 1 / 3)
        # a: de->de, b: fr->de, c: it->fr. Same-language = {a}, cross = {b, c}
        self.assertEqual(r["same_vs_cross"]["same-language"]["n"], 1)
        self.assertEqual(r["same_vs_cross"]["cross-lingual"]["n"], 2)
        self.assertEqual(r["by_language_pair"]["de->de"]["accuracy"], 1.0)
        self.assertEqual(r["by_language_pair"]["it->fr"]["invalid"], 1)

    def test_gold_against_itself(self):
        golds = [gold("a", 0, evidence="x y"), gold("b", 1), gold("c", 2, cl="fr", evidence="z")]
        preds = [{"id": g["id"], "label": g["label"],
                  "evidence": [{"text": t} for t in ev.gold_passages(g["evidence"])]} for g in golds]
        r = ev.evaluate(preds, golds)
        self.assertEqual(r["labels"]["macro_f1"], 1.0)
        self.assertEqual(r["evidence"]["exact_match"], 1.0)
        self.assertEqual(r["evidence"]["overlap_f1"], 1.0)


if __name__ == "__main__":
    unittest.main()
