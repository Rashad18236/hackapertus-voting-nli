### FINISH: all 600 dev cases with the final defaults of session 9, through the Docker image

**What ran.** `make run IMAGE=hackapertus-voting-nli:final` (image built at `50cb320` by
the session's sandbox build, which differs from `make build` only by giving pip the sandbox's proxy
certificate as a build secret; id in `image.txt`), the real endpoint (Public AI, `swiss-ai/apertus-v1.5-8b` from `.env`),
`LLM_MIN_INTERVAL=1`, input `data/dev/cases.jsonl` (300 task A and 300 task B cases in one file). Started
21:22:41 UTC, ended 21:44:01 UTC; exit code 0, 600 responses, no failures. The image's defaults were checked
before the run: task B `--context-b cut`, task A `label_rule_a` (prompt `A-v4-section-route-L1`), evidence
halves on, L2 off, context `section-route`.

**Scores** (the starter's `evaluate.py`: `official_score.json`, `.txt`; per task and backend:
`breakdown_by_task.json` from `scripts/stability_report.py`):

| Task | Macro-F1 | F1 E / N / C | Evidence | Unreadable | Mean input / output tokens | Mean / p95 time |
|---|---|---|---|---|---|---|
| A (300) | **0.980** | 0.980 / 0.990 / 0.969 | **0.980** (197/201) | 0 | 1,238 / 14.5 | 2.2 / 4.5 s |
| B (300) | **0.967** | 0.985 / 0.963 / 0.951 | not scored | 0 | 1,231 / 8.4 | 2.0 / 3.8 s |

All 600 answers came from one backend (`...dd237840`, blablador); no gateway cache hits.

**Compared with what (same day, different runs, so only indicative):** stability point 1 at 17:28 UTC with the
defaults before session 9's changes scored task A 0.966 (evidence 0.930, no halves) with 1,210 input tokens
and task B 0.967 with 1,994. The changes were adopted on interleaved runs (phases C and D), not on this
comparison.

These answers, with the val L1 arm's (`2026-10-09_rashad_label-errors-confirm_valA580/L1`), are the saved
answers of the new replay reference `2026-10-09_rashad_prompt-snapshot-final_devAB-valA`.

Task B's `run.json` is in `task-B/` with the task B lines of this folder's files.
