### Task A prompts A1–A5 and second look A6 on dev and the on-topic neutral set (session 13, step 1): none passes

**Arms** (interleaved, all 300 dev task A cases and the 46 on-topic neutral cases, 7 arms in rotation, 1 request per
second also between a case's own calls, 20:09 to 21:38 UTC; all 2,422 answers and 3 second looks from one backend,
blablador `vllm-0.23.1rc1`). Prompts word for word from the session 13 instruction (`src/nli.py`, `--prompt-a`);
`--second-look-a6`: a neutral answer that cites paragraphs gets one more call (`A-v6-second-look`) with the cited
paragraphs and their neighbours, its finding same / different / nothing → 0 / 2 / 1. The on-topic set is
`scripts/paired_run.py --exclude-paragraphs` (session 10: the routed part without its gold passage, expected neutral).

| Arm | Macro-F1 | F1 ent / neu / con | Evidence | Input + output tokens per case | Unreadable | Gold 2 answered 1 | Fixes / breaks | Sign test p (one / two-sided) | On-topic answered neutral (of 46) |
|---|---|---|---|---|---|---|---|---|---|
| today | **0.983** | 0.980 / 0.995 / 0.975 | 0.985 | 1,240.4 + 14.7 | 0 | 1 | | | **32** |
| A1 `A-v6-says` | 0.902 | 0.975 / 0.843 / 0.888 | 0.970 | 1,291.2 + 75.6 | 6 | 0 | 5 / 29 | 1.0 / <0.001 | 13 |
| A2 `A-v6-residual` | 0.973 | 0.971 / 0.990 / 0.959 | 0.980 | 1,258.4 + 14.7 | 0 | 2 | 1 / 4 | 0.97 / 0.38 | 27 |
| A3 `A-v6-mismatch` | 0.980 | 0.975 / 0.995 / 0.970 | 0.990 | 1,337.1 + 26.1 | 0 | 0 | 1 / 2 | 0.88 / 1.0 | 19 |
| A4 `A-v6-opposite` | 0.964 | 0.975 / 0.969 / 0.946 | 0.985 | 1,334.1 + 53.3 | 2 | 0 | 2 / 8 | 0.99 / 0.11 | 28 |
| A5 `A-v6-words` | 0.983 | 0.980 / 0.995 / 0.975 | 0.990 | 1,251.4 + 16.4 | 0 | 0 | 1 / 1 | 0.75 / 1.0 | 25 |
| today+A6 | **0.987** | 0.980 / 1.000 / 0.980 | 0.990 | 1,242.1 + 14.7 | 0 | 0 | 1 / 0 | 0.5 / 1.0 | 30 |

Dev columns over the 300 dev cases (the on-topic cases only in the last column). Today's one dev error of the row
"gold contradiction answered neutral" is row 1016; A3, A5 and A6 fix it (A3 breaks rows 31 and 688, A5 row 500).

**A6:** 3 second looks (1 dev, 2 on-topic: 1 per 100 dev cases), 0 unreadable; on dev 1 answer changed (a fix); on
the on-topic set both second looks turned a neutral answer into a contradiction (rows 232 and 1026; their first answers
equal today's). The prompt arms make the on-topic set worse too: the more a prompt pushes towards "a different value
is never neutral", the more often the part without its passage is called a contradiction (A3 19, A1 13 of 46).

**PAIRED RULE, dev conditions** (decisions file): (b) dev at most 0.004 below today; (d) input tokens at most +4 %
(A6: +3 %); (e) no more unreadable answers; (g) on-topic neutral at least today's 32 − 0.05 × 46 → 30 (A6: at most one
flip away from neutral).

| Arm | (b) | (d) | (e) | (g) | Verdict |
|---|---|---|---|---|---|
| A1 | −0.082 fails | +4.1 % fails | 6 fails | 13 fails | **fails** |
| A2 | −0.010 fails | +1.5 % | 0 | 27 fails | **fails** |
| A3 | −0.003 holds | +7.8 % fails | 0 | 19 fails | **fails** |
| A4 | −0.020 fails | +7.6 % fails | 2 fails | 28 fails | **fails** |
| A5 | +0.000 holds | +0.9 % | 0 | 25 fails | **fails** |
| A6 | +0.003 holds | +0.1 % | 0 | 2 flips fails | **fails** |

**No step 1 arm can be adopted.** The val run (`2026-10-13_rashad_prompts-A_valA580`: today, A5, A3, today+A6, the
instruction's arms) shows which of session 12's 15 val errors answered neutral each one fixes; it decides nothing.
