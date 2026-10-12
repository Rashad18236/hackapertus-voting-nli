### Fewer tokens for task B: BP-short, B-cut4 and both, against today, on dev (session 10, step 5)

**Run.** All 300 dev task B cases, four arms interleaved (Williams design, one request per second), Public AI
`apertus-v1.5-8b`; all 1,200 answers from one backend (blablador). 0 failed calls, 0 HTTP 429.

- **today:** the defaults after step 2: `v3-topic-first`, the whole reference (no cut), max_tokens 32, no schema.
- **BP-short:** `v6-short`, v3's rules in fewer words (144 fixed tokens with the Apertus v1 tokenizer instead of
  203; the README's label names).
- **B-cut4:** a reference over 3,000 characters becomes its first line plus the 4 paragraphs most similar to the
  claim (multilingual-e5-small), in their order; prompt unchanged.
- **BP-short+B-cut4:** both.

| arm | Macro-F1 | F1 E / N / C | neutral recall | unreadable | input + output tokens | fixes / breaks vs today |
|---|---|---|---|---|---|---|
| today | 0.967 | 0.985 / 0.963 / 0.951 | 0.929 | 2 | 1,994.2 + 8.4 | |
| BP-short | 0.667 | 0.431 / 0.671 / 0.898 | 0.960 | 29 | 1,935.2 + 6.7 | 3 / 86 |
| **B-cut4** | **0.987** | 0.990 / 0.990 / 0.980 | 0.980 | **0** | **882.6** + 8.9 | 7 / 1 (p 0.07) |
| BP-short+B-cut4 | 0.718 | 0.532 / 0.710 / 0.912 | 1.000 | 24 | 823.6 + 7.2 | 8 / 79 |

(`rule_check.json`; Macro-F1 as the starter's scorer gives it, `<arm>/official_score.txt`.)

**BP-short fails**: it answers neutral far more often (153 of 300 `{"label": 1}`), and 29 answers cannot be read
(28 a bare digit such as `2`, one `1 (Unrelated / Neutral)`). Its fixed text saves 59 tokens on about 2,000, 3 %: it could not have
met the rule's 10 % anyway.

**B-cut4 passes the TOKEN RULE on dev**: Macro-F1 +0.020 (rule: at most 0.005 lower), fewer unreadable answers (0
against 2), input tokens −55.7 % (at least 10 % lower). Of its 7 fixes, 5 are neutral claims (paired with a long
unrelated section) that today called a contradiction; the others are one contradiction and one entailment; its
one break is an entailment it calls a contradiction (row 232). It goes to val
(`2026-10-12_rashad_fewer-tokens-B_valB580`). Its local time (e5 embedding of every reference over 3,000
characters) enters the decision through REF SCORE (val notes).
