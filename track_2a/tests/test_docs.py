"""docs/results.md and docs/decisions.md must equal what scripts/build_docs.py generates,
and every run.json must agree with its run's own files."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_docs  # noqa: E402


class GeneratedDocs(unittest.TestCase):
    def setUp(self):
        self.files, self.problems = build_docs.build()

    def test_every_run_json_agrees_with_its_files(self):
        self.assertEqual(self.problems, [])

    def test_generated_pages_are_up_to_date(self):
        for path, text in self.files.items():
            with self.subTest(path=path.name):
                self.assertEqual(path.read_text(encoding="utf-8"), text,
                                 f"{path.name} is out of date: run python3 scripts/build_docs.py")


if __name__ == "__main__":
    unittest.main()
