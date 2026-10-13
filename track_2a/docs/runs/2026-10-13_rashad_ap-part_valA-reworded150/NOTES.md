### AP-part on reworded openings, confirmed on val: +0.051 Macro-F1 over VW; adopted as the step after the rules (session 11 step 3)

The val confirmation of `2026-10-12_rashad_ap-part_reworded150`: 150 balanced val task A cases (50 per label) whose
opening was replaced by other words for the same source with the dev replacements, unchanged
(`scripts/make_reworded.py --cases data/val/cases.jsonl`; the rules find no part in any of them). Same three arms,
interleaved, 1 request per second also inside a case, 00:38 to 01:09 UTC; all 600 requests answered by one backend
(blablador `vllm-0.23.1rc1`). The AP-part arm ran the implementation that ships (the worker process prepares every
valid part of the vote; the main process asks Apertus, then sends that part's request; "none" goes to the arm's
fallback, VW, as on dev).

| Arm | Macro-F1 | Evidence (of 100) | F1 ent / neu / con | Input + output tokens per case | of which the part call |
|---|---|---|---|---|---|
| today (embed-e5-small) | 0.898 | 0.520 (52) | 0.923 / 0.923 / 0.848 | 1,715 + 15.5 | 0 |
| VW | 0.876 | 0.650 (65) | 0.932 / 0.885 / 0.810 | 1,024 + 14.7 | 0 |
| **AP-part** | **0.926** | **0.840** (84) | 0.929 / 0.935 / 0.915 | 1,323 + 63.3 | 236 + 48.9 |

Fixes / breaks against today: VW 6 / 9, AP-part 10 / 6. 0 failed calls, 0 unreadable answers. Apertus's part equals
the original opening's for 127 of 150 (84.7 %): council 46/46, summary 38/38, committee 30/30, law 9/19, detail 4/17;
"none" 8 times.

**HYBRID RULE, AP-part:** dev +0.073, val **+0.051** over VW (needs +0.02 on both): **adopted** as the step after the
rules (`ap_part_a = "after-rules"`). A case the rules route is never touched; Apertus is asked only when the rules
find no part and the vote has valid parts. Its "none" (and a part the parser did not validate) goes to today's
fallback (embed-e5-small), since VW was not adopted (step 2). On dev and val the rules route all but a few cases, so
the default costs tokens only for those (G1/G2 list them).
