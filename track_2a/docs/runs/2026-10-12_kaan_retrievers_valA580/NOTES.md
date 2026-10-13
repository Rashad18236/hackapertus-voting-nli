### Retrievers with the model on val, routing off: all 580 val task A cases (confirmation, three arms)

**Command** (from `track_2a/`): `EMBED_MODEL_DIR=models/multilingual-e5-small MT_MODEL_DIR=models/m2m100_418M-ct2
python3 scripts/paired_run.py --cases data/val/cases.jsonl --data-dir output/data_dev --out-dir
docs/runs/2026-10-12_kaan_retrievers_valA580 --min-interval 2 --arm '{"name":"embed-e5-small","context_a":
"embed-e5-small"}' --arm '{"name":"bm25-mt","context_a":"bm25-mt"}' --arm '{"name":"hybrid","context_a":"hybrid"}'`;
17:41 to 18:49 UTC. The val booklet missing locally (`2025_02_09_fr.pdf`) was fetched first with
`scripts/fetch_dev_booklets.py --cases data/val/cases.jsonl`. 0 failed calls, 0 unparseable answers, 0 HTTP 429;
embed-e5-small had one answer citing no valid page (counted by the scorer as given). The two arms that gained at
least 0.01 on dev against embed-e5-small (bm25-mt +0.064, hybrid +0.037) are confirmed here; vote-section-hybrid
(+0.020 on dev, below hybrid) was left out to save calls.

| Arm | Right of 580 | Macro-F1 | Evidence | Mean input tokens | Mean / p95 time (ms) |
|---|---|---|---|---|---|
| embed-e5-small (today's fallback) | 505 | 0.871 | 0.589 (236/401) | 1,856 | 2,070 / 2,706 |
| **bm25-mt** | 535 | **0.923** | 0.706 (283/401) | 2,522 | 2,419 / 3,100 |
| **hybrid** | **537** | **0.926** | **0.713 (286/401)** | 2,381 | 2,341 / 3,446 |

Paired (cases only one arm got right; two-sided sign test): bm25-mt vs embed-e5-small 51 vs 21 (p = 0.0005),
hybrid vs embed-e5-small 48 vs 16 (p = 0.0001), bm25-mt vs hybrid 19 vs 21 (p = 0.87, no difference).

By group (right of the group; e5 / bm25-mt / hybrid): gold neutral 160 / 167 / 162 of 179; gold entailment or
contradiction 345 / 368 / 375 of 401; same language 175 / 188 / 181 of 196; cross-language 330 / 347 / 356 of 384.

**Verdict.** On cases nobody looked at, both new retrievers beat today's fallback by about 0.05 Macro-F1 and 0.12
evidence, and are equal to each other. On dev bm25-mt was ahead of hybrid (13 vs 5, p = 0.096). bm25-mt needs no
embedding of the booklet (today's fallback embeds the whole booklet on its first case: the slowest local step),
only the translation of one claim.
