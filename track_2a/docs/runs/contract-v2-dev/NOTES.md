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
- The second run also answered the 300 dev task A requests with the placeholder (label 1, no model call): official task A Macro-F1 0.165, the always-neutral value. It is not a task A result.
