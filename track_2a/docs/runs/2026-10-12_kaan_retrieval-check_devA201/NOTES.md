### R0: retrievers offline on the 201 dev task A cases with a gold passage (no model calls)

**Command** (from `track_2a/`, for each variant): `EMBED_MODEL_DIR=models/multilingual-e5-small
MT_MODEL_DIR=models/m2m100_418M-ct2 python3 scripts/retrieval_check.py --variant <name> --per-case
output/robustness/r0_<name>.jsonl`; per-case results in each subfolder's `per_case.jsonl`. "Hit" = at least one of
the 8 sent chunks matches the gold passage (partial ratio ≥ 90 after normalising); "ceiling" = a sent page would
pass the evidence check.

| Variant | Hit | Same language (67) | Cross-language (134) | Evidence ceiling | Mean chars sent |
|---|---|---|---|---|---|
| embed-e5-small (today's fallback) | 0.741 | 0.851 | 0.687 | 0.612 | 5,386 |
| bm25 | 0.547 | 0.821 | 0.410 | 0.443 | 6,728 |
| bm25-mt (claim translated first) | 0.851 | 0.821 | 0.866 | 0.682 | 7,238 |
| hybrid (e5 + bm25-mt, RRF) | 0.866 | 0.866 | 0.866 | 0.672 | 6,796 |
| vote-section-hybrid | **0.876** | 0.866 | **0.881** | 0.682 | 6,853 |

embed-e5-small reproduces the recorded 0.741 (`2026-10-08_kaan_retrieval-check_embed-e5-small`), so the
measurement matches. By claim type (router's part, hit rate e5 → vote-section-hybrid): committee 0.74 → 0.93,
council 0.68 → 0.79, detail 0.88 → 0.96, law 0.84 → 1.00, summary 0.71 → 0.85.

Plain BM25 fails across languages (0.410), as expected: a German claim shares few words with a French booklet.
Translating the claim locally fixes that (0.866 cross-language) and is the largest single gain; fusing with e5
adds a little on same-language cases.
