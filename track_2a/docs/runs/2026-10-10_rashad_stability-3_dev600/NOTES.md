### Stability point 3 of 3 (session 9, A4): all 600 dev cases through the Docker image, about 16.5 hours after point 1

**What ran.** Exactly stability point 1's settings: `make run IMAGE=hackapertus-voting-nli:stability` (the
image of points 1 and 2, built at `7edbae4`, id `sha256:af004f5d…` in `image.txt`), the real endpoint (Public
AI, `swiss-ai/apertus-v1.5-8b` from `.env`), `LLM_MIN_INTERVAL=1`, input `data/dev/cases.jsonl`. Started
09:56:01 UTC, ended 10:16:21 UTC; exit code 0, 600 responses. The sandbox had restarted again since point 2;
the Docker daemon was started again, the image was unchanged.

| Task | Macro-F1 | Evidence | Unreadable | Failed calls | Cache hits | Mean input tokens | Mean / p95 time |
|---|---|---|---|---|---|---|---|
| A (300) | 0.966 | 0.930 (187/201) | 0 | 0 | 0 | 1,210 | 2.4 / 5.1 s |
| B (300) | 0.963 | not scored | 1 | 0 | 0 | 1,994 | 1.6 / 2.6 s |

**Backends.** All 600 answers came from the same backend as points 1 and 2 (`...dd237840`, blablador).

**The three points** (`stability.json`, `scripts/stability_report.py --points` with all three):

| Point (UTC) | Task A | Evidence | Task B | Unreadable (B) | Labels equal to point 1 (A; B) |
|---|---|---|---|---|---|
| 1, 2026-10-09 17:28 | 0.966 | 0.930 | 0.967 | 3 | – |
| 2, 2026-10-10 01:56 | 0.966 | 0.935 | 0.967 | 4 | 299/300; 300/300 |
| 3, 2026-10-10 09:56 | 0.966 | 0.930 | 0.963 | 1 | 300/300; 299/300 |

Across the three points, two of the 600 cases ever changed label: row 1138 (task A, gold contradiction:
neutral, entailment, neutral, wrong every time) and row 640 (task B, gold neutral: neutral, neutral,
contradiction, wrong only at point 3, which explains task B's 0.967 → 0.963). Over 16.5 hours the endpoint,
on this one backend, answered the same requests almost identically; no gateway cache was involved (each
point's requests were last sent eight hours before).

Task B's `run.json` is in `task-B/`.
