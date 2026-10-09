"""Matching of canary results in scripts/canary_taskb.py."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import canary_taskb  # noqa: E402


class Identical(unittest.TestCase):
    def test_full_answers_must_be_equal(self):
        a = {"answers": {"x": '{"label": 1}', "y": '{"label": 2}'}}
        b = {"answers": {"x": '{"label": 1}', "y": '{"label": 0}'}}
        self.assertEqual(canary_taskb.identical(a, b), 1)

    def test_a_cut_answer_matches_a_full_answer_that_starts_with_it(self):
        cut = {"answers": {"x": '{"label": 2}\n**Reasoning:** The ref'}, "prefix_only": ["x"]}
        longer = {"answers": {"x": '{"label": 2}\n**Reasoning:** The reference text says so.'}}
        shorter = {"answers": {"x": '{"label": 2}\n'}}
        self.assertEqual((canary_taskb.identical(longer, cut), canary_taskb.identical(cut, longer)), (1, 1))
        self.assertEqual((canary_taskb.identical(shorter, cut), canary_taskb.identical(cut, shorter)), (0, 0))


if __name__ == "__main__":
    unittest.main()
