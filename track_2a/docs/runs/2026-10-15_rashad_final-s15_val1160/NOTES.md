### Final defaults of session 15 on val (1,160 cases) through the published image

**What ran.** The final image `ghcr.io/rashad18236/hackapertus-voting-nli:sha-7ae78ad87cfd` (the `session-15` tag at the
time; id in `task-A/image.txt`): session 14's defaults plus A6 on. `make run` with the organisers' command, task A (all 580
val cases, booklets `output/booklets_dev`) and task B (all 580 val cases) in separate containers pinned to CPUs 0–1, the
real endpoint, `LLM_MIN_INTERVAL=1`, 15:40:10 to 16:07:17 UTC (task A to 15:55:49), between stability runs 1 and 2. The
folder is named `2026-10-15_…` as the session 15 instruction names the final runs; it ran on 14 October (`run.json`).

| Task | Macro-F1 | F1 ent / neu / con | Evidence | Unreadable (Python's neutral) | Calls | Mean input + output tokens |
|---|---|---|---|---|---|---|
| A (580) | **0.9812** | 0.984 / 0.983 / 0.976 | **0.988** (396 of 401) | 0 | 592 (580 + 10 A6 second looks + 2 translations) | 1,233 + 14.9 |
| B (580) | **0.9675** | 0.982 / 0.963 / 0.958 | — | 1 | 580 | 820 + 9.3 |

Session 13's final image on the same cases (A6 off): task A 0.969 (evidence 0.965), task B 0.968. A6's 10 second looks
answered "different" 9 times (rows 950, 1053, 1151, 1210, 1226, 1309, 1318, 1404, 1467) and "nothing" once (row 991),
as in sessions 14 and 15's interleaved runs. Paths (task A): council 175, summary 139, committee 102, law 87, detail 74,
fallback bm25-ap 3. Every call from one backend (blablador `vllm-0.23.1rc1`); 0 failed calls, 0 cache hits.

**Local time and REF SCORE** (as for dev600: the same image, CPUs 2–3, 4 GB, the new reference's table, which holds val
task A's answers; task B's 580 val requests are replay misses answered by the fake model's fixed answer, as in session
13; one measurement per delay; `local_time_*.json`, `ref_score.json`): task A 0.0095 / 0.0099 s, task B 0.0092 / 0.0095 s
per case at 1.0 / 0.3 s per request; **REF SCORE 0.908 / 0.907** (S_A 0.910, S_B 0.904 / 0.901; session 13's final
image: 0.917 / 0.912, mostly task B's local time, 0.006 / 0.007 s then).
