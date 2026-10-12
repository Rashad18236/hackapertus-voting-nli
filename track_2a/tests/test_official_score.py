"""Tests for scripts/official_score.py (REF SCORE, session 10)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import official_score as osc  # noqa: E402


class RefScore(unittest.TestCase):
    def test_weights_and_reference_values_are_fixed(self):
        self.assertEqual(osc.REF_TOKENS, {"A": 600.0, "B": 800.0})
        self.assertEqual(osc.REF_TIME_S, {"A": 0.05, "B": 0.005})
        self.assertEqual(sum(osc.WEIGHTS["A"].values()), 1.0)
        self.assertAlmostEqual(sum(osc.WEIGHTS["B"].values()), 1.0)

    def test_at_the_reference_values_every_part_is_full(self):
        a = osc.task_score("A", 1.0, 600, 0.05, evidence=1.0)
        b = osc.task_score("B", 1.0, 800, 0.005)
        self.assertEqual((a["K"], a["T"], a["S"]), (1.0, 1.0, 1.0))
        self.assertEqual((b["K"], b["T"], b["S"]), (1.0, 1.0, 1.0))
        self.assertEqual(osc.total(a, b), 1.0)

    def test_ratios_are_capped_and_have_no_floor(self):
        self.assertEqual(osc.ratio(600, 300), 1.0)        # better than the reference: capped at 1
        self.assertAlmostEqual(osc.ratio(0.05, 0.5), 0.1)  # ten times the best time gives 10 %
        self.assertEqual(osc.ratio(600, 0), 0.0)

    def test_example(self):
        a = osc.task_score("A", 0.98, 1200, 0.5, evidence=0.98)
        # 0.5*0.98 + 0.2*0.98 + 0.15*0.1 + 0.15*0.5
        self.assertAlmostEqual(a["S"], 0.49 + 0.196 + 0.015 + 0.075, places=4)
        b = osc.task_score("B", 0.96, 1600, 0.05)
        self.assertAlmostEqual(b["S"], 0.672 + 0.015 + 0.075, places=4)
        self.assertAlmostEqual(osc.total(a, b), round(0.4 * b["S"] + 0.6 * a["S"], 4))
        self.assertIsNone(b["evidence"])

    def test_below_a_minimum_the_submission_is_invalid(self):
        a = osc.task_score("A", 0.59, 600, 0.05, evidence=1.0)
        b = osc.task_score("B", 0.99, 800, 0.005)
        self.assertFalse(a["valid"])
        self.assertEqual(osc.total(a, b), 0.0)
        self.assertFalse(osc.task_score("B", 0.749, 800, 0.005)["valid"])


if __name__ == "__main__":
    unittest.main()
