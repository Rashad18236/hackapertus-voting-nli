"""Tests for the context variant "section-route" (src/contexts/section_route.py) and its path in src/cli.py."""

import json
import unittest
from unittest import mock

from src import cli
from src.contexts import embed_e5_small, retrieval, section_route
from tests.test_booklet import booklet_pages
from tests.test_cli import OneVectorEmbedder, run_cli

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


if __name__ == "__main__":
    unittest.main()
