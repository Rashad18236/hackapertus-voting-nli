"""Tests for src/ap_parse.py and cli.ap_route (session 11, step 3: Apertus in the parsing roles; off by default)."""

import json
import unittest
from unittest import mock

from src import ap_parse, cli, llm
from tests.test_booklet import booklet_pages


def result(text, input_tokens=100, output_tokens=20):
    return llm.LLMResult(text=text, input_tokens=input_tokens, output_tokens=output_tokens, elapsed_ms=100)


GOOD_ENTRIES = [{"title": "Volksinitiative «Für mehr Velowege»", "summary": 4, "detail": 8, "arguments": 12, "law": 16},
                {"title": "Änderung des Jagdgesetzes", "summary": 6, "detail": 18, "arguments": 20, "law": 24}]


class Structure(unittest.TestCase):
    def setUp(self):
        ap_parse._structures.clear()

    def test_entries_from_the_answer_and_one_call_per_booklet(self):
        answer = json.dumps({"votes": GOOD_ENTRIES})
        with mock.patch.object(llm, "chat", return_value=result(answer)) as chat:
            entries, call = ap_parse.structure(booklet_pages())
            again, call2 = ap_parse.structure(booklet_pages())
        self.assertEqual(chat.call_count, 1)
        self.assertEqual(entries, GOOD_ENTRIES)
        self.assertEqual(again, GOOD_ENTRIES)
        self.assertTrue(call["first"])
        self.assertFalse(call2["first"])  # cached: no second request, no second token count
        self.assertEqual((call["input_tokens"], call["output_tokens"]), (100, 20))
        self.assertIn("=== PAGE 2 ===", chat.call_args[0][0][1]["content"])

    def test_an_unreadable_answer_gives_no_entries(self):
        with mock.patch.object(llm, "chat", return_value=result("no json")):
            entries, call = ap_parse.structure(booklet_pages())
        self.assertIsNone(entries)
        self.assertEqual(call["parse_reason"], "unreadable structure answer")

    def test_entries_pass_the_parser_s_own_checks(self):
        parsed = ap_parse.booklet_from_entries(booklet_pages(), GOOD_ENTRIES)
        self.assertTrue(all(v.ok for v in parsed.votes))
        self.assertEqual(parsed.votes[0].parts["council"], [14, 15])

    def test_a_wrong_page_from_apertus_is_not_used(self):
        wrong = [dict(GOOD_ENTRIES[0], detail=9), GOOD_ENTRIES[1]]  # page 9 has no "Im Detail" heading
        first = ap_parse.booklet_from_entries(booklet_pages(), wrong).votes[0]
        self.assertFalse(first.ok)
        self.assertNotIn("detail", first.valid)
        self.assertIn("no detail heading on page 9", first.problems)


class Claim(unittest.TestCase):
    def test_part_and_statement(self):
        answer = json.dumps({"part": "council", "statement": "Die Kantone sind zuständig."})
        with mock.patch.object(llm, "chat", return_value=result(answer)) as chat:
            part, statement, call = ap_parse.claim("Die Landesregierung meint, die Kantone seien zuständig.", "de")
        self.assertEqual((part, statement), ("council", "Die Kantone sind zuständig."))
        self.assertIn("LANGUAGE: de", chat.call_args[0][0][1]["content"])

    def test_none_and_failures(self):
        with mock.patch.object(llm, "chat", return_value=result(json.dumps({"part": "none", "statement": "x"}))):
            self.assertEqual(ap_parse.claim("x", "de")[:2], (None, "x"))
        with mock.patch.object(llm, "chat", side_effect=llm.LLMError("down")):
            part, statement, call = ap_parse.claim("x", "de")
        self.assertEqual((part, statement), (None, None))
        self.assertIn("down", call["error"])


VOTE = "Volksinitiative «Für mehr Velowege»"
REWORDED = "Die Landesregierung meint, die Kantone seien für Velowege zuständig."  # the rules find no part


class ApRoute(unittest.TestCase):
    def setUp(self):
        ap_parse._structures.clear()

    def route(self, settings, answers):
        raw = {"id": "a"}
        with mock.patch.object(llm, "chat", side_effect=[result(a) for a in answers]) as chat:
            routed, found = cli.ap_route(booklet_pages(), VOTE, REWORDED, "de", raw, settings)
        return routed, found, raw, chat.call_count

    def test_ap_part_after_the_rules_routes_a_claim_the_rules_miss(self):
        settings = cli.Settings(ap_part_a="after-rules")
        routed, found, raw, calls = self.route(settings, [json.dumps({"part": "council", "statement": "s"})])
        self.assertEqual(routed[0], "council")
        self.assertEqual(calls, 1)
        self.assertEqual(raw["ap_tokens"], [100, 20])
        self.assertEqual(raw["ap_part"]["rules"], None)

    def test_ap_part_none_leaves_the_case_to_the_fallback(self):
        routed, found, raw, calls = self.route(cli.Settings(ap_part_a="after-rules"),
                                               [json.dumps({"part": "none", "statement": "s"})])
        self.assertIsNone(routed)
        self.assertIsNotNone(found[1])  # the vote is found: VW can use it

    def test_rules_first_no_call_when_they_match(self):
        raw = {"id": "a"}
        with mock.patch.object(llm, "chat") as chat:
            routed, _ = cli.ap_route(booklet_pages(), VOTE, "Der Bundesrat meint, die Kantone seien zuständig.", "de",
                                     raw, cli.Settings(ap_part_a="after-rules"))
        chat.assert_not_called()
        self.assertEqual(routed[0], "council")

    def test_ap_all_uses_apertus_for_part_and_structure(self):
        settings = cli.Settings(ap_part_a="all", ap_structure_a="all")
        routed, found, raw, calls = self.route(settings, [json.dumps({"part": "council", "statement": "s"}),
                                                          json.dumps({"votes": GOOD_ENTRIES})])
        self.assertEqual(routed[0], "council")
        self.assertEqual(calls, 2)
        self.assertEqual(raw["ap_tokens"], [200, 40])
        self.assertTrue(raw["ap_structure"]["vote_found"])

    def test_add_ap_tokens_to_the_metrics(self):
        resp = cli.response("a", 1, 10, 2)
        cli.add_ap_tokens(resp, {"ap_tokens": [5, 1]})
        self.assertEqual((resp["metrics"]["input_tokens"], resp["metrics"]["output_tokens"]), (15, 3))


if __name__ == "__main__":
    unittest.main()


class AskPartAfterRules(unittest.TestCase):
    """Session 11, step 3: AP-part after the rules on the worker-process path (asked in complete())."""

    settings = cli.Settings(ap_part_a="after-rules")

    def test_the_mode_keeps_the_worker_processes(self):
        self.assertTrue(cli.ask_part_after_rules(self.settings))
        self.assertFalse(cli.ap_in_prepare(self.settings))
        self.assertTrue(cli.ap_in_prepare(cli.Settings(ap_part_a="all")))
        self.assertTrue(cli.ap_in_prepare(cli.Settings(ap_part_a="after-rules", ap_structure_a="after-parser")))
        # session 12: AP-structure asked after the parser (main process) keeps AP-part after the rules
        both = cli.Settings(ap_part_a="after-rules", ap_structure_a="ask-after-parser")
        self.assertTrue(cli.ask_part_after_rules(both))
        self.assertFalse(cli.ap_in_prepare(both))

    def test_candidates_only_when_the_rules_name_no_part(self):
        raw = {}
        candidates = cli.part_candidates(booklet_pages(), VOTE, REWORDED, raw, self.settings)
        self.assertIn("council", candidates)
        self.assertEqual(candidates["council"][0], "council")
        self.assertEqual(cli.part_candidates(booklet_pages(), VOTE, "Der Bundesrat meint, x.", {}, self.settings), {})
        self.assertEqual(cli.part_candidates(booklet_pages(), "Eine Vorlage, die es nicht gibt", REWORDED, {},
                                             self.settings), {})

    def ask(self, answers):
        candidates = cli.part_candidates(booklet_pages(), VOTE, REWORDED, {}, self.settings)
        fallback = cli.finished("a", {"fallback": "embed-e5-small"}, cli.response("a", 1), "fallback")
        p = cli.Prepared("a", {"id": "a"}, kind="A-ask-part", vote=VOTE, claim_text=REWORDED,
                         ask=("de", candidates, fallback))
        with mock.patch.object(llm, "chat", side_effect=[result(a) for a in answers]) as chat:
            resp, status, raw = cli.complete(p, self.settings)
        return resp, status, raw, chat

    def test_apertus_names_a_valid_part(self):
        resp, status, raw, chat = self.ask([json.dumps({"part": "council", "statement": "s"}),
                                            json.dumps({"paragraphs": [1], "label": 0})])
        self.assertEqual(chat.call_count, 2)
        self.assertIn("Federal Council", chat.call_args_list[1][0][0][1]["content"])  # the council's PART line
        self.assertEqual((raw["route"], raw["ap_part"]["apertus"], resp["label"]), ("council", "council", 0))
        self.assertEqual((resp["metrics"]["input_tokens"], resp["metrics"]["output_tokens"]), (200, 40))
        self.assertTrue(resp["evidence"])

    def test_none_goes_to_the_fallback_with_the_call_counted(self):
        resp, status, raw, chat = self.ask([json.dumps({"part": "none", "statement": "s"})])
        self.assertEqual(chat.call_count, 1)
        self.assertEqual((status, raw["fallback"], resp["label"]), ("fallback", "embed-e5-small", 1))
        self.assertEqual(resp["metrics"]["input_tokens"], 100)

    def test_a_failed_call_goes_to_the_fallback(self):
        candidates = {"council": ("council", [(14, "x")])}
        fallback = cli.finished("a", {}, cli.response("a", 1), "fallback")
        p = cli.Prepared("a", {"id": "a"}, kind="A-ask-part", vote=VOTE, claim_text=REWORDED,
                         ask=("de", candidates, fallback))
        with mock.patch.object(llm, "chat", side_effect=llm.LLMError("down")):
            resp, status, raw = cli.complete(p, self.settings)
        self.assertEqual((status, resp["label"]), ("fallback", 1))
        self.assertIn("down", raw["ap_calls"][0]["error"])
