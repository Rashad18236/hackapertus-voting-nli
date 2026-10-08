"""Tests for src/contexts/vote_section.py (pages of the ballot named in `vote`)."""

import unittest

from src.contexts import vote_section


class VoteSection(unittest.TestCase):
    # A miniature two-ballot booklet: front matter, a section on hunting (pages 3-7),
    # a section on fighter jets (pages 8-10). Page 5 is an "arguments" page whose
    # header does not name the ballot; gap filling must keep it.
    PAGES = {
        1: "Votation populaire Modification de la loi sur la chasse Arrêté fédéral relatif aux avions de combat",
        2: "Sommaire et informations pratiques",
        3: "3 Premier objet : loi sur la chasse Modification de la loi sur la chasse Contexte et projet",
        4: "4 Premier objet : loi sur la chasse Les loups et la régulation des espèces protégées",
        5: "5 Arguments du comité référendaire",
        6: "6 Premier objet : loi sur la chasse Arguments du Conseil fédéral",
        7: "7 Texte soumis au vote",
        8: "8 Second objet : avions de combat Arrêté fédéral relatif aux avions de combat",
        9: "9 Second objet : avions de combat Coûts et calendrier",
        10: "10 Arguments du comité",
    }
    VOTE = "Modification de la loi sur la chasse"

    def test_selects_the_ballot_section(self):
        sel = vote_section.section_pages(self.PAGES, self.VOTE)
        self.assertTrue({3, 4, 5, 6, 7} <= set(sel))      # the whole section, page 5 by gap filling
        self.assertNotIn(9, sel)                         # the other ballot's detail pages stay out

    def test_select_keeps_original_page_numbers(self):
        text, shown = vote_section.select(self.PAGES, self.VOTE, "any claim")
        self.assertEqual(shown[4], self.PAGES[4])
        self.assertEqual(list(shown), sorted(shown))
        self.assertIn("=== PAGE 4 ===", text)

    def test_no_match_falls_back_to_all_pages(self):
        self.assertEqual(vote_section.section_pages(self.PAGES, "Völlig andere Vorlage zum Thema Velowege"),
                         sorted(self.PAGES))
        self.assertEqual(vote_section.section_pages(self.PAGES, "   "), sorted(self.PAGES))


if __name__ == "__main__":
    unittest.main()
