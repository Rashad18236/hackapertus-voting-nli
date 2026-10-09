### 2026-10-08/09, session 6, Part 3 (E5): section-route against embed-e5-small, paired, all 300 dev task A cases

- Command (from `track_2a/`, on the host, nothing else running): `LLM_NAME=swiss-ai/apertus-v1.5-8b EMBED_MODEL_DIR=models/multilingual-e5-small python3 scripts/paired_run.py --cases output/devA/cases.jsonl --data-dir output/data_dev --out-dir docs/runs/2026-10-08_rashad_section-route-vs-embed_devA300 --arm '{"name": "section-route", "context_a": "section-route"}' --arm '{"name": "embed-e5-small", "context_a": "embed-e5-small"}'`, 23:41 UTC on 2026-10-08 to 00:07 on 2026-10-09, code `02ecd5d`. Order alternates per case. Both arms start with empty embedding caches. The progress log is `paired_run.log`.
- **Model: `swiss-ai/apertus-v1.5-8b` on Public AI for all 600 calls** (it answered at 23:35 and 23:41; no fallback to the thinking model was needed). **0 failed calls and 0 unparseable answers.**
- Before the run, two dev cases (rows 4 and 75) were sent once through `src.cli --context-a section-route` as a smoke test of the new answer schema; those answers are not part of any result.
- Scored with the starter's `evaluate.py` (commit `559b598`); per-part and per-language numbers from `scripts/paired_analysis.py` (`paired_analysis.json`), whose re-implemented evidence rule gives the official totals (182 and 133).

| | section-route | embed-e5-small |
|---|---|---|
| **Macro-F1** | **0.953** | 0.834 |
| F1 entailment | 0.965 | 0.832 |
| F1 neutral | 0.947 | 0.850 |
| F1 contradiction | 0.947 | 0.819 |
| **Evidence** | **0.905 (182/201)** | 0.662 (133/201) |
| Mean input tokens | **1,210** | 1,868 |
| Median / p95 time | 1.6 s / **3.9 s** | 1.9 s / 11.7 s |
| Routed / fell back | 299 / 1 | – |

Confusion matrix, section-route:

| gold \ predicted | entailment | neutral | contradiction |
|---|---|---|---|
| entailment | 97 | 4 | 1 |
| neutral | 0 | 99 | 0 |
| contradiction | 2 | 7 | 90 |

Confusion matrix, embed-e5-small:

| gold \ predicted | entailment | neutral | contradiction |
|---|---|---|---|
| entailment | 77 | 8 | 17 |
| neutral | 3 | 85 | 11 |
| contradiction | 3 | 8 | 88 |

By claim type (part the router assigns) and by language: Macro-F1, evidence found / gold cases:

| | Cases | section-route F1 | embed-e5-small F1 | section-route evidence | embed-e5-small evidence |
|---|---|---|---|---|---|
| summary | 67 | 0.929 | 0.789 | 49/55 | 25/55 |
| council | 102 | 1.000 | 0.852 | 65/68 | 50/68 |
| committee | 49 | 0.960 | 0.863 | 24/27 | 20/27 |
| law | 39 | 0.944 | 0.668 | 24/25 | 17/25 |
| detail | 43 | 0.817 | 0.818 | 20/26 | 21/26 |
| same-language | 100 | 0.930 | 0.910 | 58/67 | 52/67 |
| cross-language | 200 | 0.965 | 0.796 | 124/134 | 81/134 |
| booklet de | 100 | 0.909 | 0.830 | 57/67 | 47/67 |
| booklet fr | 100 | 0.980 | 0.841 | 64/67 | 41/67 |
| booklet it | 100 | 0.970 | 0.832 | 61/67 | 45/67 |

Macro-F1 by booklet -> claim language (starter's scorer, 33 or 34 cases each):

| booklet -> claim | section-route | embed-e5-small |
|---|---|---|
| de->de | 0.824 | 0.852 |
| de->fr | 0.938 | 0.760 |
| de->it | 0.970 | 0.877 |
| fr->de | 0.942 | 0.740 |
| fr->fr | 1.000 | 0.909 |
| fr->it | 1.000 | 0.877 |
| it->de | 0.971 | 0.672 |
| it->fr | 0.970 | 0.851 |
| it->it | 0.970 | 0.970 |

Paired outcomes (300 cases, both arms answered): both right 241, **section-route right and embed-e5-small wrong 45**, embed-e5-small right and section-route wrong 9, both wrong 5 (sign test on the 54 discordant cases: p = 7e-7). By claim type:

| | both right | only section-route right | only embed-e5-small right | both wrong |
|---|---|---|---|---|
| summary | 51 | 12 | 4 | 0 |
| council | 87 | 15 | 0 | 0 |
| committee | 42 | 5 | 1 | 1 |
| law | 27 | 10 | 1 | 1 |
| detail | 34 | 3 | 3 | 3 |

- **section-route wins on every measure: Macro-F1 0.953 against 0.834 (+0.119), evidence 0.905 against 0.662, 35 % fewer input tokens (1,210 against 1,868), p95 time 3.9 s against 11.7 s.** It wins in every claim type except detail (0.817 against 0.818, a tie) and in 7 of the 9 booklet/claim language pairs (German booklet with German claim: 0.824 against 0.852; Italian with Italian: 0.970 for both). The cross-language gap of embed-e5-small (0.796 against 0.910 same-language) disappears (0.965 against 0.930).
- Where it still errs: 14 wrong labels, 10 of them gold entailment or contradiction called neutral (3 summary, 4 detail, 2 committee, 1 law). Detail is the weakest part (8 of its 26 evidence cases have a section over 8,000 characters, cut to 8 paragraphs).
- Evidence misses (19 of 201): 11 predicted neutral (no evidence), 8 cited a paragraph outside the gold passage (3 council, 2 summary, 2 detail, 1 committee; one of these is the committee's disclaimer line "Der Text auf dieser Doppelseite stammt vom Initiativkomitee").
- The one fallback case (row 1383, committee claim on a vote without a committee) ran as embed-e5-small and was right.
- **The control arm scores much higher here (0.834) than in E4 (0.711 on `apertus-v1.5-8b-thinking`, with whole-page evidence 0.373).** Different model, different server time and, for evidence, the new default `cited-pieces`; rows from different runs do not compare, only the two arms of this run.
