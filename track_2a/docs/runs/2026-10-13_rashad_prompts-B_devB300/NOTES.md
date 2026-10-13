### Task B prompts B2, B4 and selector B3 on dev (session 13, step 2): only B2 is not ruled out

**Arms** (interleaved, all 300 dev task B cases, 4 arms in a balanced Latin square, 1 request per second, 22:35 to
23:04 UTC; all 1,200 answers from one backend, blablador `vllm-0.23.1rc1`). B1 (`v7-same-ballot`) is void after the
format check (`2026-10-13_rashad_format-check-B_devB5`); prompts word for word from the session 13 instruction.

| Arm | Macro-F1 | F1 ent / neu / con | Input + output tokens per case | Unreadable | Gold 1 answered 2 (same / cross language) | Fixes / breaks | Sign test p (one / two-sided) |
|---|---|---|---|---|---|---|---|
| today (v3-topic-first, T) | **0.987** | 0.985 / 0.995 / 0.980 | 815.3 + 8.7 | 0 | 1 (1 / 0) | | |
| B2 `v7-unrelated` | 0.983 | 0.985 / 0.990 / 0.974 | 841.3 + 7.6 | 0 | 0 | 1 / 2 | 0.88 / 1.0 |
| B3 `cut4-tf` | 0.980 | 0.975 / 0.985 / 0.980 | 839.6 + 8.8 | 0 | 1 (1 / 0) | 0 / 2 | 1.0 / 0.5 |
| B4 `v7-claim-first` | 0.980 | 0.980 / 0.985 / 0.974 | 851.3 + 39.3 | **5** | 0 | 1 / 3 | 0.94 / 0.63 |

B4's 5 unreadable answers stop `claim_says` at its `maxLength` of 120 characters with a stray tab or NUL character, or
with whitespace until the budget ends: not valid JSON (the same endpoint behaviour as B1's void answer).

**PAIRED RULE, dev conditions:** B2: (b) −0.0035 holds (at most −0.004), (d) +3.2 % holds (at most +4 %), (e) holds:
**goes to val**. B3: (b) −0.0067 fails. B4: (b) −0.0068, (d) +4.4 %, (e) 5 unreadable: fails. Val
(`2026-10-13_rashad_prompts-B_valB580`) runs today, B2 and B3 (the best two by dev Macro-F1).
