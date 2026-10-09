### 2026-10-09, checks without a model, Part 6: router stress test

- Command (from `track_2a/`): `python3 scripts/router_stress.py --out <folder>` and the same with `--proposal`, 01:06 UTC. Outputs: `output.txt`, `output_proposal.txt`, `router_stress.json`, `router_stress_proposal.json` (every claim, its intended part, the route and the outcome).
- **The claims:** 100 per language, written for this test (none from the dataset): reworded openings for each part (other verbs, word order, "Initiativkomitee", "Referendumskomitee", "Bundesrat und Parlament", "comité référendaire", "Consiglio federale e Parlamento", other names for the law text and for "if accepted"), 4 per language that name no source at the start (falling back is right), and variants of routed openings to reach 100: leading «, „, ", ' quotes, lower and upper case, a leading dash, leading spaces, a non-breaking space, a line break.
- **Router as it is:**

| | right | wrong part | fallback (part intended) | correct fallback |
|---|---|---|---|---|
| de | 40 | 2 | 54 | 4 |
| fr | 47 | 1 | 48 | 4 |
| it | 44 | 1 | 51 | 4 |
| **all** | **131** | **4** | **153** | **12** |

- **Wrong part (4):** a source named after the subject: "Der Bundesrat ist laut Zusammenfassung der Ansicht ..." (council, intended summary), "Das Komitee kritisiert gemäss der Zusammenfassung ..." (committee), "Le Conseil fédéral, selon le résumé, ..." (council), "Il Consiglio federale, secondo il riassunto, ..." (council). Apertus would read the wrong part.
- **Variants:** lower case, upper case, leading spaces, a non-breaking space and a line break are routed as before (the router normalises them). **Every leading quote (38) and leading dash (8) falls back**: the patterns are anchored at the first character.
- **Fallbacks (153)**, by kind: other prepositions or verbs ("Nach Ansicht des Bundesrates", "Aus Sicht des Bundesrats", "Pour le Conseil fédéral", "De l'avis du Conseil fédéral", "A parere del Consiglio federale"), "Gemäß dem Bundesrat" with ß, "Bundesrat und Parlament ..." without article, "Conseil fédéral et Parlement", plural committees ("Die Initiativkomitees", "Les comités référendaires", "I comitati referendari"), the initiative or the law as the subject of "if accepted" ("Wird die Initiative angenommen", "Si l'initiative est acceptée", "Se l'iniziativa viene accettata", "En cas d'acceptation", "In caso di approvazione"), other names for the text ("Laut Initiativtext", "Selon le texte de l'initiative", "Secondo il testo dell'iniziativa"), and summary synonyms ("In Kürze", "En bref", "In breve").
- No opening without a source was routed (0 wrongly routed).
- **With the proposed patterns** (`scripts/router_stress.py`, `PROPOSED`; tried before the router's own; leading quotes and dashes stripped): 273 right, 0 wrong part, 15 fallbacks, 12 correct fallbacks. The 15 left: "Die Landesregierung", "Le gouvernement fédéral", "Il governo federale", a source at the end of the sentence, "Der Text der Vorlage", "Der Wortlaut der Vorlage", "Der neue Verfassungsartikel", "Le nouvel article constitutionnel", "Il nuovo articolo costituzionale", "Zusammengefasst", "Laut dem Überblick", "Le bref aperçu", "Résumé :". On the 877 distinct dataset claims outside the test booklets (the 300 dev claims and the rest), the proposal changes no route. The proposal was written after seeing the stress claims, so 273 is not an unseen measure.
