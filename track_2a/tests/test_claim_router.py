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
        # Since session 8 a summary named within the first words (up to 40 characters, no comma or full stop
        # before it) overrides the subject (P10); named later, it still does not count.
        self.assertEqual(claim_router.route("Die Initiative sagt laut der Zusammenfassung etwas."), "summary")
        self.assertIsNone(claim_router.route("Die Initiative sagt etwas, und laut der Zusammenfassung steigt die Steuer."))
        self.assertIsNone(claim_router.route(
            "Die Initiative der Jungen für eine wesentlich höhere Steuer ist laut der Zusammenfassung nötig."))

    def test_unknown_opening_gives_none(self):
        self.assertIsNone(claim_router.route("Die Schweiz hat 26 Kantone."))
        self.assertIsNone(claim_router.route(""))


class Session8Patterns(unittest.TestCase):
    """The patterns added in session 8 (P10, docs/checks_no_model.md): one opening per pattern group, written for
    the router stress test of 2026-10-09 (none from the dataset)."""

    CASES = [
        # A summary named within the first words overrides the subject (the four openings that went to the
        # wrong part before session 8 come first).
        ("Der Bundesrat ist laut Zusammenfassung der Ansicht, dass die Vorlage die Kosten senkt.", "summary"),
        ("Das Komitee kritisiert gemäss der Zusammenfassung die hohen Kosten.", "summary"),
        ("Le Conseil fédéral, selon le résumé, estime que le projet réduit les coûts.", "summary"),
        ("Il Consiglio federale, secondo il riassunto, ritiene che il progetto riduca i costi.", "summary"),
        # summary
        ("Nach der Zusammenfassung senkt die Vorlage die Kosten.", "summary"),
        ("In Kürze: Die Vorlage senkt die Kosten.", "summary"),
        ("Selon la synthèse, le projet réduit les coûts.", "summary"),
        ("En bref, le projet réduit les coûts.", "summary"),
        ("In breve, il progetto riduce i costi.", "summary"),
        ("In sintesi, il progetto riduce i costi.", "summary"),
        # council
        ("Gemäß dem Bundesrat senkt die Vorlage die Kosten.", "council"),
        ("Bundesrat und Parlament empfehlen, die Vorlage anzunehmen.", "council"),
        ("Nach Ansicht des Bundesrates senkt die Vorlage die Kosten.", "council"),
        ("Conseil fédéral et Parlement recommandent d'accepter le projet.", "council"),
        ("De l'avis du Conseil fédéral, le projet réduit les coûts.", "council"),
        ("Consiglio federale e Parlamento raccomandano di accettare il progetto.", "council"),
        ("A parere del Consiglio federale, il progetto riduce i costi.", "council"),
        # committee
        ("Gemäss Komitee erhöht die Vorlage die Kosten.", "committee"),
        ("Die Initiantinnen und Initianten sagen, die Vorlage erhöhe die Kosten.", "committee"),
        ("Pour le comité, le projet augmente les coûts.", "committee"),
        ("Les initiants affirment que le projet augmente les coûts.", "committee"),
        ("I promotori dell'iniziativa affermano che il progetto aumenta i costi.", "committee"),
        ("I comitati sostengono che il progetto aumenta i costi.", "committee"),
        # law
        ("Nach dem Abstimmungstext trägt der Bund die Kosten.", "law"),
        ("Laut Initiativtext trägt der Bund die Kosten.", "law"),
        ("Selon le texte de l'initiative, la Confédération prend les coûts en charge.", "law"),
        ("Secondo il testo dell'iniziativa, la Confederazione si assume i costi.", "law"),
        # detail
        ("Wird die Initiative angenommen, trägt der Bund die Kosten.", "detail"),
        ("Bei Annahme der Initiative trägt der Bund die Kosten.", "detail"),
        ("Si l'initiative est acceptée, la Confédération prend les coûts en charge.", "detail"),
        ("En cas d'acceptation, la Confédération prend les coûts en charge.", "detail"),
        ("Se l'iniziativa viene accettata, la Confederazione si assume i costi.", "detail"),
        ("In caso di approvazione, la Confederazione si assume i costi.", "detail"),
    ]

    def test_each_new_pattern_group(self):
        for claim, part in self.CASES:
            with self.subTest(claim=claim):
                self.assertEqual(claim_router.route(claim), part)

    def test_leading_quotes_and_dashes_are_ignored(self):
        for claim, part in (("«Laut der Zusammenfassung senkt die Vorlage die Kosten.»", "summary"),
                            ("„Der Bundesrat vertritt die Ansicht, dass ...“", "council"),
                            ("\"Le comité affirme que le projet augmente les coûts.\"", "committee"),
                            ("'Il comitato afferma che il progetto aumenta i costi.'", "committee"),
                            ("– Selon le comité, le projet augmente les coûts.", "committee"),
                            ("— Laut dem Abstimmungstext trägt der Bund die Kosten.", "law")):
            with self.subTest(claim=claim):
                self.assertEqual(claim_router.route(claim), part)

    def test_still_no_route_without_a_named_source(self):
        for claim in ("Die Vorlage senkt die Kosten.", "« Le projet réduit les coûts. »", "– Il progetto riduce i costi."):
            with self.subTest(claim=claim):
                self.assertIsNone(claim_router.route(claim))


if __name__ == "__main__":
    unittest.main()
