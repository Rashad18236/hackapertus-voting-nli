"""Tests for src/context.py (page selection for task A)."""

import unittest

from src import context


class Full(unittest.TestCase):
    def test_full_returns_every_page_in_order(self):
        pages = {3: "c", 1: "a", 2: "b"}
        self.assertEqual(list(context.select_pages(pages, "any vote", "full")), [1, 2, 3])

    def test_unknown_mode_is_an_error(self):
        with self.assertRaises(ValueError):
            context.select_pages({1: "a"}, "v", "nonsense")


if __name__ == "__main__":
    unittest.main()


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
        sel = context.vote_section(self.PAGES, self.VOTE)
        self.assertTrue({3, 4, 5, 6, 7} <= set(sel))      # the whole section, page 5 by gap filling
        self.assertNotIn(9, sel)                         # the other ballot's detail pages stay out

    def test_select_pages_keeps_original_page_numbers(self):
        sel = context.select_pages(self.PAGES, self.VOTE, "vote-section")
        self.assertEqual(sel[4], self.PAGES[4])
        self.assertEqual(list(sel), sorted(sel))

    def test_no_match_falls_back_to_all_pages(self):
        self.assertEqual(context.vote_section(self.PAGES, "Völlig andere Vorlage zum Thema Velowege"), sorted(self.PAGES))
        self.assertEqual(context.vote_section(self.PAGES, "   "), sorted(self.PAGES))
