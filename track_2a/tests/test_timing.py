"""Tests for src/timing.py (session 11, step 4a: phase timing, off by default)."""

import io
import json
import unittest
from unittest import mock

from src import timing


class Timing(unittest.TestCase):
    def test_off_by_default_records_nothing(self):
        with mock.patch.object(timing, "ENABLED", False), mock.patch.dict(timing._totals, clear=True):
            with timing.phase("pdf_read"):
                pass
            timing.add("embed", 1.0)
            self.assertEqual(timing._totals, {})

    def test_on_adds_up_seconds_and_reports_one_line(self):
        with mock.patch.object(timing, "ENABLED", True), mock.patch.dict(timing._totals, clear=True), \
             mock.patch.dict(timing._counts, clear=True), mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            timing.add("embed", 1.5)
            timing.add("embed", 0.5)
            with timing.phase("pdf_read"):
                pass
            timing.report("lane")
        line = err.getvalue().strip()
        self.assertTrue(line.startswith("PHASES "))
        record = json.loads(line[7:])
        self.assertEqual((record["role"], record["seconds"]["embed"], record["counts"]["embed"]), ("lane", 2.0, 2))
        self.assertIn("pdf_read", record["seconds"])
        self.assertGreater(record["max_rss_mib"], 0)
