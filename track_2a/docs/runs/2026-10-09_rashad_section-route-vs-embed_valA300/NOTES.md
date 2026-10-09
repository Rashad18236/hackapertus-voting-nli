### 2026-10-09, session 7, Part 3 (E6): section-route against embed-e5-small, paired, 300 val task A cases

- Command (from `track_2a/`, on the host, nothing else running): `LLM_NAME=swiss-ai/apertus-v1.5-8b EMBED_MODEL_DIR=models/multilingual-e5-small python3 scripts/paired_run.py --cases data/val/sample300/cases.jsonl --data-dir output/data_dev --out-dir docs/runs/2026-10-09_rashad_section-route-vs-embed_valA300 --arm '{"name": "section-route", "context_a": "section-route"}' --arm '{"name": "embed-e5-small", "context_a": "embed-e5-small"}'`, 00:38 to 01:04 UTC, code `2d4a435`. Order alternates per case; both arms start with empty embedding caches. Progress log: `paired_run.log`.
- Cases: `data/val/sample300` (300 of the 580 val cases, balanced over label, claim language and booklet language, seed 42; 105 / 96 / 99 entailment / neutral / contradiction; 204 with a gold passage). No val case was seen while the router or the parser was written.
- **Model `swiss-ai/apertus-v1.5-8b` on Public AI for all 600 calls** (it answered at 00:38); **0 failed calls, 0 unparseable answers.** One embed-e5-small answer (label 2) cited no page it had been sent, so it has no evidence (format warning, label kept).
- Scored with the starter's `evaluate.py`; splits from `scripts/paired_analysis.py` (`paired_analysis.json`), whose re-implemented evidence rule gives the official totals (193 and 120).

| | section-route (val) | embed-e5-small (val) | section-route (dev, E5) | embed-e5-small (dev, E5) |
|---|---|---|---|---|
| **Macro-F1** | **0.956** | 0.865 | 0.953 | 0.834 |
| F1 entailment | 0.976 | 0.901 | 0.965 | 0.832 |
| F1 neutral | 0.955 | 0.883 | 0.947 | 0.850 |
| F1 contradiction | 0.936 | 0.811 | 0.947 | 0.819 |
| **Evidence** | **0.946 (193/204)** | 0.588 (120/204) | 0.905 (182/201) | 0.662 (133/201) |
| Mean input tokens | **1,222** | 1,827 | 1,210 | 1,868 |
| Median / p95 time | 1.5 s / **3.0 s** | 1.8 s / 12.3 s | 1.6 s / 3.9 s | 1.9 s / 11.7 s |
| Routed / fell back | 299 / 1 | – | 299 / 1 | – |

Confusion matrices on val (rows: gold; columns: predicted entailment, neutral, contradiction):

| gold | section-route | | | embed-e5-small | | |
|---|---|---|---|---|---|---|
| entailment | 103 | 1 | 1 | 96 | 4 | 5 |
| neutral | 0 | 96 | 0 | 0 | 87 | 9 |
| contradiction | 3 | 8 | 88 | 12 | 10 | 77 |

By claim type and language (Macro-F1; evidence found / gold cases), val next to dev:

| | Val cases | Val section-route | Val embed-e5-small | Val evidence s-r / e5 | Dev section-route | Dev embed-e5-small |
|---|---|---|---|---|---|---|
| summary | 60 | 0.924 | 0.794 | 50/52 / 20/52 | 0.929 | 0.789 |
| council | 88 | 0.974 | 0.938 | 54/57 / 37/57 | 1.000 | 0.852 |
| committee | 53 | 0.942 | 0.853 | 28/30 / 21/30 | 0.960 | 0.863 |
| law | 51 | 0.983 | 0.806 | 34/35 / 23/35 | 0.944 | 0.668 |
| detail | 48 | 0.912 | 0.814 | 27/30 / 19/30 | 0.817 | 0.818 |
| same-language | 101 | 0.970 | 0.858 | 66/68 / 47/68 | 0.930 | 0.910 |
| cross-language | 199 | 0.949 | 0.867 | 127/136 / 73/136 | 0.965 | 0.796 |
| booklet de | 101 | 0.950 | 0.869 | 64/68 / 33/68 | 0.909 | 0.830 |
| booklet fr | 101 | 0.938 | 0.870 | 62/68 / 44/68 | 0.980 | 0.841 |
| booklet it | 98 | 0.980 | 0.856 | 67/68 / 43/68 | 0.970 | 0.832 |

Macro-F1 by booklet -> claim language (starter's scorer, 31 to 34 cases each):

| booklet -> claim | Val section-route | Val embed-e5-small | Dev section-route | Dev embed-e5-small |
|---|---|---|---|---|
| de->de | 0.970 | 0.878 | 0.824 | 0.852 |
| de->fr | 0.939 | 0.850 | 0.938 | 0.760 |
| de->it | 0.941 | 0.875 | 0.970 | 0.877 |
| fr->de | 0.939 | 0.942 | 0.942 | 0.740 |
| fr->fr | 0.939 | 0.817 | 1.000 | 0.909 |
| fr->it | 0.938 | 0.845 | 1.000 | 0.877 |
| it->de | 0.965 | 0.798 | 0.971 | 0.672 |
| it->fr | 0.971 | 0.884 | 0.970 | 0.851 |
| it->it | 1.000 | 0.877 | 0.970 | 0.970 |

Paired outcomes on val (300 cases, both arms answered): both right 255, **only section-route right 32**, only embed-e5-small right 5, both wrong 8 (sign test on the 37 discordant cases: p = 7e-6; dev: 45 against 9). By claim type:

| | both right | only section-route right | only embed-e5-small right | both wrong |
|---|---|---|---|---|
| summary | 48 | 8 | 1 | 3 |
| council | 82 | 4 | 1 | 1 |
| committee | 45 | 5 | 1 | 2 |
| law | 40 | 10 | 1 | 0 |
| detail | 40 | 5 | 1 | 2 |

- **The dev result holds on val: section-route 0.956 against 0.865 (+0.091; dev 0.953 against 0.834, +0.119).** Evidence 0.946 against 0.588 (dev 0.905 against 0.662), 33 % fewer input tokens, p95 time 3.0 s against 12.3 s.
- section-route is better or equal in every claim type and in 8 of the 9 language pairs (French booklet with German claim: 0.939 against 0.942). On val its weakest part is detail (0.912), as on dev (0.817), but less so; German booklet with German claim, the one pair it lost on dev, is now its win (0.970 against 0.878).
- Its remaining errors are again mostly gold entailment or contradiction called neutral (9 of 13 wrong answers); it never calls a neutral claim entailed or contradicted (0 of 96).
- The control arm scores higher on val (0.865) than on dev (0.834); the two sets are different cases, so the arms of each run compare, not runs with each other.
- **Part 4 rule met (section-route at least 0.90 and at least 0.05 above embed-e5-small on val): section-route becomes the task A default in its own commit.**
