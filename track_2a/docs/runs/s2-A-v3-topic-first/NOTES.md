### 2026-10-08, session 2, Run A: v3-topic-first (task B)

- Only change against `v2-label-only`: the decision rule (first check whether the reference deals with the claim's subject at all; contradiction only for an incompatible statement; missing information is never a contradiction). See `docs/neutral_analysis.md`.
- Command: `make run CASES=output/devB/cases.jsonl OUTPUT_DIR=docs/runs/s2-A-v3-topic-first EXTRA_ARGS="--prompt-b v3-topic-first --raw /output/raw_answers.jsonl"` (+ sandbox proxy flags); `output/devB/` holds the 300 task B dev cases and their expected labels, filtered by id. 06:10 to 06:24 UTC.
- First attempt stopped after 5 of 5 calls failed (HTTP 504, endpoint outage, log in `s2-A-v3-topic-first_attempt1/`); rerun once after a two-minute wait, as the session rule says.
- Rerun: 5 of 300 calls failed (1.7 %, the first five cases, all gold entailment, label 1 by fallback) and 2 answers were unparseable (one was a bare `1` without JSON). Mean time includes the failed calls (about 61 s each); without them it is 1753 ms and mean input tokens 2001.
- Confusion (rows gold E/N/C): E 95/6/1, N 0/92/7, C 2/0/97. Same-language 0.960, cross-lingual 0.940; language pairs 0.882 (de->de) to 1.000 (it->it).
- On the 295 cases that Runs A and C both answered: v3 0.963, v4 0.933.
- Runs A and C ran from the `session-2` working tree before its first commit: the code equals the first session-2 commit except that `llm.py` had no retry yet and the task A path was still the placeholder (B-only input never reaches it). Per-label F1 is shown as E/N/C.
