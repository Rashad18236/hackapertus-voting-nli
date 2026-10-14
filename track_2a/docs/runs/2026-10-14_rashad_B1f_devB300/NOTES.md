### B1 retried with the format fixed (session 15, step 3): fails on dev, no val run, not adopted

**Arms** (interleaved, all 300 dev task B cases, 14:11 to 14:36 UTC, 1 request per second, arms alternating which goes
first, CPUs 0–1; every answer from one backend, blablador `vllm-0.23.1rc1`; 0 failed calls; the first 10 cases of both
arms were gateway cache hits from the format check, `2026-10-14_rashad_format-check-B1f_devB10`): `today` = session
15's defaults (`v3-topic-first`, selector T, 32 tokens, no schema) and `B1f` (`--prompt-b v7-same-ballot-f`: session
13's B1 prompt and schema with "at most 6 words" and `maxLength` 40 for both ballot fields, budget 64 tokens).

| Arm | Macro-F1 | F1 ent / neu / con | Input + output tokens per case | Unreadable | Gold 1 answered 2 (same / cross language) | Fixes / breaks | Sign test p (one / two-sided) |
|---|---|---|---|---|---|---|---|
| today | **0.987** | 0.985 / 0.995 / 0.980 | 815.3 + 8.7 | 0 | 1 (1 / 0) | | |
| B1f `v7-same-ballot-f` | 0.892 | 0.980 / 0.836 / 0.861 | 922.3 (+13.1 %) + 53.5 | **19** | 20 (6 / 14) | 2 / 30 | 1.0 / < 0.001 |

**PAIRED RULE, dev conditions (decisions file: val only if (b), (d) and (e) hold on dev):** (b) −0.094 fails (at most
−0.004); (d) +13.1 % fails (at most +6 %); (e) 19 unreadable against 0 fails. **No val run; B1f is not adopted** and
stays in the code as `--prompt-b v7-same-ballot-f`.

**What went wrong.**

- **Unreadable answers (19; Python wrote the neutral fallback for each):** the format check's 10 answers were readable,
  but over 300 cases the endpoint again ended 19 answers inside a string, with a run of whitespace, tab or NUL
  characters until the budget ran out ("no JSON object"): the failure of session 13's B1 at the shorter cap. 10 of
  the 30 breaks are these fallbacks (7 gold contradictions, 3 gold entailments).
- **Unrelated passages called contradictions (the other 20 breaks):** 20 gold-neutral cases (6 same-language, 14
  cross-language) were answered 2 against today's 1. In 17 of them Apertus wrote `same_ballot: true` with
  `claim_ballot` identical to `passage_ballot`; in 3 it wrote `same_ballot: false` and still label 2. The field meant
  to catch the other-ballot claim is mostly a copy of the passage's title.
- Over all 281 readable answers: `same_ballot` true in 232, false in 49; `claim_ballot` equals `passage_ballot` in 229
  of the 232 true answers.

**Language of `claim_ballot` (30 answers drawn at random, seed 15, judged by hand):** 3 unreadable; of the 27 readable,
21 are in the reference's language and 6 in the claim's language (all 6 cross-language cases; in 2 of them the value
is not a ballot name at all: "Keine Übereinstimmung", "Il comitato ritiene che il sistema svizz…"). 19 of the 21 in
the reference's language are a word-for-word copy of `passage_ballot`; of the 21 cross-language cases in the sample,
15 have `claim_ballot` in the reference's language, i.e. Apertus names the claim's ballot by copying the reference's
title rather than by reading the claim. Several values are cut by the 40-character cap inside a word (with the
booklet's soft hyphens or no-break spaces copied).

Files: `today/` and `B1f/` (predictions, raw answers, `official_score.json` from the starter's `evaluate.py`),
`arm_table.json` (`scripts/arm_table.py --cases output/devB/cases.jsonl`: Macro-F1, tokens, unreadable, error row with
the language split, fixes / breaks, sign test).
