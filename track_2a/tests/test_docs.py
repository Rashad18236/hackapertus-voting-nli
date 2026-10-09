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


class CanaryMark(unittest.TestCase):
    canary = {"t1": {"answers": {"a": "x", "b": "y"}}, "t2": {"answers": {"a": "x", "b": "y"}},
              "t3": {"answers": {"a": "x", "b": "z"}}}

    def test_changed_only_when_the_checks_before_and_after_differ(self):
        mark = lambda before, after: build_docs.changed_during_run(  # noqa: E731
            {"canary": {"before": before, "after": after}}, self.canary)
        self.assertEqual((mark("t1", "t2"), mark("t1", "t3")), (False, True))
        self.assertFalse(build_docs.changed_during_run({}, self.canary))

    def test_unknown_canary_time_is_a_problem(self):
        run = {"person": "p", "date": "2026-10-09", "start_utc": "02:30", "kind": "stopped", "code": "c", "task": "A",
               "cases": "", "setup": "", "format": "", "model": "", "endpoint": "", "notes": "../README.md",
               "results": None, "canary": {"before": "t1", "after": "t9"}}
        problems = build_docs.check_run("x", run, set(), self.canary)
        self.assertIn("x: canary after 't9' is not in docs/canary_results.jsonl", problems)
        self.assertNotIn("x: canary before 't1' is not in docs/canary_results.jsonl", problems)


if __name__ == "__main__":
    unittest.main()
