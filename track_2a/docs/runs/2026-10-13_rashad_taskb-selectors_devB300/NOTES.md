### Task B: fewer tokens without local time (session 11 step 6): T and H pass the TASK B RULE on dev, E fails on local time

**Step 6a, no model.** B-cut4 (E, session 10) cuts a reference over 3,000 characters to its first line (the ballot's
title) and the 4 paragraphs most similar to the claim by e5; it halves the tokens but its e5 work cost local time.
Cheaper selectors of the same 4 paragraphs (`src/taskb_context.py`, `--context-b cut4-*`): **Q** e5's own 8-bit
export (`model_qint8_avx512_vnni.onnx`, same repository and licence), **T** e5 on the first 300 characters of each
paragraph, **L** shared character 4-grams and numbers (no model), **H** L when the claim is in the reference's
language, else T.

Agreement with E's paragraphs on the 218 dev references E cuts (`selector_agreement.json`,
`scripts/taskb_selectors.py`; E's own mean is 3.81 because some references have fewer than 4 paragraphs after the
first line):

| Selector | Mean paragraphs shared with E | All equal to E |
|---|---|---|
| Q | 3.36 | 60 % |
| T | 3.06 | 42 % |
| H | 2.78 | 37 % |
| L | 2.03 | 23 % |

Local time per case of the image with each selector (`local_time/`; 2 CPUs, the step 4 defaults, fake model after
1.0 / 0.3 / 0.1 s per request; requests the replay table does not know get the fake model's fixed answer, which does
not change the local work):

| Context | 1.0 s | 0.3 s | 0.1 s | within +0.005 s of today at 1.0 and 0.3 s? |
|---|---|---|---|---|
| today (whole reference) | 0.0067 | 0.0066 | 0.0067 | — |
| E | 0.0110 | 0.661 | not measured | no |
| Q | 0.0099 | 0.440 | not measured | no |
| T | 0.0077 | 0.0089 | not measured | yes |
| H | 0.0072 | 0.0082 | 0.059 | yes |
| L | 0.0065 | 0.0066 | 0.0067 | yes |

With step 4's light-first lanes, T's and H's short e5 work hides behind the requests down to 0.3 s per request; E and
Q embed every paragraph in full and do not. The 1–2 best selectors within the bound by agreement: **T and H**.

**Step 6b, dev run** (interleaved, 300 dev task B cases, 1 request per second, 01:10 to 01:41 UTC; all 1,200 answers
from one backend, blablador `vllm-0.23.1rc1`):

| Arm | Macro-F1 | F1 ent / neu / con | Unreadable (neutral fallback) | Input + output tokens per case | Fixes / breaks vs today |
|---|---|---|---|---|---|
| today | 0.967 | 0.985 / 0.963 / 0.951 | 2 | 1,994 + 8.3 | |
| E | 0.987 | 0.990 / 0.990 / 0.980 | 0 | 883 + 8.7 (−55.7 %) | 7 / 1 |
| **T** | 0.987 | 0.985 / 0.995 / 0.980 | 0 | **815 + 8.5 (−59.1 %)** | 8 / 2 |
| H | **0.993** | 0.990 / 1.000 / 0.990 | 0 | 923 + 8.5 (−53.7 %) | 8 / 0 |

**TASK B RULE on dev** (Macro-F1 at most 0.005 lower, no more unreadable answers, input tokens at least 30 % lower,
local time at most +0.005 s per case at 1.0 and 0.3 s): **T passes, H passes, E fails** (local time at 0.3 s). The
best for val: T, by REF SCORE (mean S_B over 1.0 and 0.3 s with the measured tokens and local times: T 0.927, H 0.922;
H's higher Macro-F1 is 2 cases of 300, T's tokens are 12 % fewer). Val: `2026-10-13_rashad_taskb-selectors_valB580`.
