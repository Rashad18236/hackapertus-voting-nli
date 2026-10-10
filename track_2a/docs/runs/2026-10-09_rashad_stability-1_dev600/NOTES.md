### Stability point 1 of 3 (session 9, A4): all 600 dev cases through the Docker image

**What ran.** `make run` with the Docker image `hackapertus-voting-nli:stability` (built from commit `7edbae4`,
image id in `image.txt`), the real endpoint (Public AI, `swiss-ai/apertus-v1.5-8b` from `track_2a/.env`),
default settings of that commit, `LLM_MIN_INTERVAL=1` (at most one request per second). Input: `data/dev/cases.jsonl`
(300 task A and 300 task B cases in one file); output and raw answers in this folder. Started 17:28:05 UTC,
ended 17:48:38 UTC (`started_utc.txt`, `ended_utc.txt`); exit code 0, 600 responses.

The image predates A2 (evidence halves), so task A's evidence here has no halves. Stability points 2 and 3
(about 02:00 and 10:00 UTC) run the same image with the same settings, so the three points differ only in
time (and in what the endpoint does).

**Scores** (the starter's `evaluate.py`, `official_score.json`; per backend by `scripts/stability_report.py`,
`stability.json`):

| Task | Macro-F1 | Evidence | Unreadable | Failed calls | Cache hits | Mean input tokens | Mean / p95 time (ms) |
|---|---|---|---|---|---|---|---|
| A (300) | 0.966 | 0.930 (187/201) | 0 | 0 | 1 | 1,210 | 2,606 / 5,375 |
| B (300) | 0.967 | not scored | 3 | 0 | 1 | 1,994 | 1,494 / 2,611 |

**Backends.** Every one of the 600 answers came from one backend (system_fingerprint
`vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840`, routed to `api.blablador.fz-juelich.de`); the second
backend seen on 2026-10-09 (`fp1-nst-nes`, featherless.ai) answered none. So the per-backend table has one row,
equal to the totals above.

**For comparison only (different run, not a paired comparison).** In the four-arm task B run of 02:11 UTC
(`2026-10-09_rashad_taskb-4arm_devB300`), the same prompt and settings (arm A) scored 0.867 overall: 0.966 on
the 189 cases the blablador backend answered and 0.566 on the 111 the featherless backend answered. Today's
task B 0.967 matches the blablador figure. Which backend answers is the largest source of variation we have
seen; stability points 2 and 3 show whether it changes at night and in the morning.

Task B's `run.json` is in `task-B/` (one task per `run.json`); its `predictions.jsonl` and
`raw_answers.jsonl` there are the task B lines of this folder's files.
