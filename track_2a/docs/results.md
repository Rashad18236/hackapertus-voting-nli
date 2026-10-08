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
| 2026-10-08 | session-2 ³ | re-parsed offline (no new calls) | task A, all 300 dev cases | swiss-ai/apertus-v1.5-8b | Public AI | A-v3-fulldoc + prose-label parser | 0.608 (E 0.686, N 0.647, C 0.491) | evidence score 0.209 (42/201) | 97 | 3 | 39706 | 11501 | 30334 |
| 2026-10-08 | session-2 ³ | official | task A, dev sample 60, max_tokens 256 (endpoint drift, see notes) | swiss-ai/apertus-v1.5-8b | Public AI | A-v3-fulldoc | 0.398 (E 0.276, N 0.467, C 0.452) | evidence score 0.150 (6/40) | 34 | 0 | 41124 | 11660 | 31684 |
| 2026-10-08 | session-2 ³ | re-parsed offline (no new calls) | task A, dev sample 60, max_tokens 256 | swiss-ai/apertus-v1.5-8b | Public AI | A-v3-fulldoc + prose-label parser | 0.553 (E 0.595, N 0.520, C 0.545) | evidence score 0.150 (6/40) | 14 | 0 | 41124 | 11660 | 31684 |
| 2026-10-08 | session-2 ⁴ | official | task A, dev sample 60, JSON mode (attempt 1; 27 % failed calls) | swiss-ai/apertus-v1.5-8b | Public AI | A-v3-fulldoc | 0.378 (E 0.357, N 0.483, C 0.294) | evidence score 0.125 (5/40) | 15 | 16 | 21041 | 15766 | 58256 |
| 2026-10-08 | session-3 ⁵ | official, paired (E1) | task A, dev sample 60 | swiss-ai/apertus-v1.5-8b | Public AI | A-v3-fulldoc, answer format by prompt (control) | 0.817 (E 0.811, N 0.810, C 0.829) | evidence score 0.350 (14/40) | 3 | 2 | 39077 | 10235 | 18711 |
| 2026-10-08 | session-3 ⁵ | official, paired (E1) | task A, dev sample 60 | swiss-ai/apertus-v1.5-8b | Public AI | A-v3-fulldoc + json_schema, max_tokens 128 | 0.850 (E 0.857, N 0.865, C 0.829) | evidence score 0.325 (13/40) | 0 | 1 | 39834 | 6972 | 17960 |
| 2026-10-08 | session-3 ⁵ | official, paired (E2) | **task A, all 300 dev cases** | swiss-ai/apertus-v1.5-8b | Public AI | A-v3-fulldoc + json_schema, **full booklet** | **0.669** (E 0.700, N 0.723, C 0.583) | evidence score 0.284 (57/201) | 0 | 7 | 39206 | 12717 | 37079 |
| 2026-10-08 | session-3 ⁵ | official, paired (E2) | **task A, all 300 dev cases** | swiss-ai/apertus-v1.5-8b | Public AI | A-v3-fulldoc + json_schema, **vote section** | **0.732** (E 0.845, N 0.674, C 0.676) | evidence score 0.224 (45/201) | 0 | 6 | 15868 | 8248 | 13513 |

¹ Runs A and C ran from the `session-2` working tree before its first commit: the code equals the first session-2 commit except that `llm.py` had no retry yet and the task A path was still the placeholder (B-only input never reaches it). Per-label F1 is shown as E/N/C.

⁵ Session 3 paired runs (`scripts/paired_run.py`): both configurations on the same case back to back, alternating order, warm booklet cache, run on the host with the entrypoint's code (`cli.predict`). Rows of one comparison are only comparable with each other.

⁴ JSON mode = `--json-mode-a` (`response_format: json_object`), the only change against the 60-case row; code committed with session 2's last commit. Mean input tokens count the 16 failed calls as 0. The rerun after the two-minute wait was stopped at 7 failed calls in 24 cases (over 10 % certain) and has no score (`s2-A60-A-v3-fulldoc-jsonmode_attempt2_stopped/run.log`).

³ The max_tokens run used commit `60e9eb1` with `--max-tokens-a 256`. "Re-parsed" rows apply the current parser (which also reads an explicit prose label statement) to the saved raw answers of the run above them, with `scripts/reparse_run.py`: no new model calls, tokens and time copied, scored with the official scorer.

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

### 2026-10-08, session 2: task A max_tokens 256 (60-case sample) and offline re-parses

- **max_tokens 256** (`s2-A60-A-v3-fulldoc-max256`, 07:38 to 07:50 UTC, the only change against the 60-case row): 0.398, 34 of 60 unparseable, mostly complete prose answers without JSON. **Not attributable to max_tokens**: at 07:50 the same two cases that gave clean JSON at 06:39 were repeated with the original settings; one now answered in prose and the other cited different pages. The endpoint's output drifted during the session (unparseable rate 10 % at 06:39, 43 % from 06:49 to 07:37, 57 % from 07:38 to 07:50). Default kept at 64.
- **Prose-label parser, re-parsed offline:** full 300 0.589 → **0.608** (13 previously unparseable answers now read, 5 responses changed); max256 sample 0.398 → 0.553 (20 now read); the first 60-case run is unchanged at 0.767 (it had no prose answers with a stated label), a sanity check. Most 64-token prose answers were cut before stating a label, so parsing alone recovers little there.

### 2026-10-08, session 2: task A JSON mode (60-case sample)

- `--json-mode-a` asks the endpoint for a JSON object (`response_format: json_object`); the only change against the 60-case row. Attempt 1 (07:53 to 08:09 UTC): 0.378, with 16 of 60 calls failing even after the retry (15 × HTTP 503, 1 × 504), so the run is invalid by the 10 % rule. The rerun after the two-minute wait (08:12 to 08:24) failed 7 of its first 24 calls and was stopped, as the session rule says.
- What JSON mode did do: no prose answers, but 15 answers used an invented schema such as `{"display_answers": {"answers": ["0"]}}` with no `label` key. JSON mode guarantees JSON, not our JSON. Not adopted; the default stays off.

### 2026-10-08, session 3, E1: answer format by prompt vs json_schema (task A, 60-case sample, paired)

- Command: `python3 scripts/paired_run.py --cases output/devA60/cases.jsonl --data-dir output/data_dev --out-dir docs/runs/s3-E1-A60 --arm '{"name": "fulldoc-prompt"}' --arm '{"name": "fulldoc-schema", "schema_a": true, "max_tokens_a": 128}'` (the control used the then-default settings: prompt format, 64 tokens), 11:47 to 12:04 UTC. Scored per arm with the official scorer.
- Unparseable answers: prompt 3, schema 0. Failed calls (HTTP 504 through the retry): prompt 2, schema 1. Order balanced (30 first each).
- On the 58 cases where both arms got an answer: prompt 0.846, schema 0.863.
- Schema mean time 7.0 s against 10.2 s; input tokens equal (same prompt).
- The control produced far fewer prose answers than in session 2 (3/60 against 43 %): endpoint drift, which is why comparisons are now paired.
- **Kept:** json_schema with max_tokens 128 is now the task A default (`Settings.schema_a=True`, `max_tokens_a=128`).

### 2026-10-08, session 3, E2: full booklet vs vote section (task A, all 300 dev cases, paired) — the central experiment

- Both arms: prompt `A-v3-fulldoc`, json_schema answers, 128 tokens. The only difference is which pages are sent: all of them, or `context.vote_section` (title match, running-header match, facing page, gap filling up to 10 pages; see `src/context.py`).
- Command: `python3 scripts/paired_run.py --cases output/devA/cases.jsonl --data-dir output/data_dev --out-dir docs/runs/s3-E2-A300 --arm '{"name": "fulldoc-schema", "schema_a": true, "max_tokens_a": 128, "context_a": "full"}' --arm '{"name": "section-schema", "schema_a": true, "max_tokens_a": 128, "context_a": "vote-section"}'`, 12:06 to 14:17 UTC. It was paused from 12:37 to 13:03 during a Public AI outage (HTTP 504 even for one-line calls) and resumed with `--resume`; nothing was re-run.
- Failed calls: full 7, section 6 (both arms hit at the same moments). 0 unparseable answers in both. Order balanced (150 first each).
- **On the 292 cases where both arms got an answer: full 0.674, section 0.741.** Same label in 200; where they differ (92), section right 49, full right 30.
- **Input tokens: section 15,868 per case against 39,206 (−60 %); total 4.76M against 11.76M.** Per case, section/full: mean 49 %, median 40 %. Pages sent: 55 % of the booklet on average.
- **Time: mean 8.2 s against 12.7 s; p95 13.5 s against 37.1 s.**
- Confusion (rows gold E/N/C): full E 76/9/17, N 10/69/20, C 29/14/56; section E 82/8/12, N 2/63/34, C 8/17/74. The section arm is much better on entailment and contradiction but calls more neutral claims contradiction (34 against 20).
- Same-language / cross-lingual: full 0.725 / 0.640, section 0.737 / 0.727. By booklet language: full de 0.681, fr 0.624, it 0.699; section de 0.723, fr 0.702, it 0.768. Cross-lingual cases gain the most.
- **Evidence is worse with the section (0.224 against 0.284).** With the shorter context the model's first cited page is more often on the front summary pages (65 of 145 cases against 50 of 147). These pages cannot simply be removed: for 47 of the 169 gold cases with a gold page, the gold page is *only* on the front summary (removing the first 15 % of pages would drop recall from 0.988 to 0.710).
- **Kept:** `vote-section` is now the task A default. It wins on Macro-F1 (the primary metric), tokens and time, at the cost of evidence score.
- The full-booklet arm (0.669) is far above session 2's reference row (0.589): json_schema removed the unparseable answers, and the endpoint's behaviour has changed since then.
