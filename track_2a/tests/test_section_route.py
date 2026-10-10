"""Tests for the context variant "section-route" (src/contexts/section_route.py) and its path in src/cli.py."""

import json
import unittest
from unittest import mock

from src import cli
from src.contexts import embed_e5_small, retrieval, section_route
from tests.test_booklet import booklet_pages
from tests.test_cli import OneVectorEmbedder, fake_chat, run_cli

VOTE = "Volksinitiative «Für mehr Velowege»"
COUNCIL_CLAIM = "Der Bundesrat ist der Ansicht, dass die Kantone für Velowege zuständig sind."


def case(claim, vote=VOTE):
    return {"id": "a", "vote": vote, "claim": {"text": claim, "language": "de"},
            "booklet": {"path": "booklets/x.pdf", "language": "de"}}


class Route(unittest.TestCase):
    def test_council_claim_gets_the_council_part_as_paragraphs(self):
        part, paragraphs = section_route.route(booklet_pages(), VOTE, COUNCIL_CLAIM)
        self.assertEqual(part, "council")
        self.assertEqual([p for p, _ in paragraphs], [5, 14, 15])  # the box, then the arguments' pages

    def test_long_part_keeps_the_most_similar_paragraphs_in_page_order(self):
        paragraphs = [(p, f"Absatz {p} " + "x" * 1200) for p in range(1, 12)]
        with mock.patch.object(retrieval, "embedder", return_value=OneVectorEmbedder()), \
             mock.patch.object(retrieval, "query_vector", return_value=__import__("numpy").ones(4) / 2.0):
            kept = section_route.most_similar(paragraphs, "claim")
        self.assertEqual(len(kept), section_route.TOP_K)
        self.assertEqual(kept, sorted(kept))

    def test_falls_back_to_embed_e5_small(self):
        pages = booklet_pages()
        for claim, vote in [("Die Schweiz hat 26 Kantone.", VOTE),  # no route
                            (COUNCIL_CLAIM, "Bundesgesetz über die Raumfahrt")]:  # vote not in the booklet
            with self.subTest(claim=claim, vote=vote):
                self.assertIsNone(section_route.route(pages, vote, claim))
                with mock.patch.object(embed_e5_small, "select", return_value=("EMBED", {1: "x"})) as embed:
                    self.assertEqual(section_route.select(pages, vote, claim), ("EMBED", {1: "x"}))
                embed.assert_called_once()

    def test_evidence_is_the_cited_paragraphs_verbatim(self):
        paragraphs = [(5, "Box\ntext"), (14, "Erster\nAbsatz"), (15, "Zweiter")]
        self.assertEqual(section_route.evidence_items(paragraphs, [2, 9, 2, 1]),
                         [{"page": 14, "text": "Erster\nAbsatz"}, {"page": 5, "text": "Box\ntext"}])


class Cli(unittest.TestCase):
    def run_case(self, claim, answer):
        seen = []
        with mock.patch.object(cli.parse, "load_pages", return_value=booklet_pages()), \
             mock.patch.object(cli.Path, "is_file", return_value=True), \
             mock.patch.object(embed_e5_small, "select_chunks", return_value=[(14, "chunk")]):
            code, out = run_cli([json.dumps(case(claim))], [answer], ["--context-a", "section-route"], seen)
        self.assertEqual(code, 0)
        return out[0], seen[0]

    def test_routed_case_cites_paragraphs(self):
        out, messages = self.run_case(COUNCIL_CLAIM, '{"paragraphs": [1], "label": 0}')
        self.assertIn("PART: the arguments and recommendation of the Federal Council", messages[1]["content"])
        self.assertIn("[1] Nein Für Bundesrat und Parlament", messages[1]["content"])
        self.assertEqual(out["label"], 0)
        self.assertEqual(out["evidence"][0]["page"], 5)
        self.assertIn("zuständig sind.", out["evidence"][0]["text"])

    def test_unrouted_case_runs_as_embed_e5_small(self):
        out, messages = self.run_case("Die Schweiz hat 26 Kantone.", '{"pages": [14], "label": 0}')
        self.assertIn("=== PAGE 14 ===\nchunk", messages[1]["content"])  # embed-e5-small's prompt
        self.assertEqual(out["evidence"][0]["page"], 14)


class RoutingErrors(unittest.TestCase):
    """A booklet that makes the parser raise must still get an embed-e5-small answer (session 7)."""

    @staticmethod
    def broken_booklets():
        missing = booklet_pages()
        del missing[13]          # a page number missing inside the vote's pages: KeyError in the parser
        none_text = booklet_pages()
        none_text[9] = None      # a page without text: TypeError in the parser
        return {"missing page": missing, "None as page text": none_text}

    def test_the_parser_really_raises_on_these_booklets(self):
        for name, pages in self.broken_booklets().items():
            with self.subTest(name), self.assertRaises(Exception):
                section_route.route(pages, VOTE, COUNCIL_CLAIM)

    def test_routing_error_runs_the_case_as_embed_e5_small(self):
        for name, pages in self.broken_booklets().items():
            with self.subTest(name):
                seen = []
                with mock.patch.object(cli.parse, "load_pages", return_value=pages), \
                     mock.patch.object(cli.Path, "is_file", return_value=True), \
                     mock.patch.object(cli.llm, "chat", fake_chat(['{"pages": [14], "label": 2}'], seen)), \
                     mock.patch.object(embed_e5_small, "select_chunks", return_value=[(14, "chunk")]), \
                     self.assertLogs("cli", level="WARNING") as logs:
                    resp, status, raw = cli.predict(case(COUNCIL_CLAIM), ".", cli.Settings(context_a="section-route"))
                self.assertEqual(len(seen), 1)  # the model was called: no neutral answer without a call
                self.assertIn("=== PAGE 14 ===\nchunk", seen[0][1]["content"])  # embed-e5-small's prompt
                self.assertEqual((resp["label"], status, raw["fallback"]), (2, "ok", "embed-e5-small"))
                self.assertEqual(resp["evidence"][0]["page"], 14)
                self.assertIn("route_error", raw)
                self.assertIn("routing failed", " ".join(logs.output))

    def test_the_run_log_counts_routing_errors(self):
        pages = self.broken_booklets()["missing page"]
        with mock.patch.object(cli.parse, "load_pages", return_value=pages), \
             mock.patch.object(cli.Path, "is_file", return_value=True), \
             mock.patch.object(embed_e5_small, "select_chunks", return_value=[(14, "chunk")]), \
             self.assertLogs("cli", level="INFO") as logs:
            code, out = run_cli([json.dumps(case(COUNCIL_CLAIM))], ['{"pages": [14], "label": 0}'],
                                ["--context-a", "section-route"])
        self.assertEqual((code, out[0]["label"]), (0, 0))
        self.assertIn("Routing failed and the case ran as the fallback variant: 1", " ".join(logs.output))


class RepeatedEvidence(unittest.TestCase):
    """Session 8 (P7): a cited paragraph whose text equals one already taken gives no second item."""

    def test_same_text_cited_twice_gives_one_item(self):
        paragraphs = [(3, "Art. 1 Der Bund regelt die Jagd."), (4, "Die Kantone vollziehen."),
                      (7, "Art. 1 Der Bund regelt die Jagd."), (8, "Die Kantone vollziehen es.")]
        items = section_route.evidence_items(paragraphs, [1, 3, 2, 4])
        self.assertEqual(items, [{"page": 3, "text": "Art. 1 Der Bund regelt die Jagd."},
                                 {"page": 4, "text": "Die Kantone vollziehen."},
                                 {"page": 8, "text": "Die Kantone vollziehen es."}])

    def test_different_texts_on_one_page_are_all_kept(self):
        paragraphs = [(3, "Erster Satz."), (3, "Zweiter Satz.")]
        self.assertEqual(len(section_route.evidence_items(paragraphs, [1, 2])), 2)


class EvidenceHalves(unittest.TestCase):
    """Session 9 (A2): halves of the cited paragraphs fill the evidence up to five items."""

    def test_split_at_the_sentence_end_nearest_the_middle(self):
        self.assertEqual(section_route.split_in_half("Erster Satz hier. Zweiter Satz da. Dritter Satz dort."),
                         ["Erster Satz hier. Zweiter Satz da.", "Dritter Satz dort."])
        self.assertEqual(section_route.split_in_half("Kein Satzende in diesem Absatz"), [])
        self.assertEqual(section_route.split_in_half("Nur ein Satz."), [])

    def test_halves_follow_the_cited_paragraphs_up_to_five_items(self):
        paragraphs = [(3, "A eins. B zwei. C drei. D vier."), (4, "E fünf. F sechs."), (5, "G sieben.")]
        items = section_route.evidence_items(paragraphs, [1, 2, 3], halves=True)
        self.assertEqual([i["text"] for i in items], ["A eins. B zwei. C drei. D vier.", "E fünf. F sechs.",
                                                      "G sieben.", "A eins. B zwei.", "C drei. D vier."])
        self.assertEqual([i["page"] for i in items], [3, 4, 5, 3, 3])
        for item in items:  # every half is a verbatim piece of its paragraph
            self.assertTrue(any(item["text"] in text for _, text in paragraphs))

    def test_without_halves_nothing_is_added_and_present_texts_are_skipped(self):
        paragraphs = [(3, "A eins. B zwei.")]
        self.assertEqual(len(section_route.evidence_items(paragraphs, [1])), 1)
        self.assertEqual(len(section_route.evidence_items(paragraphs, [1], halves=True)), 3)
        self.assertEqual(section_route.evidence_items([(3, "A eins.")], [1], halves=True), [{"page": 3, "text": "A eins."}])


if __name__ == "__main__":
    unittest.main()
