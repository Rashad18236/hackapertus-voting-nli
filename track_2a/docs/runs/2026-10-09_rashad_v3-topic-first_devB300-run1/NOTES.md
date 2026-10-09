### 2026-10-09, task B confirmation: v3-topic-first twice on the 300 dev task B cases (run 1 and run 2)

- Command, run twice one after the other (from `track_2a/`, on the host): `LLM_NAME=swiss-ai/apertus-v1.5-8b python3 -m src.cli --input output/devB/cases.jsonl --output docs/runs/<run>/predictions.jsonl --raw docs/runs/<run>/raw_answers.jsonl --prompt-b v3-topic-first`. Run 1: 01:25:24 to 01:33:17 UTC; run 2: 01:33:17 to 01:36:25 UTC. Code `8b1d418` (pipeline code as on `main` after PR #11). `output/devB/cases.jsonl` holds exactly the 300 task B lines of `data/dev/cases.jsonl` (checked).
- Prompt `v3-topic-first`, unchanged since session 2; no `response_format` (not strict JSON); max_tokens 32; temperature 0. Model `swiss-ai/apertus-v1.5-8b` on Public AI for every call.
- Scored with the starter's `evaluate.py`; comparison and error list by `scripts/taskb_analysis.py` (`rerun_analysis.json`, `docs/taskb_errors.md`); token breakdown by `scripts/taskb_tokens.py` (`tokens/`).

| | Run 1 | Run 2 |
|---|---|---|
| **Macro-F1** | **0.919** | 0.916 |
| F1 entailment / neutral / contradiction | 0.990 / 0.877 / 0.891 | 0.990 / 0.872 / 0.886 |
| Failed calls | 0 | 1 (HTTP 429 "Too Many Requests", row 1478; fallback neutral) |
| Unreadable answers | 1 (a bare `1`, row 645; fallback neutral = its gold label) | 1 (the same case, same answer) |
| Mean input tokens | 1,994 | 1,992 (the failed call counts as 0) |
| Mean / median / p95 time | 1,574 / 1,302 / 2,764 ms | 624 / 603 / 753 ms |

- **Cases with different labels: 1 of 300** (row 1478: contradiction in run 1, neutral in run 2), and that one is run 2's failed call. In the 299 cases both runs answered, **the answer text is identical in all 299** and so is the input token count.
- **Noise floor: Macro-F1 gap 0.0033** (0.9194 against 0.9161), all of it from one failed call. Temperature 0 on this server gave no answer-to-answer variation in back-to-back runs.
- Run 2 was about 2.5 times faster on the same prompts (median 0.6 s against 1.3 s). The endpoint gives no reason; a server-side cache of repeated prompts is a likely explanation, not verified. Times of a rerun of identical prompts are therefore not comparable with first runs.
- v3-topic-first scored 0.947 in session 2 (`s2-A-v3-topic-first`, before Public AI changed what it serves as `apertus-v1.5-8b` at about 13:25 UTC on 2026-10-08). Today it scores 0.919: the same prompt on today's server, not a change of ours.

Run 1, confusion matrix (rows: gold; columns: predicted entailment / neutral / contradiction):

| gold | entailment | neutral | contradiction |
|---|---|---|---|
| entailment (102) | 100 | 1 | 1 |
| neutral (99) | 0 | 82 | 17 |
| contradiction (99) | 0 | 5 | 94 |

Run 1, Macro-F1 by group:

| Group | Cases | Macro-F1 |
|---|---|---|
| claim German | 102 | 0.911 |
| claim French | 99 | 0.919 |
| claim Italian | 99 | 0.929 |
| passage German | 100 | 0.900 |
| passage French | 100 | 0.889 |
| passage Italian | 100 | 0.970 |
| same-language | 100 | 0.929 |
| cross-language | 200 | 0.914 |

Errors (24, all listed in `docs/taskb_errors.md`): 17 unrelated claims called a contradiction, 5 refuted claims called neutral, 1 supported claim called neutral, 1 supported claim called a contradiction.

Token breakdown of run 1's requests (300 cases; `tokens/summary.json`; counted with the Apertus v1 tokenizer, `swiss-ai/Apertus-8B-Instruct-2509`, because the v1.5 repository is gated):

| Part | Mean | p95 | Share of the mean |
|---|---|---|---|
| (a) fixed instructions: system prompt 194 + user-message labels 9 | 203 | 203 | 10.2 % |
| (b) examples | 0 | 0 | 0 % |
| (c) the passage | 1,737.5 | 4,209 | 87.1 % |
| (d) claim (the vote name is not sent in task B) | 35.4 | 56 | 1.8 % |
| (e) added by the endpoint (chat template), system + user message | 19 | 19 | 1.0 % |
| **total, usage.prompt_tokens (true)** | **1,994.2** | **4,463** | |

- (e) measured on the endpoint with `max_tokens` 1: one user message "Hello" gives prompt_tokens 63, i.e. 62 added (with no system message the template inserts its own default text); a system "Hello" plus a user "Hello" gives 21, i.e. **19 added**, the shape of every task B request.
- **Our count (a + b + c + d + e) against usage.prompt_tokens: on average 0.65 tokens too high (0.05 %), never more than 1 token off; exact in 106 of 300.** The ungated v1 tokenizer counts this endpoint's tokens almost exactly.
- Passage length in characters: min 1,068, median 3,674, p95 17,076, max 20,924 (mean 7,010); in tokens: min 250, median 915, p95 4,209, max 5,514. Neutral passages are all long (9,746 to 20,284 characters; the dataset pairs neutral claims with a whole part of another ballot).
- Output tokens: mean 7.6; 292 answers are exactly `{"label": n}` (7 tokens), 7 add a "Reasoning" paragraph after the JSON and stop at the 32-token cap, 1 is a bare `1` (2 tokens).
