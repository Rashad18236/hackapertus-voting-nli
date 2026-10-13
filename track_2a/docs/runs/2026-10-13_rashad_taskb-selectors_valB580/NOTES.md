### Task B selector T confirmed on val: TASK B RULE passes; T becomes task B's default (session 11 step 6b)

The val confirmation of `2026-10-13_rashad_taskb-selectors_devB300`: all 580 val task B cases, today (the whole
reference) against T (B-cut4 with selector T: a reference over 3,000 characters is cut to its first line and the 4
paragraphs whose first 300 characters are most similar to the claim by e5). Interleaved, 1 request per second,
01:41 to 02:04 UTC; all 1,160 answers from one backend (blablador `vllm-0.23.1rc1`).

| Arm | Macro-F1 | F1 ent / neu / con | Unreadable (neutral fallback) | Input + output tokens per case | Fixes / breaks vs today |
|---|---|---|---|---|---|
| today | 0.954 | 0.984 / 0.938 / 0.938 | 3 | 1,957 + 9.0 | |
| **T** | **0.968** | 0.982 / 0.963 / 0.958 | 1 | **820 + 9.4 (−58.1 %)** | 12 / 4 |

**TASK B RULE** (dev and val: Macro-F1 at most 0.005 lower, no more unreadable answers, input tokens at least 30 %
lower, local time at most +0.005 s per case at 1.0 and 0.3 s per request):

| | dev | val |
|---|---|---|
| Macro-F1, today → T | 0.967 → 0.987 | 0.954 → 0.968 |
| Unreadable answers | 2 → 0 | 3 → 1 |
| Input tokens | −59.1 % | −58.1 % |
| Local time per case at 1.0 / 0.3 s (dev, image) | 0.0067 / 0.0066 → 0.0077 / 0.0089 | (dev's) |

**T passes and becomes task B's default** (`context_b = "cut4-t"`); output tokens rise by 0.2 to 0.4 per case.
