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

    def test_a_start_page_without_its_heading_loses_only_that_part(self):
        # Session 11, per-part validity: before, the whole vote lost its parts.
        self.pages[18] = f"18\n{paragraph('Ohne Überschrift')}"
        second = booklet.parse(self.pages).votes[1]
        self.assertFalse(second.ok)
        self.assertIn("no detail heading on page 18", second.problems)
        self.assertNotIn("detail", second.valid)
        self.assertNotIn("detail", second.parts)
        self.assertEqual(second.valid, {"summary", "committee", "parliament", "council", "law"})
        self.assertEqual(second.parts["council"], [22, 23])

    def test_a_vote_that_passes_has_every_part_valid(self):
        self.assertEqual([v.valid for v in self.bk.votes], [set(booklet.PARTS)] * 2)


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


class PerPartValidity(unittest.TestCase):
    """Session 11: a vote keeps every part that passes its own checks when another part fails."""

    def test_contents_entry_without_arguments(self):
        # General cause (seen in one 2025 booklet): the text layer drops a vote's "Argumente" contents line. The
        # arguments start where the detail page's list and the page headings put the first sub-section.
        pages = booklet_pages()
        pages[2] = pages[2].replace("Argumente 20\n", "")
        pages[18] = ("18 Zweite Vorlage: Jagdgesetz\nIm Detail\nArgumente Referendumskomitee 20\n"
                     "Argumente Bundesrat und Parlament 22\n" + paragraph("Jagd im Detail"))
        second = booklet.parse(pages).votes[1]
        self.assertIn("contents entry without arguments", second.problems)
        self.assertFalse(second.ok)
        self.assertEqual(second.valid, {"summary", "detail", "committee", "parliament", "council", "law"})
        self.assertEqual((second.parts["detail"], second.parts["committee"], second.parts["council"]),
                         ([18, 19], [20, 21], [22, 23]))

    def test_without_arguments_entry_and_without_a_sub_section_detail_is_not_guessed(self):
        pages = booklet_pages()
        pages[2] = pages[2].replace("Argumente 20\n", "")
        pages[20] = f"20\n{paragraph('Kein Titel')}"
        pages[22] = f"22\n{paragraph('Kein Titel')}"
        second = booklet.parse(pages).votes[1]
        self.assertEqual(second.valid, {"summary", "law"})  # the detailed section's end is unknown

    def test_a_lost_arguments_heading_confirmed_by_the_per_vote_list(self):
        # General cause: the text layer can lose a heading. The contents entry and the detail page's list of
        # sub-sections name the same page, so the arguments' start counts as confirmed.
        pages = booklet_pages()
        pages[12] = f"12 Erste Vorlage: Velowege\n{paragraph('Das Komitee will Velowege')}"  # heading lost
        first = booklet.parse(pages).votes[0]
        self.assertFalse(first.ok)
        self.assertEqual(first.valid, set(booklet.PARTS))
        self.assertEqual(first.parts["committee"], [12, 13])
        self.assertIn("arguments start on page 12 confirmed by the per-vote list only", first.problems)


def old_layout_pages(spaced=False):
    """A miniature booklet in the older layout (until mid-2018): one contents entry per vote and its legal text;
    inside the vote's pages, each part starts on a page whose heading names it (not always the first line)."""
    pages = {n: f"{n}\n{paragraph(f'Seite {n} endet hier')}" for n in range(1, 17)}
    seiten = "Sei ten" if spaced else "Seiten"
    pages[3] = (f"3\nDarüber wird abgestimmt\nVolksinitiative «Für mehr Velowege»\n{paragraph('Die Initiative will')}\n"
                f"Informationen zur Vorlage {seiten} 4–1 1\nDer Abstimmungstext Seite 8\n"
                f"Bundesgesetz über die Jagd\nInformationen zur Vorlage {seiten} 12–15\nDer Abstimmungstext Seite 14")
    pages[4] = f"4\nErste Vorlage\nVolksinitiative «Für mehr Velowege»\n{paragraph('Abstimmungsfrage')}"
    pages[5] = f"5\n{paragraph('Im Kasten steht')}\nDas Wichtigste in Kürze\n{paragraph('Velowege sind gut')}"
    pages[6] = f"6\nDie Vorlage im Detail\n{paragraph('Velowege im Detail')}"
    pages[8] = f"8\n§\nAbstimmungstext\n{paragraph('Art. 1 Velowege')}"
    pages[9] = f"9\nDie Beratungen im Parlament\n{paragraph('Das Parlament hat beraten')}"
    pages[10] = f"10\nDie Argumente des Initiativkomitees\n{paragraph('Das Komitee will Velowege')}"
    pages[11] = f"11\n{paragraph('Der Bundesrat lehnt ab')}\nDie Argumente von Bundesrat und Parlament"
    pages[12] = f"12\nZweite Vorlage\nDas Wichtigste in Kürze\n{paragraph('Jagd kurz')}"
    pages[13] = f"13\nDie Vorlage im Detail\n{paragraph('Jagd im Detail')}"
    pages[14] = f"14\n§\nAbstimmungstext\n{paragraph('Art. 7 Jagdbare Arten')}"
    pages[15] = f"15\nDie Argumente des Bundesrates\n{paragraph('Der Bundesrat ist dafür')}"
    return pages


class OldLayout(unittest.TestCase):
    """Session 11: booklets until mid-2018 (one contents entry per vote; parts found by their page headings)."""

    def test_votes_and_parts(self):
        parsed = booklet.parse(old_layout_pages())
        first, second = parsed.votes
        self.assertTrue(first.ok and second.ok)
        self.assertEqual({k: v for k, v in first.parts.items() if v},
                         {"summary": [4, 5], "detail": [6, 7], "law": [8], "parliament": [9], "committee": [10],
                          "council": [11]})
        self.assertEqual(second.parts["council"], [15])
        self.assertEqual(second.parts["committee"], [])  # no committee for this vote
        self.assertIs(booklet.find_vote(parsed, "Bundesgesetz über die Jagd"), second)

    def test_stray_spaces_in_the_contents_line(self):
        # General cause (2016 booklets): the text layer puts spaces inside words and numbers ("Sei ten 4–1 1").
        votes = booklet.parse(old_layout_pages(spaced=True)).votes
        self.assertEqual([v.entry["block"] for v in votes], [(4, 11), (12, 15)])

    def test_a_missing_heading_leaves_the_other_parts_valid(self):
        pages = old_layout_pages()
        pages[13] = f"13\n{paragraph('Ohne Überschrift')}"
        second = booklet.parse(pages).votes[1]
        self.assertFalse(second.ok)
        self.assertIn("no detail heading in pages 12-15", second.problems)
        self.assertEqual(second.valid, {"summary", "law", "council"})

    def test_a_heading_in_the_running_text_does_not_count(self):
        self.assertIsNone(booklet._old_heading("10\nWie die Vorlage im Detail zeigt, ist das so."))
        self.assertEqual(booklet._old_heading("10\nText\nDie Vorlage im Detail"), "detail")


if __name__ == "__main__":
    unittest.main()
