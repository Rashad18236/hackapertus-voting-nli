"""Session 10, step 8: a vote name the title match cannot place is placed by meaning (e5) if it leads clearly."""

import unittest
from unittest import mock

import numpy as np

from src import booklet
from src.contexts import retrieval, section_route


class FakeEmbedder:
    """Titles mentioning "Jagd" point one way, "Velo" another; anything else in between."""

    def embed(self, texts):
        rows = []
        for t in texts:
            v = np.array([1.0, 0.0]) if "Jagd" in t or "chasse" in t else np.array([0.0, 1.0]) if "Velo" in t else np.ones(2)
            rows.append(v / np.linalg.norm(v))
        return np.array(rows)


def booklet_with(*titles):
    return booklet.Booklet(votes=[booklet.Vote(title=t, entry={}, ok=True) for t in titles])


class VoteByMeaning(unittest.TestCase):
    def setUp(self):
        section_route._title_vectors.clear()
        retrieval._query_cache.clear()
        self.patch = mock.patch.object(retrieval, "embedder", return_value=FakeEmbedder())
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        retrieval._query_cache.clear()

    def test_a_name_in_another_language_is_placed_when_it_leads_clearly(self):
        parsed = booklet_with("Bundesgesetz über die Velowege", "Änderung des Jagdgesetzes")
        self.assertIsNone(booklet.find_vote(parsed, "Modification de la loi sur la chasse"))
        self.assertIs(section_route.vote_by_meaning(parsed, "Modification de la loi sur la chasse"), parsed.votes[1])

    def test_no_clear_lead_gives_none(self):
        parsed = booklet_with("Bundesgesetz über die Velowege", "Änderung des Jagdgesetzes")
        position, lead = section_route.vote_scores(parsed, "Arrêté fédéral sur les avions")  # equally far from both
        self.assertLess(lead, section_route.VOTE_MARGIN)
        self.assertIsNone(section_route.vote_by_meaning(parsed, "Arrêté fédéral sur les avions"))

    def test_the_title_match_still_comes_first(self):
        parsed = booklet_with("Bundesgesetz über die Velowege", "Änderung des Jagdgesetzes")
        self.assertIs(booklet.find_vote(parsed, "Änderung des Jagdgesetzes"), parsed.votes[1])


if __name__ == "__main__":
    unittest.main()
