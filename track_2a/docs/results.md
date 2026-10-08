# Results

One row per run. Every number comes from an actual run; each run's
predictions, raw answers and scores are in `docs/runs/`. Dev = the 300 dev
rows (`data/splits.json`). Test has not been run.

Since the contract-alignment stage, the official scorer is the starter's
`evaluate.py` (commit `559b598`), run unchanged. Its minimum Macro-F1 for a
valid submission is 0.75 on task B and 0.60 on task A.

| Date | Commit | Format | Task | Model | Endpoint | Prompt | Macro-F1 | Evidence | Parse failures | Failed calls | Mean input tokens | Mean time (ms) | p95 time (ms) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-08 | `16ec6af` | **pre-contract** | beginner (= task B), dev 300 | swiss-ai/apertus-v1.5-8b | Public AI | v1-json | 0.202 (our scorer) | exact match / overlap F1: n/a (no gold evidence) | 8 | 9 | 1938 | 4118 | 6018 |
| 2026-10-08 | `bb78f85` | official | task B, dev 300 | swiss-ai/apertus-v1.5-8b | Public AI | v2-label-only | **0.541** (official scorer; ours agrees) | not scored for task B | 0 | 1 | 1963 | 1944 | 2815 |
| 2026-10-08 | session-2 ¹ | official | task B, dev 300 (Run A) | swiss-ai/apertus-v1.5-8b | Public AI | v3-topic-first | **0.947** (E 0.955, N 0.934, C 0.951) | not scored for task B | 2 | 5 | 1968 | 2748 | 2878 |
| 2026-10-08 | session-2 ¹ | official | task B, dev 300 (Run C) | swiss-ai/apertus-v1.5-8b | Public AI | v4-topic-first-examples | 0.933 (E 0.985, N 0.907, C 0.906) | not scored for task B | 0 | 0 | 2162 | 1765 | 2986 |
| 2026-10-08 | session-2 ² | official | task A, dev sample 60 (20 per label) | swiss-ai/apertus-v1.5-8b | Public AI | A-v3-fulldoc | **0.767** (E 0.872, N 0.744, C 0.684) | evidence score 0.375 (15/40) | 6 | 0 | 41124 | 9617 | 23331 |
| 2026-10-08 | session-2 ² | official | **task A, all 300 dev cases** (reference row) | swiss-ai/apertus-v1.5-8b | Public AI | A-v3-fulldoc | **0.589** (E 0.671, N 0.635, C 0.462) | evidence score 0.209 (42/201) | 110 | 3 | 39706 | 11501 | 30334 |

¹ Runs A and C ran from the `session-2` working tree before its first commit: the code equals the first session-2 commit except that `llm.py` had no retry yet and the task A path was still the placeholder (B-only input never reaches it). Per-label F1 is shown as E/N/C.

² Task A runs used code identical to commit `4e90ddc` (prompt `A-v3-fulldoc`, retry active).

The second run also answered the 300 dev task A requests with the
placeholder (label 1, no model call): official task A Macro-F1 0.165, the
always-neutral value. It is not a task A result.

## Notes per run

### 2026-10-08, `16ec6af`, v1-json (pre-contract)

- Our own input format and our own `evaluate.py`, before the official contract was known. Kept for comparison; not comparable in every detail (failed cases had no label, not label 1).
- Command: `python3 -m src.cli data/dev_inputs.jsonl docs/runs/baseline-v0_dev_predictions.jsonl --raw docs/runs/baseline-v0_dev_raw_answers.jsonl`, run on the host from a sandbox (not in Docker), 04:56 to 05:17 UTC.
- Score: `python3 -m src.evaluate docs/runs/baseline-v0_dev_predictions.jsonl data/dev_gold.jsonl` at that commit (full output in `docs/runs/baseline-v0_dev_scores.json`). scikit-learn's `f1_score(average="macro")` gives the same 0.202.
- 17 of 300 cases have no label and count as wrong: 8 parse failures (5 answers cut off at the 400-token limit while quoting) and 9 calls that failed with HTTP 504 from the Public AI gateway after about 61 s.
- Mean input tokens include the 9 failed calls as 0 tokens; over the 291 completed calls the mean is 1998. Mean time includes the 9 failed calls at about 61 s each; without them it is 2355 ms.
- Accuracy 0.310. Per-class F1: entailment 0.000, neutral 0.000, contradiction 0.606. The model never answered 0.
- Evidence was kept for 34.6 % of entailment/contradiction predictions; the rest were empty or not verbatim.

### 2026-10-08, `bb78f85`, v2-label-only (official format)

- Command (from `track_2a/`, in Docker through the real `make run`; the proxy flags are needed only in our sandbox):
  `make run CASES=data/dev/cases.jsonl OUTPUT_DIR=docs/runs/contract-v2-dev EXTRA_ARGS="--raw /output/raw_answers.jsonl" DOCKER_RUN_FLAGS="--network host -e HTTPS_PROXY"`,
  05:29 to 05:39 UTC, 600 requests (300 task B with a model call, 300 task A placeholders). Exit code 0; 600 responses.
- Official score (in the starter checkout):
  `uv run python evaluate.py --predictions .../contract-v2-dev/predictions.jsonl --expected .../data/dev/expected-labels.jsonl --cases .../data/dev/cases.jsonl`
  (full report in `docs/runs/contract-v2-dev/official_score.json`). Our `python -m src.evaluate` gives the same 0.5406 (`breakdown.json`, `docs/self_checks.md`).
- Task B accuracy 0.630. Per-class F1: entailment 0.922 (P 0.978, R 0.873), neutral 0.057 (R 0.030), contradiction 0.642 (R 0.980).
- Confusion (rows gold): entailment 89 / 3 / 10; neutral 0 / 3 / 96; contradiction 2 / 0 / 97. Neutral is almost always called contradiction.
- Same-language 0.543, cross-lingual 0.539; language pairs 0.415 (fr->de) to 0.618 (it->fr), source->claim.
- 1 call failed (HTTP 502 from Public AI) and got the fallback label 1. 0 parse failures: 295 of 300 answers were exactly `{"label": n}`; 4 added text after the JSON (3 a "Reasoning" paragraph, 1 the same JSON again in a code fence), which the parser handles.
- Mean input tokens are over the 300 task B cases (the failed call counts as 0); mean output 7.3 tokens (was 70).
- Two changes against the pre-contract run, so the gain cannot be split between them: the evidence request was removed, and the label definitions now use the guide's wording.

### 2026-10-08, session 2, Run A: v3-topic-first (task B)

- Only change against `v2-label-only`: the decision rule (first check whether the reference deals with the claim's subject at all; contradiction only for an incompatible statement; missing information is never a contradiction). See `docs/neutral_analysis.md`.
- Command: `make run CASES=output/devB/cases.jsonl OUTPUT_DIR=docs/runs/s2-A-v3-topic-first EXTRA_ARGS="--prompt-b v3-topic-first --raw /output/raw_answers.jsonl"` (+ sandbox proxy flags); `output/devB/` holds the 300 task B dev cases and their expected labels, filtered by id. 06:10 to 06:24 UTC.
- First attempt stopped after 5 of 5 calls failed (HTTP 504, endpoint outage, log in `s2-A-v3-topic-first_attempt1/`); rerun once after a two-minute wait, as the session rule says.
- Rerun: 5 of 300 calls failed (1.7 %, the first five cases, all gold entailment, label 1 by fallback) and 2 answers were unparseable (one was a bare `1` without JSON). Mean time includes the failed calls (about 61 s each); without them it is 1753 ms and mean input tokens 2001.
- Confusion (rows gold E/N/C): E 95/6/1, N 0/92/7, C 2/0/97. Same-language 0.960, cross-lingual 0.940; language pairs 0.882 (de->de) to 1.000 (it->it).
- On the 295 cases that Runs A and C both answered: v3 0.963, v4 0.933.

### 2026-10-08, session 2, Run C: v4-topic-first-examples (task B)

- Only change against v3: three short examples (one per label, an invented ballot, not from the dataset) before the answer format. They add exactly **168 input tokens per case** (paired difference on the same cases).
- Same command with `--prompt-b v4-topic-first-examples`, 06:24 to 06:33 UTC. 0 failed calls, 0 parse failures.
- Confusion (rows gold E/N/C): E 101/0/1, N 0/83/16, C 2/1/96. The examples help entailment but push more neutral cases to contradiction. Same-language 0.928, cross-lingual 0.935.
- Not kept: lower Macro-F1 than v3 on the same cases, and 168 more input tokens per case.

### 2026-10-08, session 2: task A full-document baseline, 60-case sample (A-v3-fulldoc)

- Whole booklet in one call (pypdf text, `=== PAGE n ===` before each page), then VOTE and CLAIM; the answer is `{"pages": [...], "label": n}`; evidence = the cited pages' text (split at 5,000 characters, at most five items). Prompts A-v1 and A-v2 (pages after the label) never named pages and were not scored; see `decisions.md`.
- Sample: 20 task A dev cases per label, round-robin over the 9 language pairs, seed 42 (`output/devA60/`, filtered by id from `data/dev/`). Booklets: the 44 dev booklets from the starter's `prepare_cases.py --download-booklets`, mounted read-only at `/data/booklets`.
- Command: `make run CASES=output/devA60/cases.jsonl BOOKLETS=output/booklets_dev OUTPUT_DIR=docs/runs/s2-A60-A-v3-fulldoc EXTRA_ARGS="--raw /output/raw_answers.jsonl"` (+ sandbox proxy flags), 06:39 to 06:49 UTC. 0 failed calls; 6 unparseable answers (label-1 fallback); format check: no errors.
- Confusion (rows gold E/N/C): E 17/2/1, N 0/16/4, C 2/5/13.
- Input tokens per case: mean 41,124 (the whole booklet). Time: mean 9.6 s, p95 23.3 s.

### 2026-10-08, session 2: task A full-document baseline, all 300 dev cases (A-v3-fulldoc) — reference row

- The 60-case sample run plus a run on the other 240 task A dev cases (`s2-A240-A-v3-fulldoc`, 06:49 to 07:37 UTC), with the same image, prompt and settings, merged in `docs/runs/s2-A300-A-v3-fulldoc/` and scored once with the official scorer on all 300 task A dev cases (`output/devA/`, filtered by id from `data/dev/`). Format check: no errors.
- **This is the reference row for every later context-selection experiment:** 39,706 input tokens per case on average (the whole booklet), mean 11.5 s, p95 30.3 s.
- Below the 0.60 minimum, mostly because of unparseable answers: 110 of 300 (37 %). 84 of the 104 in the 240-case part were reasoning in prose that hit the 64-token answer limit before the JSON, 16 were a stray `<|inner_prefix|>` token, and 4 were page lists that were too long. All got the label-1 fallback, which is why 55 gold contradictions came out neutral. The 60-case sample had only 6 such answers (10 %), so its 0.767 was optimistic.
- Diagnostic only (not an official number): on the 187 cases with a parsed answer, Macro-F1 is 0.765.
- Confusion (rows gold E/N/C): E 57/33/12, N 3/87/9, C 8/55/36. Same-language 0.647, cross-lingual 0.560; by booklet language de 0.522, fr 0.588, it 0.656.
- Evidence: an upper bound measured on the 60-case sample shows that at least 35 of its 40 gold entailment/contradiction cases have a page that matches the gold passage under the official rule (0.875), against 15/40 actually cited. So the evidence gap is page choice, not page text.
