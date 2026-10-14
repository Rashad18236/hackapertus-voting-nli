### Task B prompt B2 and selector B3 on val (session 13, step 2): B2 removes every unrelated passage answered contradiction, but fails (c) and (e)

**Arms** (interleaved, all 580 val task B cases, 3 arms in rotation, 1 request per second, 23:04 to 23:37 UTC; all
1,740 answers from one backend, blablador `vllm-0.23.1rc1`): today, B2 (`v7-unrelated`) and B3 (`cut4-tf`), the best
two by dev Macro-F1 (`2026-10-13_rashad_prompts-B_devB300`; B1 void, B4 failed on dev).

| Arm | Macro-F1 | F1 ent / neu / con | Input + output tokens per case | Unreadable | Gold 1 answered 2 (same / cross language) | Fixes / breaks | Sign test p (one / two-sided) | Session 12's 9 answered contradiction: fixed | New of that kind |
|---|---|---|---|---|---|---|---|---|---|
| today | 0.968 | 0.982 / 0.963 / 0.958 | 819.5 + 9.5 | 1 | 8 (4 / 4) | | | 0 | 1 (row 396) |
| B2 `v7-unrelated` | **0.974** | 0.982 / 0.973 / 0.968 | 845.5 + 8.0 | **2** | **0** | 8 / 4 | 0.19 / 0.39 | **8** (503, 602, 696, 747, 923, 941, 991, 992) | 0 |
| B3 `cut4-tf` | 0.966 | 0.976 / 0.966 / 0.955 | 840.0 + 9.5 | 1 | 7 (4 / 3) | 4 / 5 | 0.75 / 1.0 | 4 (503, 696, 923, 941) | 6 |

Session 12's ninth case (row 186, gold entailment answered contradiction) stays wrong in every arm. The unreadable
answers are a bare `1` without a JSON object (today row 654; B2 rows 396 and 654; B3 row 7): task B sends no
`response_format`, and the CLI writes the neutral fallback for them. B2's breaks: rows 1086, 1142, 1210, 1452 (a
supported or contradicted claim now called neutral: B2 sends "when unsure … the label is 1").

**PAIRED RULE for B2** (dev `2026-10-13_rashad_prompts-B_devB300` and val): (a) val +0.0068 (at least +0.005) holds;
(b) dev −0.0035 (at most −0.004) holds; **(c) fixes / breaks over dev and val 9 / 6, p = 0.30 (at most 0.10): fails**;
(d) input tokens +3.2 % dev, +3.2 % val (at most +4 %) holds; **(e) 2 unreadable answers against today's 1 on val
(dev 0 and 0): fails**; (f) not measured. **B2 is not adopted; B3 fails (a) and (b).** Step 2 adopts nothing.
