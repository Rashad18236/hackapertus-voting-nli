### Stability point 2 of 3 (session 9, A4): all 600 dev cases through the Docker image, about 8.5 hours after point 1

**What ran.** Exactly stability point 1's settings: `make run IMAGE=hackapertus-voting-nli:stability` (the
image of point 1, built at `7edbae4`, id `sha256:af004f5d…` in `image.txt`, before session 9's default
changes), the real endpoint (Public AI, `swiss-ai/apertus-v1.5-8b` from `.env`), `LLM_MIN_INTERVAL=1`, input
`data/dev/cases.jsonl`. Started 01:56:21 UTC, ended 02:17:58 UTC; exit code 0, 600 responses. The sandbox had
restarted since point 1, so the Docker daemon was started again first; the image was still there, unchanged.

| Task | Macro-F1 | Evidence | Unreadable | Failed calls | Cache hits | Mean input tokens | Mean / p95 time |
|---|---|---|---|---|---|---|---|
| A (300) | 0.966 | 0.935 (188/201) | 0 | 0 | 0 | 1,210 | 2.5 / 4.8 s |
| B (300) | 0.967 | not scored | 4 | 0 | 0 | 1,994 | 1.8 / 3.1 s |

**Backends.** All 600 answers came from the same backend as point 1 (`...dd237840`, blablador).

**Against point 1** (`stability.json`, `scripts/stability_report.py`): task A labels agree in 299 of 300 cases,
task B labels in 300 of 300; Macro-F1 is the same to four decimals in both tasks (A 0.9662, B 0.9666); the
evidence score moved by one case (187 → 188). No gateway cache hit (the same requests were last sent more than
eight hours earlier), so these are fresh model answers.

Task B's `run.json` is in `task-B/`.
