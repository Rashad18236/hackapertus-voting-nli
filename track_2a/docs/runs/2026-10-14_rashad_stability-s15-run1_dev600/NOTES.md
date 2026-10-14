### Stability run 1 of 3 (session 15, step 5): all 600 dev cases through the final image

**What ran.** The final image `ghcr.io/rashad18236/hackapertus-voting-nli:sha-7ae78ad87cfd` (the `session-15` tag at the
time; id in `task-A/image.txt`), `make run` with the organisers' command, task A (300 cases, booklets
`output/booklets_dev`) and task B (300 cases) in separate containers pinned to CPUs 0–1, the real endpoint (Public AI,
`swiss-ai/apertus-v1.5-8b` from `.env`), `LLM_MIN_INTERVAL=1`, 15:23:16 to 15:40:10 UTC (task A to 15:34:10). The first run of step 5, 30 minutes after the B6 run's last dev requests (14:53). Exit code 0, 600 responses.

| Task | Macro-F1 | Evidence | Unreadable | Failed calls | Cache hits | Calls | Mean input + output tokens |
|---|---|---|---|---|---|---|---|
| A (300) | 0.9767 | 0.990 (199 of 201) | 0 | 0 | 0 | 306 (300 + 5 A6 second looks + 1 translation) | 1,259 + 14.9 |
| B (300) | 0.9867 | — | 0 | 0 | 0 | 300 | 815 + 8.4 |

**Backend:** every call from blablador (`vllm-0.23.1rc1…dd237840`). The comparison of the three runs (labels that ever
changed, bootstrap intervals) is in run 3's NOTES and `stability.json` there (`scripts/stability.py`).
