### 2026-10-09, session 7, Part 2: section-route offline on the validation set (no model calls)

- Command (from `track_2a/`): `EMBED_MODEL_DIR=models/multilingual-e5-small python3 scripts/route_check.py --cases data/val --out <folder>`, 00:33 to about 00:38 UTC, code `f73b650`. Output: `summary.json`, `per_case.jsonl`.
- Val: 580 task A cases from the rows in neither dev nor test, without the six rows used for router patterns in session 6 (`data/val/rows.json`). Nothing in the router or the parser was changed after this run.

**Booklets.** All 45 booklets the val cases use parse completely (132 of 132 votes); 44 are the dev booklets, one (2025-02-09, French) had not been opened before. No problem reported.

**Claims.** The router assigns a part to all 580 val claims (no unrouted claim). Routes: council 175, detail 74, summary 139, committee 105, law 87. 577 cases are routed; 3 fall back to embed-e5-small.

**What the routed part holds**, val next to dev (session 6, `2026-10-08_rashad_route-check_devA300`). Hit: a sent paragraph lies inside the gold passage (starter's evidence rule); coverage: share of the gold passage's 200-character windows in the sent text.

| | Val cases | Val hit | Val coverage | Val characters sent | Dev cases | Dev hit | Dev coverage | Dev characters sent |
|---|---|---|---|---|---|---|---|---|
| summary | 111 | 1.000 | 0.921 | 2,129 | 55 | 1.000 | 0.921 | 2,246 |
| council | 117 | 1.000 | 0.951 | 3,125 | 68 | 1.000 | 0.945 | 3,141 |
| committee | 63 | 0.984 | 0.941 | 3,071 | 26 | 1.000 | 0.962 | 3,102 |
| law | 63 | 1.000 | 0.602 | 3,325 | 25 | 1.000 | 0.610 | 3,482 |
| detail | 46 | 1.000 | 0.755 | 5,178 | 26 | 1.000 | 0.791 | 5,452 |
| same-language | 129 | 1.000 | 0.868 | 3,076 | 67 | 1.000 | 0.889 | 3,350 |
| cross-language | 271 | 0.996 | 0.861 | 3,123 | 133 | 1.000 | 0.874 | 3,173 |
| booklet de | 144 | 0.993 | 0.868 | 2,966 | 66 | 1.000 | 0.881 | 3,067 |
| booklet fr | 155 | 1.000 | 0.859 | 3,144 | 67 | 1.000 | 0.877 | 3,130 |
| booklet it | 101 | 1.000 | 0.864 | 3,255 | 67 | 1.000 | 0.878 | 3,499 |
| **all routed** | 400 | 0.998 | 0.863 | 3,108 | 200 | 1.000 | 0.879 | 3,233 |

**Every failure, in full.**

Unrouted claims: none.

Cases that fall back to embed-e5-small (3), all committee claims on the OECD minimum-tax vote of 2023-06-18, which has no committee (its "no" side is a parliamentary minority), as the one dev fallback:

- `v1.1-row-646-A` (booklets/2023_06_18_de.pdf): "Das Komitee vertritt die Auffassung, dass die Altersvorsorgereform eine Anhebung des Umwandlungssatzes auf 6,8 % vorsieht."
- `v1.1-row-912-A` (booklets/2023_06_18_fr.pdf): "Il comitato afferma che introdurre un salario minimo legale di 20 franchi l’ora migliorerebbe le condizioni lavorative dei dipendenti a basso reddito in tutti i settori dell’economia."
- `v1.1-row-1036-A` (booklets/2023_06_18_it.pdf): "Das Komitee vertritt die Ansicht, die Minderheit habe einen niedrigeren Anteil für die Bundesregierung verlangt und die Einnahmen stärker ungleich zwischen den Kantonen verteilen wollen, wodurch die steuerlich attraktiven Kantone zusätzlich begünstigt würden."

Routed evidence cases where no sent paragraph lies inside the gold passage (1):

- `v1.1-row-235-A` (booklets/2026_03_08_de.pdf, vote "Volksinitiative « Ja zu einer unabhängigen, freien Schweizer Währung mit Münzen oder Banknoten (Bargeld ist Freiheit) » und direkter Gegenentwurf (Bundesbeschluss über die schweizerische Währung und die Bargeldversorgung)"), routed to `committee` (pages [20, 21]): "Le comité estime que le contre-projet direct répond aux préoccupations de l’initiative sans compliquer inutilement l’ordre juridique, puisqu’il reprend des formulations déjà existantes." The gold passage lies on page [22], the parliamentary debate ("Debatte Parlament") of the cash initiative and its counter-proposal, which the parser assigns to the part `parliament`, not `committee`.

- **On claims it was not written for, the router routes every claim and the routed part holds the gold passage in 399 of 400 cases (dev: 200 of 200).** Coverage and characters sent are close to dev's; law and detail are again cut most often to 8 paragraphs (15 of 63 and 16 of 46 cases).
- As agreed, nothing was changed because of these results; the one miss and the three fallbacks are listed for the report.
