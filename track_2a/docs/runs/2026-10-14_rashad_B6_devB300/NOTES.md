### B6, a task B second look on the ballot after an answer 2 (session 15, step 4): fails on dev, no val run, not adopted

**Arms** (interleaved, all 300 dev task B cases, 14:38 to 14:53 UTC, 1 request per second, arms alternating which goes
first, CPUs 0–1; every answer and second look from one backend, blablador `vllm-0.23.1rc1`; 0 failed calls, 0 HTTP
429): `today` = session 15's defaults (`v3-topic-first`, selector T, 32 tokens, no schema) and `today+B6`
(`--second-look-b6`: when the first answer is 2, one more request, a single user message with the reference's first
line, the case's vote field and the claim, then the instruction's question "Is the claim about the ballot named in the
title? Answer in JSON: {"same_ballot": true|false}.", schema `{"same_ballot": boolean}`, 16 tokens; false makes the
label 1). **Both arms share every first answer** (300 of 300; the arm sent second got the gateway's cache), so they
differ exactly by B6; no second look was a cache hit.

| Arm | Macro-F1 | F1 ent / neu / con | Input + output tokens per case | Unreadable | Gold 1 answered 2 (same / cross language) | Fixes / breaks | Sign test p (one / two-sided) |
|---|---|---|---|---|---|---|---|
| today | **0.987** | 0.985 / 0.995 / 0.980 | 815.3 + 8.6 | 0 | 1 (1 / 0) | | |
| today+B6 | 0.970 | 0.985 / 0.971 / 0.953 | 872.7 (+7.0 %) + 12.0 | 0 (first and second) | 0 | 1 / 6 | 0.99 / 0.125 |

**B6's second looks:** 99 (33.0 per 100 cases; one per first answer 2), 174 + 10.4 tokens each; 92 answered
`same_ballot: true` (the first answer stands), 7 `false` (label 1): **7 changed answers, 2 same-language, 5
cross-language; 1 fix, 6 breaks.**

- **The fix:** row 688 (fr → fr; the claim is about a cut in profit tax, the reference about the clean drinking water
  initiative), the one dev case of the targeted error (gold neutral answered contradiction, same-language).
- **The 6 breaks** (gold contradiction): rows 1063 (de → de), 1074 (de → it), 1144 (de → fr), 1223 (fr → de), 1263
  (fr → de), 1472 (it → de). Each claim is about the reference's own ballot ("Laut der Zusammenfassung …", "Le résumé
  indique que …") but states its opposite (the initiative "would promote intensive animal farming", the climate law
  "bans fossil fuels"). Apertus answers "not about the ballot named in the title" when the claim misstates that ballot:
  it reads "about the same ballot" as "agrees with the ballot". In every dev case the vote field repeats the title, so
  the VOTE line adds nothing the TITLE line does not say.

**PAIRED RULE, dev conditions (decisions file: val only if (b), (d) and (e) hold on dev):** (b) −0.017 fails (at most
−0.004); (d) +7.0 % fails (at most +5 %); (e) 0 against 0 holds. **No val run; B6 is not adopted** and stays in the
code as `--second-look-b6` (off). (f) is not measured (only for an arm passing (a)–(e)).

Files: `today/` and `today+B6/` (predictions, raw answers with `second_look_b6`, `official_score.json` from the starter's
`evaluate.py`), `arm_table.json` (`scripts/arm_table.py --cases output/devB/cases.jsonl`; B6's block: calls, changes,
fixes, breaks, changes by language).
