### Fewer tokens for task A: P-short, K4 and both, against today, on dev (session 10, step 5)

**Run.** All 300 dev task A cases, four arms interleaved (`scripts/paired_run.py`, Williams design, one request
per second), Public AI `apertus-v1.5-8b`; every one of the 1,200 answers came from the same backend (blablador,
`vllm-0.23.1rc1 ... dd237840`), so all cases are same-backend cases. 0 failed calls, 0 HTTP 429.

- **today:** the defaults after step 2 (section-route, `A-v4-section-route-L1` + json_schema, evidence with halves).
- **P-short:** routed cases get `A-v5-short`, the same rules in fewer words: 200 fixed tokens (system prompt and
  user labels, Apertus v1 tokenizer) instead of 330; L1's sentence word for word; the label names of the dataset
  README ("Entailment (0)", "Unrelated / Neutral (1)", "Contradiction (2)").
- **K4:** `--section-top-k-a 4`: a routed case keeps only the 4 paragraphs most similar to the claim (e5), in
  their order.
- **P-short+K4:** both.

| arm | Macro-F1 | F1 E / N / C | evidence | neutral recall | unreadable | input + output tokens | fixes / breaks vs today |
|---|---|---|---|---|---|---|---|
| today | 0.980 | 0.980 / 0.990 / 0.969 | 0.980 | 1.000 | 0 | 1,237.8 + 14.5 | |
| P-short | 0.670 | 0.331 / 0.710 / 0.969 | 0.527 | 1.000 | 0 | 1,108.2 + 15.0 | 2 / 82 |
| **K4** | **0.990** | 0.990 / 0.995 / 0.985 | **0.975** | **1.000** | 0 | **808.5** + 14.3 | 5 / 2 (p 0.45) |
| P-short+K4 | 0.619 | 0.239 / 0.669 / 0.947 | 0.478 | 0.990 | 0 | 678.9 + 14.9 | 2 / 94 |

(`rule_check.json`, `scripts/rule_check.py`; Macro-F1 and evidence as the starter's scorer gives them,
`<arm>/official_score.txt`.)

**P-short fails.** It cites a paragraph and then answers neutral: 82 entailments became neutral (its most frequent
answers are `{"paragraphs": [n], "label": 1}`). Shortening today's wording changed how Apertus reads the rule;
the step does not try a third wording.

**K4 passes the TOKEN RULE on dev:** Macro-F1 +0.010 (rule: at most 0.005 lower), evidence −0.005 (at most 0.010
lower), neutral recall 1.000 (at least 0.98), no unreadable answers, input tokens −34.7 % (at least 10 % lower). It
goes to val (`2026-10-12_rashad_fewer-tokens-A_valA580`).

**K4 costs local time.** It embeds the paragraphs of every routed part with e5 (cached per part). Measured with the
fake model (`scripts/local_time.py`, image of this code, 2 CPUs; measured while another model run used the CPU):
0.215 s per case at 1.0 s per request (today 0.015 s) and 0.837 s at 0.3 s (today 0.300 s). Its REF SCORE is in
the val notes.
