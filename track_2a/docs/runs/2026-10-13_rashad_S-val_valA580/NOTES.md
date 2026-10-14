### Model S on val (session 13, step 6): S passes the S RULE and becomes the default ranker

**Arms** (interleaved, all 580 val task A cases, 1 request per second, 23:37 to 00:00 UTC; all 1,160 answers and the
4 translation calls from one backend, blablador `vllm-0.23.1rc1`): today (e5 ranks a long part's paragraphs, the
fallback's chunks and vote names by meaning) and S (`--ranker S`, model S in the same three places). Task B is not
sent: its requests do not depend on the ranker (G1 on dev: 0 of 300 task B requests change), so S's task B part is
today's val task B answers from `2026-10-13_rashad_prompts-B_valB580` (decisions file).

| Arm | Macro-F1 | F1 ent / neu / con | Evidence | Input + output tokens per case | Unreadable | Gold 2 answered 1 | Fixes / breaks |
|---|---|---|---|---|---|---|---|
| today | 0.961 | 0.974 / 0.960 / 0.948 | 0.963 (386) | 1,210.7 + 14.7 | 0 | 13 | |
| **S** | **0.969** | 0.984 / 0.965 / 0.958 | **0.968** (388) | 1,224.9 + 14.7 | 0 | 12 | 6 / 1 (p = 0.06) |

S's fixes are rows 17, 186, 341, 1025, 1159 and 1174, all routing errors of session 12 (the gold passage was not
among the 8 paragraphs e5 kept of a long law or detail part); its break is row 1175. Of session 12's 15 val errors
answered neutral S fixes 3 (341, 1025, 1159).

**Local time per case** (`scripts/local_time.py`, image `sha-92984cd5d591`, 2 CPUs, three alternating rounds,
medians; `local_time_*.json`):

| | 1.0 s per request | 0.3 s per request |
|---|---|---|
| val task A, today / S | 0.0091 / 0.0073 s | 0.0088 / 0.0071 s |
| val task B, today (both arms) | 0.0052 s | 0.0060 s |
| dev task A, today / S (for comparison) | 0.0188 / 0.0148 s | 0.1271 / 0.0164 s |

**REF SCORE on val** (`ref_score_S_rule.json`; task A from this run, task B today's): today 0.9243 / 0.9166, S
**0.9269 / 0.9192** at 1.0 / 0.3 s per request. **S RULE** (higher at 0.3 s, not lower by more than 0.003 at 1.0 s):
**passes.** S becomes the default ranker; e5 stays in the image for task B's selector T. On val the local times of
both arms are below REF SCORE's reference (0.05 s for task A), so S wins on Macro-F1 and evidence there; on dev it
would also win on local time (0.127 → 0.016 s at 0.3 s per request).
