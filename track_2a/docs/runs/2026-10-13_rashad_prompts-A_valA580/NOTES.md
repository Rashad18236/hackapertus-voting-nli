### Task A prompts A5, A3 and second look A6 on val (session 13, step 1): all three fix about half of the 15 errors answered neutral, none can be adopted

**Arms** (interleaved, all 580 val task A cases, 4 arms in a balanced Latin square, 1 request per second, 21:40 to
22:34 UTC; all 2,320 answers and 12 second looks from one backend, blablador `vllm-0.23.1rc1`): today, the two best
prompt arms by dev Macro-F1 (A5 0.9834, A3 0.9801) and today+A6, as the instruction lists them. **Run for the report
only:** each of them already failed a dev condition (`2026-10-13_rashad_prompts-A_devA300-ontopic46`).

| Arm | Macro-F1 | F1 ent / neu / con | Evidence | Input + output tokens per case | Unreadable | Gold 2 answered 1 | Fixes / breaks | Sign test p (one / two-sided) | Session 12's 15 answered neutral: fixed | New of that kind |
|---|---|---|---|---|---|---|---|---|---|---|
| today | 0.959 | 0.974 / 0.957 / 0.946 | 0.960 | 1,210.7 + 14.7 | 0 | 14 | | | 0 | 1 (row 1162) |
| A5 `A-v6-words` | 0.971 | 0.971 / 0.983 / 0.959 | 0.978 | 1,221.6 + 16.4 | 0 | 5 | 10 / 3 | 0.046 / 0.092 | 7 | 0 |
| A3 `A-v6-mismatch` | 0.970 | 0.974 / 0.977 / 0.958 | **0.988** | 1,307.2 + 25.9 | 0 | **2** | 13 / 7 | 0.13 / 0.26 | **9** | 0 |
| today+A6 | **0.973** | 0.974 / 0.981 / 0.964 | 0.983 | 1,219.9 + 14.9 | 0 | 5 | 9 / 1 | **0.011** / 0.022 | 8 | 0 |

Which of session 12's 15 (rows): A5 fixes 341, 1053, 1210, 1226, 1318, 1404, 1467; A3 fixes 1053, 1200, 1210, 1226,
1318, 1347, 1351, 1404, 1467; A6 fixes 1053, 1151, 1210, 1226, 1309, 1318, 1404, 1467. Rows 1025, 1159 and 235 stay
wrong in every arm (all three are routing errors: the gold passage is not in the part as sent,
`2026-10-13_rashad_error-types_valAB`). Breaks: A5 rows 13, 991, 1410; A3 rows 13, 576, 591, 663, 773, 816, 859; A6
row 950.

**A6 on val:** 12 second looks (2.1 per 100 cases), 0 unreadable; 11 answers changed: 9 fixes, 1 break, 1 wrong to
another wrong label.

**PAIRED RULE over dev and val:**

| Arm | (a) val ≥ +0.005 | (b) dev ≥ −0.004 | (c) fixes / breaks dev+val, p ≤ 0.10 | (d) tokens | (e) unreadable | (g) on-topic (dev) | Verdict |
|---|---|---|---|---|---|---|---|
| A5 | +0.012 holds | +0.000 holds | 11 / 4, p = 0.059 holds | +0.9 % holds | 0 holds | 25 of 46, needs 30: **fails** | not adopted |
| A3 | +0.011 holds | −0.003 holds | 14 / 9, p = 0.20 **fails** | +8.0 % **fails** | 0 holds | 19: **fails** | not adopted |
| A6 (SECOND-LOOK RULE) | +0.014 holds | +0.003 holds | 10 / 1, p = 0.006 holds | +0.8 % holds | 0 holds | 2 flips, at most 1: **fails** | not adopted |

(f) was not measured: no arm could pass. **A6 misses its rule by one on-topic case** (rows 232 and 1026 of the
on-topic set, where the part without its passage was read as contradicting the claim); on val it is the best arm.
That trade-off is for the team (session report).
