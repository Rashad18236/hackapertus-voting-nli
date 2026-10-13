### Retrievers with the model, routing off: all 300 dev task A cases (one interleaved run, five arms)

**Command** (from `track_2a/`): `EMBED_MODEL_DIR=models/multilingual-e5-small MT_MODEL_DIR=models/m2m100_418M-ct2
python3 scripts/paired_run.py --cases output/robustness/devA300.jsonl --data-dir output/data_dev --out-dir
docs/runs/2026-10-13_kaan_retrievers_devA300 (renamed, see below) --min-interval 2 --arm '{"name":"embed-e5-small","context_a":
"embed-e5-small"}' --arm '{"name":"bm25","context_a":"bm25"}' --arm '{"name":"bm25-mt","context_a":"bm25-mt"}' --arm
'{"name":"hybrid","context_a":"hybrid"}' --arm '{"name":"vote-section-hybrid","context_a":"vote-section-hybrid"}'`;
16:23 to 17:39 UTC. `output/robustness/devA300.jsonl` = the 300 task A lines of `data/dev/cases.jsonl`. The folder
was named with the machine's local date (13 October, Hong Kong time) and renamed to the UTC date during the run;
the predictions and raw answers were written in full, but paired_run's final `run.log` write failed on the old
path, so each arm's `run.log` was rebuilt from its raw answers (0 failed calls, 0 unparseable answers in every arm).

Every arm is a retriever alone, as a case that routing cannot handle would get it: top 8 chunks of at most 1,000
characters, prompt `A-v3-excerpts`, evidence `cited-pieces`. Scores: the starter's `evaluate.py` at `559b598`.

| Arm | Right of 300 | Macro-F1 | Evidence | Mean input tokens | Mean / p95 time (ms) |
|---|---|---|---|---|---|
| embed-e5-small (today's fallback) | 270 | 0.900 | 0.682 (137/201) | 1,868 | 2,240 / 3,546 |
| bm25 | 248 | 0.827 | 0.507 (102/201) | 2,396 | 2,245 / 2,840 |
| **bm25-mt** | **289** | **0.963** | **0.771 (155/201)** | 2,505 | 2,095 / 3,196 |
| hybrid | 281 | 0.936 | 0.766 (154/201) | 2,362 | 2,317 / 3,750 |
| vote-section-hybrid | 276 | 0.920 | 0.741 (149/201) | 2,362 | 2,281 / 3,920 |

For comparison, `section-route` (routing on) in the same evening's strategies run: 295 right, 0.983, evidence 0.985.

**Paired against embed-e5-small** (cases only one arm got right; two-sided sign test): bm25-mt 25 vs 6 (p = 0.0009),
hybrid 17 vs 6 (p = 0.035). bm25-mt against hybrid: 13 vs 5 (p = 0.096).

**Where bm25-mt gains** (right of the group, embed-e5-small → bm25-mt): gold neutral 86/99 → 95/99, cross-language
176/200 → 192/200, law claims 30/39 → 37/39, detail claims 37/43 → 42/43, summary claims 58/67 → 63/67. For a claim
the booklet does not cover, e5 still finds chunks that sound related and the model then calls them support or
contradiction; exact words on the translated claim find nothing convincing, so the model answers neutral.

Offline (R0) hybrid had the higher hit rate (0.866 against 0.851), but with the model bm25-mt answers better; the
hit rate counts the gold passage among 8 chunks, not what else the 8 chunks contain.
