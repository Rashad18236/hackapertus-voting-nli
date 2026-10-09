"""Tests for src/claim_router.py (the part of the vote a claim's opening names)."""

import unittest

from src import claim_router

EXAMPLES = {  # openings seen in the dev claims, three languages per part
    "summary": ["Laut der Zusammenfassung soll die CO₂-Abgabe steigen.", "Le résumé précise que la loi change.",
                "Nel riassunto si sostiene che la legge cambia."],
    "council": ["Der Bundesrat vertritt die Auffassung, dass die Reform nötig ist.",
                "Le Conseil fédéral préconise le rejet de l'initiative.",
                "Secondo il Consiglio federale, l’UE è il partner principale."],
    "committee": ["Das Komitee ist der Ansicht, dass die Steuer schadet.", "Le comité affirme que les primes ont doublé.",
                  "Il comitato ritiene che la politica climatica sia insufficiente."],
    "law": ["Laut dem Abstimmungstext empfiehlt die Bundesversammlung die Ablehnung.",
            "D’après le texte soumis au vote, l’Assemblée fédérale recommande le rejet.",
            "Stando al testo di voto, l’Assemblea federale raccomanda di approvare."],
    "detail": ["Wird die Abstimmung angenommen, muss die Schweiz bis 2050 klimaneutral sein.",
               "Si le vote est accepté, la Confédération devra financer les réductions.",
               "Se la votazione verrà approvata, la Svizzera introdurrà un nuovo regime."],
}


class Route(unittest.TestCase):
    def test_each_part_in_three_languages(self):
        for part, claims in EXAMPLES.items():
            for claim in claims:
                with self.subTest(claim=claim):
                    self.assertEqual(claim_router.route(claim), part)

    def test_only_the_opening_counts(self):
        self.assertEqual(claim_router.route("Le comité affirme que le Conseil fédéral se trompe."), "committee")
        self.assertIsNone(claim_router.route("Die Initiative sagt laut der Zusammenfassung etwas."))

    def test_unknown_opening_gives_none(self):
        self.assertIsNone(claim_router.route("Die Schweiz hat 26 Kantone."))
        self.assertIsNone(claim_router.route(""))


if __name__ == "__main__":
    unittest.main()
