### 2026-10-08, session 2: task A full-document baseline, 60-case sample (A-v3-fulldoc)

- Whole booklet in one call (pypdf text, `=== PAGE n ===` before each page), then VOTE and CLAIM; the answer is `{"pages": [...], "label": n}`; evidence = the cited pages' text (split at 5,000 characters, at most five items). Prompts A-v1 and A-v2 (pages after the label) never named pages and were not scored; see `decisions.md`.
- Sample: 20 task A dev cases per label, round-robin over the 9 language pairs, seed 42 (`output/devA60/`, filtered by id from `data/dev/`). Booklets: the 44 dev booklets from the starter's `prepare_cases.py --download-booklets`, mounted read-only at `/data/booklets`.
- Command: `make run CASES=output/devA60/cases.jsonl BOOKLETS=output/booklets_dev OUTPUT_DIR=docs/runs/s2-A60-A-v3-fulldoc EXTRA_ARGS="--raw /output/raw_answers.jsonl"` (+ sandbox proxy flags), 06:39 to 06:49 UTC. 0 failed calls; 6 unparseable answers (label-1 fallback); format check: no errors.
- Confusion (rows gold E/N/C): E 17/2/1, N 0/16/4, C 2/5/13.
- Input tokens per case: mean 41,124 (the whole booklet). Time: mean 9.6 s, p95 23.3 s.
- Task A runs used code identical to commit `4e90ddc` (prompt `A-v3-fulldoc`, retry active).
