### AP-all against today on the probe (session 11 step 3, run 1, unseen dates)

The same two arms as `2026-10-12_rashad_ap-all_devA300`, on the probe's 94 task A cases (the test rows of 2021-03-07
and 2025-09-28, 6 booklets), 23:07 to 23:19 UTC; all 288 requests answered by one backend (blablador
`vllm-0.23.1rc1`).

| Arm | Macro-F1 | Evidence (of 65) | F1 ent / neu / con | Input + output tokens per case | of which parsing calls |
|---|---|---|---|---|---|
| today | **0.971** | **0.954** (62) | 1.000 / 0.949 / 0.965 | **1,135 + 14.5** | 0 |
| AP-all | 0.951 | 0.877 (57) | 0.977 / 0.935 / 0.940 | 1,383 + 71.6 | 346 + 57.4 |

Fixes / breaks of AP-all against today: 1 / 3. 0 failed calls, 0 unreadable answers.

Today routes 90 of 94 probe cases (session 10's code routed 83; step 1's parser fixes added 7) and 4 fall back
(their claims' openings name no part the rules know). AP-all: Apertus's part equals the rules' for 84 of 94 claims
(89.4 %), "none" twice; its contents reading placed the vote for 86 of 94 cases (8 went booklet-wide). As on dev,
Apertus in the parsing roles costs Macro-F1 and evidence and adds tokens.

**Step 3b** (`../2026-10-12_rashad_ap-all_devA300/ap_claim_search.json`, `scripts/ap_claim_search.py`, no model
calls): of the dev and probe cases whose routed part is cut to 8 paragraphs and whose claim is in another language
than the booklet (17 dev + 1 probe), the 9 with a gold passage all have it among the 8 chosen with the claim, and
also with Apertus's restated statement: net gain 0 (needs ≥ 5). The measure as written (the first paragraph
today's correct answers cite) stays 7 of 7. **Run 4 is not run.**
