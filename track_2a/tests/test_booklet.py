"""Tests for src/booklet.py (votes and parts of a voting booklet) on a miniature German booklet."""

import re
import unittest

from src import booklet

LINE = "Diese Zeile ist eine volle Zeile im Fliesstext des Heftes und"  # about 60 characters


def paragraph(last):
    """Three full lines and a short last line ending a sentence, as pypdf extracts a booklet paragraph."""
    return f"{LINE}\n{LINE}\n{LINE}\n{last}."


def booklet_pages():
    """Two votes: 'Velowege' (pages 4-5, 8-17) and 'Jagdgesetz' (pages 6-7, 18-25); back cover 26."""
    pages = {n: f"{n}\n{paragraph(f'Seite {n} endet hier')}" for n in range(1, 27)}
    pages[2] = ("Erste Vorlage\nVolksinitiative «Für mehr Velowege»\nIn Kürze 4 – 5\nIm Detail 8\nArgumente 1 2\n"
                "Abstimmungstext 16\nÄnderung des Jagdgesetzes\nIn Kürze 6 – 7\nIm Detail 18\nArgumente 20\n"
                "Abstimmungstext 24\nInhaltsverzeichnis")
    pages[4] = f"4 Erste Vorlage: Velowege\n{paragraph('Der Bund baut heute keine Velowege')}\nIn Kürze"
    pages[5] = ("55\nJa\nFür das Initiativkomitee braucht die Schweiz mehr Velowege, weil viele Menschen\n"
                "mit dem Velo zur Arbeit fahren.\nvelowege-ja.ch\nWollen Sie die Volksinitiative annehmen?\n"
                "Nein\nFür Bundesrat und Parlament geht die Initiative zu weit, weil die Kantone\n"
                "für Velowege zuständig sind.\nadmin.ch/velowege\n120 Nein\n70 Ja\n2 Enthaltungen")
    pages[6] = f"6 Zweite Vorlage: Jagdgesetz\n{paragraph('Das Jagdgesetz wird geändert')}\nIn Kürze"
    pages[8] = ("8 Erste Vorlage: Velowege\nIm Detail\nArgumente Initiativkomitee 1 2\n"
                "Argumente Bundesrat und Parlament 14\nAbstimmungstext 16\n" + paragraph("Velowege im Detail"))
    pages[12] = f"12 Erste Vorlage: Velowege\nArgumente Initiativkomitee\n{paragraph('Das Komitee will Velowege')}"
    pages[14] = f"14\nArgumente Bundesrat und Parlament\n{paragraph('Der Bundesrat lehnt ab')}"
    pages[16] = f"16 Erste Vorlage: Velowege\nAbstimmungstext\n{paragraph('Art. 1 Der Bund fördert Velowege')}"
    pages[18] = f"18 Zweite Vorlage: Jagdgesetz\nIm Detail\n{paragraph('Jagd im Detail')}"
    pages[20] = f"20\nArgumente Referendumskomitee\n{paragraph('Das Komitee lehnt das Gesetz ab')}"
    pages[22] = f"22\nArgumente Bundesrat und Parlament\n{paragraph('Bundesrat und Parlament sind dafür')}"
    pages[24] = f"24\nAbstimmungstext\n{paragraph('Art. 7 Jagdbare Arten')}"
    pages[26] = "Bundesrat und Parlament empfehlen, wie folgt zu stimmen"
    return pages


class Parse(unittest.TestCase):
    def setUp(self):
        self.pages = booklet_pages()
        self.bk = booklet.parse(self.pages)

    def test_votes_and_parts_from_the_contents(self):
        first, second = self.bk.votes
        self.assertTrue(first.ok and second.ok)
        self.assertEqual(first.parts, {"summary": [4, 5], "detail": [8, 9, 10, 11], "committee": [12, 13],
                                       "parliament": [], "council": [14, 15], "law": [16, 17]})
        self.assertEqual(second.parts["summary"], [6, 7])  # up to the first detailed section
        self.assertEqual(second.parts["committee"], [20, 21])  # a referendum committee
        self.assertEqual(second.parts["law"], [24, 25])  # last vote: up to the page before the back cover

    def test_recommendation_boxes_split_per_voice(self):
        boxes = self.bk.votes[0].boxes
        self.assertEqual([p for p, _ in boxes["committee"]], [5])
        self.assertIn("Initiativkomitee braucht", boxes["committee"][0][1])
        self.assertIn("geht die Initiative zu weit", boxes["council"][0][1])
        self.assertIn("120 Nein", boxes["parliament"][0][1])  # Parliament's vote counts

    def test_find_vote_by_name_or_none(self):
        self.assertIs(booklet.find_vote(self.bk, "Änderung des Jagdgesetzes"), self.bk.votes[1])
        self.assertIsNone(booklet.find_vote(self.bk, "Bundesgesetz über die Raumfahrt"))
        self.assertIsNone(booklet.find_vote(None, "Änderung des Jagdgesetzes"))

    def test_no_contents_gives_none(self):
        self.assertIsNone(booklet.parse({1: "Titelseite", 2: "Nur Text ohne Inhaltsverzeichnis"}))

    def test_a_start_page_without_its_heading_gives_no_parts(self):
        self.pages[18] = f"18\n{paragraph('Ohne Überschrift')}"
        second = booklet.parse(self.pages).votes[1]
        self.assertFalse(second.ok)
        self.assertEqual(second.parts, {})
        self.assertIn("no detail heading on page 18", second.problems)


class Paragraphs(unittest.TestCase):
    def test_headers_and_page_numbers_removed_text_verbatim(self):
        paragraphs = booklet.page_paragraphs("12 Erste Vorlage: Velowege\n12\n" + paragraph("Erster Absatz") + "\n"
                                             + paragraph("Zweiter Absatz") + "\nRandtitel")
        self.assertEqual(paragraphs, [paragraph("Erster Absatz"), paragraph("Zweiter Absatz")])

    def test_council_part_starts_with_its_box(self):
        pages = booklet_pages()
        vote = booklet.parse(pages).votes[0]
        got = booklet.part_paragraphs(pages, vote, "council")
        self.assertEqual(got[0][0], 5)  # the box on the summary page comes first
        self.assertIn("Kantone", got[0][1])
        self.assertEqual([p for p, _ in got[1:]], [14, 15])
        self.assertTrue(all(text in pages[p] for p, text in got[1:]))  # verbatim page text


class Session8Patterns(unittest.TestCase):
    """P9 (docs/checks_no_model.md): patterns for the 2018-2019 booklets, added in session 8."""

    def test_council_arguments_without_parliament(self):
        for line in ("argumente bundesrat", "argumente des bundesrates", "argumente bundesrat und parlament",
                     "les arguments du conseil fédéral", "arguments du conseil fédéral et du parlement",
                     "gli argomenti del consiglio federale", "gli argomenti del consiglio federale e del parlamento"):
            with self.subTest(line=line):
                self.assertTrue(re.search(booklet._COUNCIL, line))  # as _sub_starts applies it

    def test_deliberazioni_in_parlamento_is_a_debate(self):
        self.assertTrue(re.fullmatch(booklet._DEBATE, "deliberazioniinparlamento"))  # a heading line, spaces removed
        self.assertTrue(re.search(booklet._DEBATE_LISTED, "le deliberazioni in parlamento 12"))
        self.assertTrue(re.fullmatch(booklet._DEBATE, "dibattitoparlamentare"))  # the older name still works

    def test_debate_heading_counts_as_the_arguments_heading(self):
        for text in ("Argumente", "Dibattito parlamentare", "Le deliberazioni in Parlamento", "Débat au Parlement"):
            with self.subTest(text=text):
                self.assertTrue(booklet._has(text, booklet._HEADINGS["arguments"]))
        self.assertFalse(booklet._has("Im Detail", booklet._HEADINGS["arguments"]))


if __name__ == "__main__":
    unittest.main()
