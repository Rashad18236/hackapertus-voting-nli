### Final defaults of session 15 on dev (600 cases) through the published image

**What ran.** The final image `ghcr.io/rashad18236/hackapertus-voting-nli:sha-7ae78ad87cfd` (the `session-15` tag at the
time; id in `task-A/image.txt`): session 14's defaults (model S, hedge H, two lanes) plus A6 on. `make run` with the
organisers' command, task A (300 cases, booklets `output/booklets_dev`) and task B (300 cases) in separate containers
pinned to CPUs 0–1, the real endpoint, `LLM_MIN_INTERVAL=1`, 17:41:02 to 17:55:30 UTC (task A to 17:48:24), 30 minutes
after stability run 3. The folder is named `2026-10-15_…` as the session 15 instruction names the final runs; it ran on
14 October (`run.json`).

| Task | Macro-F1 | F1 ent / neu / con | Evidence | Unreadable (Python's neutral) | Calls | Mean input + output tokens |
|---|---|---|---|---|---|---|
| A (300) | **0.9767** | 0.971 / 0.995 / 0.964 | **0.990** (199 of 201) | 0 | 306 (300 + 5 A6 second looks + 1 translation) | 1,259 + 14.9 |
| B (300) | **0.9867** | 0.985 / 0.995 / 0.980 | — | 0 | 300 | 815 + 9.0 |

The same 600 labels as the three stability runs (`2026-10-14_rashad_stability-s15-run{1,2,3}_dev600`). A6's 5 second
looks: "different" in rows 1016 and 1161 (both fixes), "nothing" in rows 629, 844 and 1052 (the first answer stands);
454 + 8 tokens each. Against session 14's final image (A6 off): task A 0.970 → 0.977, evidence 0.980 → 0.990. Paths
(task A): council 102, summary 67, committee 48, detail 43, law 39, fallback bm25-ap 1. One backend (blablador
`vllm-0.23.1rc1`); 0 failed calls, 0 cache hits. `apertus_roles.json`: calls and tokens per Apertus role.
