### Final defaults of session 15 on the probe (188 cases) through the published image

**What ran.** The final image `ghcr.io/rashad18236/hackapertus-voting-nli:sha-7ae78ad87cfd` (session 14's defaults plus
A6 on), `make run`, task A (94 cases, booklets `output/booklets_probe`) and task B (94 cases) in separate containers
pinned to CPUs 0–1, the real endpoint, `LLM_MIN_INTERVAL=1`, 16:27:55 to 16:32:18 UTC, after stability run 2. The probe
is the test rows of 2021-03-07 and 2025-09-28 (opened in session 10); the sealed dates were not run. Folder named
`2026-10-15_…` as the instruction names the final runs; it ran on 14 October.

| Task | Macro-F1 | F1 ent / neu / con | Evidence | Unreadable | Calls | Mean input + output tokens |
|---|---|---|---|---|---|---|
| A (94) | **0.9903** | 1.000 / 0.982 / 0.989 | **1.000** (65 of 65) | 0 | 98 (94 + 1 A6 second look + 3 translations) | 1,177 + 16.6 |
| B (94) | **0.9769** | 0.977 / 0.966 / 0.989 | — | 0 | 94 | 789 + 8.3 |

Session 13's final image (A6 off): task A 0.981 (evidence 0.985), task B 0.977. Paths (task A): council 34, summary 20,
law 16, detail 10, committee 10, fallback bm25-ap 4. One backend; 0 failed calls, 0 cache hits.

**Local time and REF SCORE** (as for dev600; the probe's requests are not in the replay table, so all are answered by
the fake model's fixed answer, as in session 13; one measurement per delay; `local_time_*.json`, `ref_score.json`):
task A 0.0387 / 0.0351 s, task B 0.0198 / 0.0191 s per case at 1.0 / 0.3 s per request; **REF SCORE 0.901 / 0.902**
(session 13's final image: 0.903 / 0.901).
