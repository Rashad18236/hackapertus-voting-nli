### Model S in task A and the bm25-ap fallback on dev (session 12 steps 4 and 5): S fails its rule by one case, bm25-ap passes (+0.057 forced)

**Arms** (interleaved, all 300 dev task A cases, 1 request per second, 11:47 to 12:45 UTC; every answer and every
translation call from one backend, blablador `vllm-0.23.1rc1`):

- **today**: the defaults (e5 chooses a long part's 8 paragraphs and the fallback's 8 chunks);
- **S**: model S in place of e5 (`--ranker S`): long parts, the fallback's chunks, vote names by meaning;
- three arms forced to the fallback (test force "no part" with AP-part off, so the fallback itself is measured, as in
  Kaan's runs with routing off): **today-nopart** (embed-e5-small), **S-nopart** (the same chunks ranked by S),
  **bm25ap-nopart** (`--fallback-a bm25-ap`: Kaan's BM25 on the claim; for the 200 claims in another language than
  the booklet, Apertus first translates the claim, `AP-translate-v1`, 127.5 + 42.2 tokens per call, 0 failed).

| Arm | Macro-F1 | Evidence (of 201) | Neutral recall | Input + output tokens per case | Fixes / breaks |
|---|---|---|---|---|---|
| today | **0.980** | **0.980** (197) | 1.000 | 1,238 + 14.5 | |
| S | 0.973 | 0.970 (195) | 1.000 | 1,251 + 14.5 | 0 / 2 vs today |
| today-nopart | 0.900 | 0.672 (135) | 0.869 | 1,868 + 15.8 | |
| S-nopart | 0.913 | 0.677 (136) | 0.929 | 2,385 + 16.1 | 18 / 14 vs today-nopart |
| **bm25ap-nopart** | **0.956** | **0.736** (148) | 0.949 | 2,591 + 44.3 | **23 / 6** vs today-nopart (sign test p = 0.002) |

**S against today.** Only 24 of 300 requests differ (23 long parts cut to 8 paragraphs, 1 fallback); S answers 21 of
them right, today 23: rows 31 and 1052 (both long "detail" parts) break, none is fixed. **S RULE (a)** (Macro-F1 and
evidence at most 0.005 below today's): Macro-F1 −0.0067 and evidence −0.010: **S fails** and stays off, although
(b) passes (forced fallback +0.013) and (c) passes clearly (step 1c: task A's local time at 0.3 s per request 0.144 →
0.018 s per case, peak memory 2,286 → 200 MiB). No val run is spent on it.

**bm25-ap against today's fallback (FALLBACK RULE, dev part):** +0.057 Macro-F1 (needs +0.02) and +0.065 evidence
(needs not lower): **passes on dev**; it goes to the val sample (`2026-10-13_rashad_bm25ap-fallback_valA300`). Its
cost: +723 input and +28.5 output tokens per fallback case (the translation call and longer chunks), only on cases
section-route cannot route (in session 11's final runs: 1 of 300 dev, 3 of 580 val and 4 of 94 probe cases). Kaan's bm25-mt with a
local translation model scored 0.963 / 0.771 in the same situation; Apertus's translation gets 0.956 / 0.736 without
a translation model in the image.
