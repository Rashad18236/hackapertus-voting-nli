"""Router stress test: 100 reworded claim openings per language through src/claim_router.py (no model calls).

Run from track_2a/:

    python3 scripts/router_stress.py --out docs/runs/<folder>

The claims below were written for this test (session of 2026-10-09); none comes from the dataset.
Each names its source the way a reworded claim might: other verbs and word order, "Initiativkomitee",
"Referendumskomitee", "Bundesrat und Parlament", leading quotes, lower case, typographic
characters. Each has the part a careful reader would route it to (summary, council, committee, law,
detail), or None when the opening names no source (then falling back is right).

Outcome per claim: "right" (routed to the intended part), "fallback" (router gives None although
a part was intended: the case runs as embed-e5-small, still answered, not better), "wrong part"
(routed to another part: Apertus reads the wrong passage), "wrongly routed" (routed although no
source is named), "correct fallback" (None, and None intended).

The patterns once proposed here (docs/checks_no_model.md, Part 6, P10) and the stripping of leading
quotes and dashes are part of src/claim_router.py since session 8, so this script now tests the router
as it is (273 right, 0 wrong part; was 131 right, 4 wrong part before session 8). The run of the checks
session (docs/runs/2026-10-09_rashad_router-stress_300) keeps the results before and with the proposal.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import claim_router  # noqa: E402

S, C, K, L, D, N = "summary", "council", "committee", "law", "detail", None

DE = [
    # summary
    (S, "Laut der Zusammenfassung senkt die Vorlage die Kosten."),
    (S, "Gemäss Zusammenfassung senkt die Vorlage die Kosten."),
    (S, "Gemäß der Zusammenfassung senkt die Vorlage die Kosten."),
    (S, "Der Zusammenfassung zufolge senkt die Vorlage die Kosten."),
    (S, "Die Zusammenfassung hält fest, dass die Vorlage die Kosten senkt."),
    (S, "In der Zusammenfassung steht, dass die Vorlage die Kosten senkt."),
    (S, "Nach der Zusammenfassung senkt die Vorlage die Kosten."),
    (S, "Wie die Zusammenfassung erklärt, senkt die Vorlage die Kosten."),
    (S, "Laut Kurzfassung senkt die Vorlage die Kosten."),
    (S, "In Kürze: Die Vorlage senkt die Kosten."),
    (S, "Zusammengefasst senkt die Vorlage die Kosten."),
    (S, "Laut dem Überblick senkt die Vorlage die Kosten."),
    (S, "Der Bundesrat ist laut Zusammenfassung der Ansicht, dass die Vorlage die Kosten senkt."),
    (S, "Das Komitee kritisiert gemäss der Zusammenfassung die hohen Kosten."),
    # council
    (C, "Der Bundesrat vertritt die Auffassung, dass die Vorlage die Kosten senkt."),
    (C, "Der Bundesrat lehnt die Initiative ab, weil sie die Kosten erhöht."),
    (C, "Laut Bundesrat senkt die Vorlage die Kosten."),
    (C, "Gemäss dem Bundesrat senkt die Vorlage die Kosten."),
    (C, "Gemäß dem Bundesrat senkt die Vorlage die Kosten."),
    (C, "Dem Bundesrat zufolge senkt die Vorlage die Kosten."),
    (C, "Bundesrat und Parlament empfehlen, die Vorlage anzunehmen."),
    (C, "Der Bundesrat und das Parlament sind der Meinung, dass die Vorlage die Kosten senkt."),
    (C, "Laut Bundesrat und Parlament senkt die Vorlage die Kosten."),
    (C, "Nach Ansicht des Bundesrates senkt die Vorlage die Kosten."),
    (C, "Aus Sicht des Bundesrats senkt die Vorlage die Kosten."),
    (C, "Für den Bundesrat ist klar, dass die Vorlage die Kosten senkt."),
    (C, "Nach Meinung von Bundesrat und Parlament senkt die Vorlage die Kosten."),
    (C, "Der Bundesrat empfiehlt ein Ja, weil die Vorlage die Kosten senkt."),
    (C, "Die Landesregierung ist der Ansicht, dass die Vorlage die Kosten senkt."),
    (C, "Dass die Vorlage die Kosten senkt, betont der Bundesrat."),
    # committee
    (K, "Das Komitee ist der Ansicht, dass die Vorlage die Kosten erhöht."),
    (K, "Das Initiativkomitee argumentiert, dass die Vorlage die Kosten erhöht."),
    (K, "Das Referendumskomitee warnt, dass die Vorlage die Kosten erhöht."),
    (K, "Laut Initiativkomitee erhöht die Vorlage die Kosten."),
    (K, "Laut dem Referendumskomitee erhöht die Vorlage die Kosten."),
    (K, "Gemäss Komitee erhöht die Vorlage die Kosten."),
    (K, "Dem Komitee zufolge erhöht die Vorlage die Kosten."),
    (K, "Die Initiativkomitees sind überzeugt, dass die Vorlage die Kosten erhöht."),
    (K, "Die Referendumskomitees warnen, dass die Vorlage die Kosten erhöht."),
    (K, "Das überparteiliche Komitee warnt, dass die Vorlage die Kosten erhöht."),
    (K, "Das Initiativ-Komitee argumentiert, dass die Vorlage die Kosten erhöht."),
    (K, "Die Initiantinnen und Initianten argumentieren, dass die Vorlage die Kosten erhöht."),
    (K, "Nach Ansicht des Komitees erhöht die Vorlage die Kosten."),
    (K, "Aus Sicht des Initiativkomitees erhöht die Vorlage die Kosten."),
    (K, "Das Komitee kritisiert, der Bundesrat unterschätze die Kosten."),
    # law
    (L, "Laut dem Abstimmungstext muss der Bund die Kosten tragen."),
    (L, "Gemäss Abstimmungstext muss der Bund die Kosten tragen."),
    (L, "Der Abstimmungstext sieht vor, dass der Bund die Kosten trägt."),
    (L, "Im Abstimmungstext steht, dass der Bund die Kosten trägt."),
    (L, "Dem Abstimmungstext zufolge trägt der Bund die Kosten."),
    (L, "Nach dem Abstimmungstext trägt der Bund die Kosten."),
    (L, "Laut Initiativtext trägt der Bund die Kosten."),
    (L, "Laut Gesetzestext trägt der Bund die Kosten."),
    (L, "Gemäss dem Verfassungstext trägt der Bund die Kosten."),
    (L, "Der Text der Vorlage sieht vor, dass der Bund die Kosten trägt."),
    (L, "Der neue Verfassungsartikel sieht vor, dass der Bund die Kosten trägt."),
    (L, "Laut Abstimmungstext muss der Bundesrat die Kosten tragen."),
    (L, "Der Wortlaut der Vorlage verpflichtet den Bund, die Kosten zu tragen."),
    # detail
    (D, "Wird die Abstimmung angenommen, trägt der Bund die Kosten."),
    (D, "Wird die Vorlage angenommen, trägt der Bund die Kosten."),
    (D, "Bei Annahme der Vorlage trägt der Bund die Kosten."),
    (D, "Wenn die Vorlage angenommen wird, trägt der Bund die Kosten."),
    (D, "Wird die Initiative angenommen, trägt der Bund die Kosten."),
    (D, "Bei Annahme der Initiative trägt der Bund die Kosten."),
    (D, "Wenn die Initiative angenommen wird, trägt der Bund die Kosten."),
    (D, "Falls die Vorlage angenommen wird, trägt der Bund die Kosten."),
    (D, "Sollte die Vorlage angenommen werden, trägt der Bund die Kosten."),
    (D, "Bei einem Ja trägt der Bund die Kosten."),
    (D, "Mit der Annahme der Vorlage trägt der Bund die Kosten."),
    (D, "Nimmt das Volk die Vorlage an, trägt der Bund die Kosten."),
    (D, "Wird das Gesetz angenommen, trägt der Bund die Kosten."),
    (D, "Wird der Bundesbeschluss angenommen, trägt der Bund die Kosten."),
    (D, "Wird die Gesetzesänderung angenommen, trägt der Bund die Kosten."),
    # no source named at the start
    (N, "Die Vorlage senkt die Kosten für die Kantone."),
    (N, "Der Bund trägt künftig die Kosten."),
    (N, "Die Kosten steigen laut Bundesrat."),
    (N, "Viele Kantone unterstützen die Vorlage."),
]

FR = [
    # summary
    (S, "Le résumé précise que le projet réduit les coûts."),
    (S, "Selon le résumé, le projet réduit les coûts."),
    (S, "D'après le résumé, le projet réduit les coûts."),
    (S, "D’après le résumé, le projet réduit les coûts."),
    (S, "Dans le résumé, on lit que le projet réduit les coûts."),
    (S, "Le résumé indique que le projet réduit les coûts."),
    (S, "Selon la synthèse, le projet réduit les coûts."),
    (S, "En bref, le projet réduit les coûts."),
    (S, "Comme l'indique le résumé, le projet réduit les coûts."),
    (S, "Le bref aperçu indique que le projet réduit les coûts."),
    (S, "Résumé : le projet réduit les coûts."),
    (S, "Le Conseil fédéral, selon le résumé, estime que le projet réduit les coûts."),
    # council
    (C, "Le Conseil fédéral estime que le projet réduit les coûts."),
    (C, "Selon le Conseil fédéral, le projet réduit les coûts."),
    (C, "D'après le Conseil fédéral, le projet réduit les coûts."),
    (C, "Le Conseil fédéral et le Parlement recommandent d'accepter le projet."),
    (C, "Conseil fédéral et Parlement recommandent d'accepter le projet."),
    (C, "Selon le Conseil fédéral et le Parlement, le projet réduit les coûts."),
    (C, "Pour le Conseil fédéral, le projet réduit les coûts."),
    (C, "De l'avis du Conseil fédéral, le projet réduit les coûts."),
    (C, "Aux yeux du Conseil fédéral, le projet réduit les coûts."),
    (C, "Le gouvernement fédéral estime que le projet réduit les coûts."),
    (C, "Le Conseil fédéral rejette l'initiative, car elle augmente les coûts."),
    (C, "Selon l’avis du Conseil fédéral, le projet réduit les coûts."),
    (C, "Le Conseil fédéral souligne que le comité exagère les coûts."),
    (C, "Que le projet réduise les coûts, le Conseil fédéral l'affirme."),
    # committee
    (K, "Le comité affirme que le projet augmente les coûts."),
    (K, "Le comité d'initiative affirme que le projet augmente les coûts."),
    (K, "Le comité référendaire affirme que le projet augmente les coûts."),
    (K, "Selon le comité, le projet augmente les coûts."),
    (K, "D'après le comité d'initiative, le projet augmente les coûts."),
    (K, "Pour le comité, le projet augmente les coûts."),
    (K, "Les initiants affirment que le projet augmente les coûts."),
    (K, "Les auteurs de l'initiative affirment que le projet augmente les coûts."),
    (K, "Les comités référendaires affirment que le projet augmente les coûts."),
    (K, "Le comité interpartis affirme que le projet augmente les coûts."),
    (K, "De l'avis du comité, le projet augmente les coûts."),
    (K, "Selon le comité référendaire, le projet augmente les coûts."),
    (K, "Le comité d’initiative estime que le projet augmente les coûts."),
    # law
    (L, "Selon le texte soumis au vote, la Confédération prend les coûts en charge."),
    (L, "D'après le texte soumis au vote, la Confédération prend les coûts en charge."),
    (L, "Le texte soumis au vote prévoit que la Confédération prend les coûts en charge."),
    (L, "Selon le texte de la votation, la Confédération prend les coûts en charge."),
    (L, "Selon le texte de l'initiative, la Confédération prend les coûts en charge."),
    (L, "Le texte de loi prévoit que la Confédération prend les coûts en charge."),
    (L, "Selon le texte de loi, la Confédération prend les coûts en charge."),
    (L, "Selon le texte mis aux voix, la Confédération prend les coûts en charge."),
    (L, "Aux termes du texte soumis au vote, la Confédération prend les coûts en charge."),
    (L, "Le nouvel article constitutionnel prévoit que la Confédération prend les coûts en charge."),
    (L, "Selon le texte soumis à la votation, la Confédération prend les coûts en charge."),
    (L, "Le texte soumis au vote oblige le Conseil fédéral à prendre les coûts en charge."),
    # detail
    (D, "Si le vote est accepté, la Confédération prend les coûts en charge."),
    (D, "Si le projet est accepté, la Confédération prend les coûts en charge."),
    (D, "Si l'objet est accepté, la Confédération prend les coûts en charge."),
    (D, "Si le projet est adopté, la Confédération prend les coûts en charge."),
    (D, "L'acceptation du projet signifie que la Confédération prend les coûts en charge."),
    (D, "Si l'initiative est acceptée, la Confédération prend les coûts en charge."),
    (D, "Si la loi est acceptée, la Confédération prend les coûts en charge."),
    (D, "En cas d'acceptation, la Confédération prend les coûts en charge."),
    (D, "En cas de oui, la Confédération prend les coûts en charge."),
    (D, "Si le peuple accepte le projet, la Confédération prend les coûts en charge."),
    (D, "Si la modification est adoptée, la Confédération prend les coûts en charge."),
    (D, "Si la révision est acceptée, la Confédération prend les coûts en charge."),
    (D, "Si le projet de loi est accepté, la Confédération prend les coûts en charge."),
    (D, "En cas d'acceptation de l'initiative, la Confédération prend les coûts en charge."),
    (D, "Si l'arrêté fédéral est accepté, la Confédération prend les coûts en charge."),
    # no source named at the start
    (N, "Le projet réduit les coûts pour les cantons."),
    (N, "La Confédération prendra les coûts en charge."),
    (N, "Les coûts augmentent selon le Conseil fédéral."),
    (N, "De nombreux cantons soutiennent le projet."),
]

IT = [
    # summary
    (S, "Il riassunto afferma che il progetto riduce i costi."),
    (S, "Secondo il riassunto, il progetto riduce i costi."),
    (S, "Nel riassunto si legge che il progetto riduce i costi."),
    (S, "Stando al riassunto, il progetto riduce i costi."),
    (S, "Il riepilogo afferma che il progetto riduce i costi."),
    (S, "In breve, il progetto riduce i costi."),
    (S, "Secondo la sintesi, il progetto riduce i costi."),
    (S, "Dal riassunto emerge che il progetto riduce i costi."),
    (S, "Come indica il riassunto, il progetto riduce i costi."),
    (S, "In sintesi, il progetto riduce i costi."),
    (S, "Il Consiglio federale, secondo il riassunto, ritiene che il progetto riduca i costi."),
    # council
    (C, "Il Consiglio federale ritiene che il progetto riduca i costi."),
    (C, "Secondo il Consiglio federale, il progetto riduce i costi."),
    (C, "Per il Consiglio federale, il progetto riduce i costi."),
    (C, "Il Consiglio federale e il Parlamento raccomandano di accettare il progetto."),
    (C, "Consiglio federale e Parlamento raccomandano di accettare il progetto."),
    (C, "Secondo Consiglio federale e Parlamento, il progetto riduce i costi."),
    (C, "A parere del Consiglio federale, il progetto riduce i costi."),
    (C, "Ad avviso del Consiglio federale, il progetto riduce i costi."),
    (C, "Stando al Consiglio federale, il progetto riduce i costi."),
    (C, "Il governo federale ritiene che il progetto riduca i costi."),
    (C, "Il Consiglio federale respinge l'iniziativa perché aumenta i costi."),
    (C, "Secondo il parere del Consiglio federale, il progetto riduce i costi."),
    (C, "Il Consiglio federale sottolinea che il comitato esagera i costi."),
    (C, "Che il progetto riduca i costi, lo afferma il Consiglio federale."),
    # committee
    (K, "Il comitato afferma che il progetto aumenta i costi."),
    (K, "Il comitato d'iniziativa afferma che il progetto aumenta i costi."),
    (K, "Il comitato referendario afferma che il progetto aumenta i costi."),
    (K, "Secondo il comitato, il progetto aumenta i costi."),
    (K, "Per il comitato, il progetto aumenta i costi."),
    (K, "I promotori dell'iniziativa affermano che il progetto aumenta i costi."),
    (K, "Secondo i promotori, il progetto aumenta i costi."),
    (K, "I comitati referendari affermano che il progetto aumenta i costi."),
    (K, "Stando al comitato, il progetto aumenta i costi."),
    (K, "A detta del comitato, il progetto aumenta i costi."),
    (K, "Il comitato d’iniziativa ritiene che il progetto aumenti i costi."),
    (K, "Secondo il comitato referendario, il progetto aumenta i costi."),
    (K, "A parere del comitato, il progetto aumenta i costi."),
    # law
    (L, "Stando al testo di voto, la Confederazione si assume i costi."),
    (L, "Secondo il testo in votazione, la Confederazione si assume i costi."),
    (L, "Il testo sottoposto al voto prevede che la Confederazione si assuma i costi."),
    (L, "Nel testo di voto si afferma che la Confederazione si assume i costi."),
    (L, "In base al testo in votazione, la Confederazione si assume i costi."),
    (L, "Secondo il testo dell'iniziativa, la Confederazione si assume i costi."),
    (L, "Il testo di legge prevede che la Confederazione si assuma i costi."),
    (L, "Secondo il testo della legge, la Confederazione si assume i costi."),
    (L, "Il nuovo articolo costituzionale prevede che la Confederazione si assuma i costi."),
    (L, "Secondo il testo sottoposto a votazione, la Confederazione si assume i costi."),
    (L, "Il testo in votazione obbliga il Consiglio federale ad assumersi i costi."),
    # detail
    (D, "Se il voto viene approvato, la Confederazione si assume i costi."),
    (D, "Se la proposta viene accettata, la Confederazione si assume i costi."),
    (D, "Se il progetto è accettato, la Confederazione si assume i costi."),
    (D, "Se il progetto verrà approvato, la Confederazione si assume i costi."),
    (D, "Se l'iniziativa viene accettata, la Confederazione si assume i costi."),
    (D, "Se la legge viene approvata, la Confederazione si assume i costi."),
    (D, "In caso di approvazione, la Confederazione si assume i costi."),
    (D, "In caso di sì, la Confederazione si assume i costi."),
    (D, "Se il popolo approva il progetto, la Confederazione si assume i costi."),
    (D, "Qualora il progetto venisse accolto, la Confederazione si assume i costi."),
    (D, "Con l'accettazione del progetto, la Confederazione si assume i costi."),
    (D, "Se la modifica viene approvata, la Confederazione si assume i costi."),
    (D, "In caso di accettazione dell'iniziativa, la Confederazione si assume i costi."),
    (D, "Se il decreto federale viene accettato, la Confederazione si assume i costi."),
    # no source named at the start
    (N, "Il progetto riduce i costi per i Cantoni."),
    (N, "La Confederazione si assumerà i costi."),
    (N, "I costi aumentano secondo il Consiglio federale."),
    (N, "Molti Cantoni sostengono il progetto."),
]

# Variants of routed openings, to reach 100 per language: leading quotes, lower and upper case, a dash or
# spaces in front, a non-breaking space after the first word.
VARIANTS = [
    ("«", lambda t: "«" + t[:-1] + "»."),
    ("„", lambda t: "„" + t[:-1] + "“."),
    ('"', lambda t: '"' + t[:-1] + '".'),
    ("'", lambda t: "'" + t[:-1] + "'."),
    ("lower case", str.lower),
    ("upper case", str.upper),
    ("leading dash", lambda t: "– " + t),
    ("leading spaces", lambda t: "   " + t),
    ("non-breaking space", lambda t: t.replace(" ", " ", 1)),
    ("line break", lambda t: t.replace(" ", "\n", 1)),
]


def with_variants(base, n=100):
    """base plus variants of its routed claims (the router routes them) until there are n claims."""
    out = [(part, text, "") for part, text in base]
    sources = [(part, text) for part, text in base if part and claim_router.route(text) == part]
    i = 0
    while len(out) < n:
        name, transform = VARIANTS[i % len(VARIANTS)]
        part, text = sources[(i * 7) % len(sources)]
        out.append((part, transform(text), name))
        i += 1
    return out[:n]


def outcome(intended, got):
    if intended is None:
        return "correct fallback" if got is None else "wrongly routed"
    if got is None:
        return "fallback"
    return "right" if got == intended else "wrong part"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    route = claim_router.route
    rows = []
    for language, base in (("de", DE), ("fr", FR), ("it", IT)):
        for intended, text, variant in with_variants(base):
            got = route(text)
            rows.append({"language": language, "intended": intended, "routed": got, "variant": variant,
                         "outcome": outcome(intended, got), "claim": text})
    report = {"claims": len(rows), "by_language": {}}
    for language in ("de", "fr", "it"):
        mine = [r for r in rows if r["language"] == language]
        report["by_language"][language] = {
            "claims": len(mine), "outcomes": dict(Counter(r["outcome"] for r in mine)),
            "routed_to": dict(Counter(str(r["routed"]) for r in mine)),
            "by_intended_part": {str(p): dict(Counter(r["outcome"] for r in mine if r["intended"] == p))
                                 for p in (S, C, K, L, D, N)},
        }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "router_stress.json").write_text(json.dumps({"summary": report, "rows": rows}, ensure_ascii=False, indent=1)
                                           + "\n", encoding="utf-8")
    for language, r in report["by_language"].items():
        print(f"{language}: {r['claims']} claims; outcomes {r['outcomes']}; routed to {r['routed_to']}")
    for r in rows:
        if r["outcome"] in ("wrong part", "wrongly routed"):
            print(f"  {r['outcome'].upper()} [{r['language']}] intended {r['intended']}, routed {r['routed']}: "
                  f"{r['claim'][:90]!r}")


if __name__ == "__main__":
    main()
