### bm25-ap fallback on the val sample (session 12 step 5): 0.957 / 0.755 against 0.875 / 0.588, passes the FALLBACK RULE

**Arms** (interleaved, the 300 balanced val task A cases of `data/val/sample300`, 1 request per second, 13:17 to 13:56
UTC; every answer and every translation from one backend, blablador `vllm-0.23.1rc1`), both forced to the fallback
(test force "no part", AP-part off), as on dev (`2026-10-13_rashad_S-and-fallbacks_devA300`):

| Arm | Macro-F1 | Evidence (of 204) | Neutral recall | Input + output tokens per case | Fixes / breaks |
|---|---|---|---|---|---|
| today-nopart (embed-e5-small) | 0.875 | 0.588 (120) | 0.927 | 1,827 + 15.6 | |
| **bm25ap-nopart** | **0.957** | **0.755** (154) | 0.979 | 2,609 + 45.4 | 29 / 5 (sign test p < 0.001) |

199 translation calls (claims in another language than the booklet), 0 failed; 0 failed calls, 0 unreadable answers.

**FALLBACK RULE** (Macro-F1 at least 0.02 above today's fallback and evidence not lower, on dev and on val): dev +0.057
/ +0.065, val **+0.082 / +0.167**: **passes; bm25-ap becomes the default fallback.** For comparison, Kaan's bm25-mt
(the same BM25 with a local translation model, not allowed in the image) scored 0.923 / 0.706 against e5's 0.871 /
0.589 on all 580 val cases in his run.
