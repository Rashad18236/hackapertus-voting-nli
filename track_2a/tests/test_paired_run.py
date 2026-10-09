"""The arm order of scripts/paired_run.py: every arm in every position, and after every other arm, equally often."""

import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import paired_run  # noqa: E402


class ArmOrder(unittest.TestCase):
    def test_two_arms_alternate_as_before(self):
        self.assertEqual([paired_run.arm_order(i, 2) for i in range(4)], [[0, 1], [1, 0], [0, 1], [1, 0]])

    def test_four_arms_balanced_latin_square(self):
        orders = [paired_run.arm_order(i, 4) for i in range(4)]
        self.assertEqual(orders, [[0, 1, 3, 2], [1, 2, 0, 3], [2, 3, 1, 0], [3, 0, 2, 1]])
        positions = Counter((pos, arm) for order in orders for pos, arm in enumerate(order))
        self.assertEqual(set(positions.values()), {1})  # each arm once in each position
        follows = Counter((a, b) for order in orders for a, b in zip(order, order[1:]))
        self.assertEqual(len(follows), 12)  # each arm directly after each other arm, once
        self.assertEqual(set(follows.values()), {1})

    def test_three_arms_rotate(self):
        self.assertEqual([paired_run.arm_order(i, 3) for i in range(3)], [[0, 1, 2], [1, 2, 0], [2, 0, 1]])


if __name__ == "__main__":
    unittest.main()
