### Combination of the adopted changes on val (session 13): H+S keeps S's result

Adopted in session 13: H (step 3, evidence only) and S (step 6, ranker). Steps 1 and 2 adopted nothing. The
combination (order prompt A → A6 → prompt B → H → S) is H+S, run once on all 580 val task A cases against today
(session 12's defaults written out: `evidence_hedge_a` false, ranker e5), interleaved, 1 request per second, 00:01 to
00:23 UTC, every answer from one backend (blablador). Task B is not sent: neither change alters a task B request.

| Arm | Macro-F1 | F1 ent / neu / con | Evidence | Input + output tokens per case | Unreadable | Gold 2 answered 1 | Fixes / breaks |
|---|---|---|---|---|---|---|---|
| today | 0.959 | 0.974 / 0.957 / 0.946 | 0.958 (384) | 1,210.7 + 14.7 | 0 | 14 | |
| **H+S** | **0.969** | 0.984 / 0.965 / 0.958 | **0.965** (387) | 1,224.9 + 14.7 | 0 | 12 | 7 / 1 (p = 0.035) |

Fixes: rows 17, 186, 341, 1025, 1159, 1162, 1174; break: row 1175 (as S alone in step 6, plus row 1162, which today
answers neutral in this run). **Dropping rule** (H+S more than 0.004 below the best single adopted change, S at
0.969 in step 6): 0.969 against 0.969: **the combination stays; the defaults are H and S.**
