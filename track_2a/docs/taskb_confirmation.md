# Task B confirmation

2026-10-09, from 01:20 UTC, branch `claude/eager-cannon-08bx1h-taskb`. Run by
Rashad, with Claude Code. No prompt was changed. The test split was never
used. Runs: `docs/runs/2026-10-09_rashad_v3-topic-first_devB300-run1/` and
`-run2/` (notes and token breakdown in run 1's folder); errors:
`docs/taskb_errors.md`; decisions:
`docs/decisions/2026-10-09-0120_rashad_taskb-confirmation.md`.

## 1. In short

- **v3-topic-first scores 0.919 on today's server** (0.947 in session 2,
  before Public AI changed what it serves as `apertus-v1.5-8b`). It passes
  the 0.75 minimum comfortably.
- **Correction (2026-10-09, 03:00 UTC): run 2 was very likely answered from Public AI's gateway cache, so 0.0033 is not the model's noise floor** (`docs/taskb_cheap_fixes.md`, section 4).
- **Two identical runs differ by 0.0033 Macro-F1, our noise floor.** The two
  runs gave the same answer text in all 299 cases both answered; the whole
  gap is one call that failed with HTTP 429 in the second run.
- **The main error: a claim about another ballot called a contradiction**
  (17 of 24 errors) instead of neutral.
- **87 % of the input tokens are the passage**; the fixed instructions are
  10 %, the claim 2 %, the endpoint's own additions 1 %.

## 2. Every task B row in `docs/results.md`

`docs/results.md` now has a "Task B runs" table with, for every task B run:
prompt version, what changed against the previous version, number of cases,
strict JSON, max_tokens, Macro-F1, failed calls, mean input tokens, mean and
p95 time. The facts live in each run's `run.json` (`task_b` block), filled
from the run notes and the code at each run's commit:

- **Cases.** Every finished task B run used all 300 dev task B cases; none
  used 120. The first attempt of session 2's Run A stopped after 5 cases
  (all five calls failed with HTTP 504) and kept no predictions, so its
  score, tokens and times read "not recorded".
- **Strict JSON.** No task B run has used it: at every run's commit the task
  B call sends no `response_format`; the prompt only asks for a JSON object.
- **max_tokens.** 400 for the pre-contract `v1-json` (it asked for a quote
  too), 32 since `v2-label-only`.
- **What changed.** v1-json (first version) → v2-label-only (two changes: no
  evidence request, the guide's label wording) → v3-topic-first (the decision
  rule) → v4-topic-first-examples (three examples, +168 tokens; not kept).

## 3. v3-topic-first twice on the 300 dev cases

| | Run 1 | Run 2 |
|---|---|---|
| **Macro-F1** | **0.919** | 0.916 |
| F1 entailment | 0.990 | 0.990 |
| F1 neutral | 0.877 | 0.872 |
| F1 contradiction | 0.891 | 0.886 |
| Failed calls | 0 | 1 |
| Cases with a different label than the other run | 1 | 1 |

- **Correction (2026-10-09, 03:00 UTC):** the gateway in front of the model
  caches identical requests for about 10 minutes, and run 2 repeated each of
  run 1's requests 3 to 8 minutes later at the speed of a cache copy. So the
  identical texts below very likely came from the cache, and the noise floor
  of fresh answers is unknown. Not verifiable now: these runs recorded no
  endpoint identity.
- **Noise floor: 0.0033.** The one case with a different label is row 1478,
  whose call in run 2 failed with HTTP 429 ("Too Many Requests") and got the
  fallback label neutral. In all 299 cases both runs answered, the answer
  text is identical, character for character. At temperature 0 the model
  itself added no variation between two runs eight minutes apart; failed
  calls are the noise.
- Run 2 was much faster (median 0.6 s against 1.3 s) on the same prompts,
  probably because the endpoint cached them (not verified). Times of an
  immediate rerun do not compare with a first run.

**Run 1, confusion matrix** (rows: gold; columns: predicted):

| gold | entailment | neutral | contradiction |
|---|---|---|---|
| entailment (102) | 100 | 1 | 1 |
| neutral (99) | 0 | 82 | 17 |
| contradiction (99) | 0 | 5 | 94 |

**Run 1, Macro-F1 by language:**

| Group | Cases | Macro-F1 |
|---|---|---|
| claim in German | 102 | 0.911 |
| claim in French | 99 | 0.919 |
| claim in Italian | 99 | 0.929 |
| passage in German | 100 | 0.900 |
| passage in French | 100 | 0.889 |
| passage in Italian | 100 | 0.970 |
| same language | 100 | 0.929 |
| different languages | 200 | 0.914 |

**Run 1, the 24 errors** (all listed with id, languages, gold, predicted,
claim and passage start in `docs/taskb_errors.md`):

1. **A claim about another ballot called a contradiction (17).** The model
   says the passage refutes the claim, although the passage is about a
   different vote and does not deal with it. 13 of these claims attribute a
   statement ("according to the summary / the text / the committee / the
   Federal Council, ..."), 4 say "if the vote is accepted, ...".
2. **A refuted claim called neutral (5).** The refuting fact is one detail:
   a percentage (75 % / 25 %, 70 %), a reversed recommendation, an order of
   events.
3. **A supported claim called neutral (1)** and **a supported claim called a
   contradiction (1).**

## 4. Where the input tokens go (run 1, 300 cases)

| Part | Mean | p95 |
|---|---|---|
| (a) fixed instructions: system prompt (194) and the user message's labels "REFERENCE TEXT:" / "CLAIM:" (9) | 203 | 203 |
| (b) examples | 0 (v3 has none) | 0 |
| (c) the passage | 1,737.5 | 4,209 |
| (d) the claim, plus the vote name (not sent in task B) | 35.4 | 56 |
| (e) added by the endpoint itself | 19 | 19 |
| **total reported by the endpoint (usage.prompt_tokens)** | **1,994.2** | **4,463** |

- **(e)** was measured on the endpoint: a request with one system message and
  one user message of one word each reports 21 prompt tokens for 2 words, so
  the endpoint adds 19 tokens (the chat template's role markers). A single
  one-word user message reports 63: without a system message, the template
  adds its own default text (62 tokens).
- **Our own count against the endpoint's.** (a) to (d) were counted with
  the Apertus tokenizer. The v1.5 tokenizer is not public (gated), so the
  tokenizer of `swiss-ai/Apertus-8B-Instruct-2509` was used. Our total is on
  average 0.65 tokens above usage.prompt_tokens (0.05 %), never more than 1
  token off, and exact in 106 of 300 cases.
- **Passage length:** min 1,068, median 3,674, p95 17,076, max 20,924
  characters (250, 915, 4,209 and 5,514 tokens). Neutral passages are all long
  (9,746 to 20,284 characters).
- **Output tokens:** 7.6 on average.

## 5. Plain answers

- **Does the model output only the label?** Almost always. 292 of 300 answers
  were exactly `{"label": n}`. 7 added a "Reasoning" paragraph after the
  JSON (cut off at the token cap; the parser reads the label from the JSON),
  and 1 was a bare `1` without JSON (unreadable, so the fallback label
  neutral was written; it happened to be the gold label).
- **Is max_tokens capped?** Yes, at 32 for task B (`src/cli.py`).
- **Is strict JSON used in task B?** No. The task B request sends no
  `response_format`; only the prompt asks for `{"label": n}`.

## 6. What stays unverified

- Why run 2 was faster (an endpoint cache is likely, not confirmed).
- Whether the organisers' endpoint counts tokens the same way; the 19 tokens
  of (e) were measured on Public AI.
- How the v1.5 tokenizer differs from v1's: our v1-based count matched the
  endpoint within one token per case, so any difference is small for this
  text.
- The organisers' rate limits: HTTP 429 is not retried (the rule allows one
  retry for 5xx and timeouts only), and it cost one case here.
