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
