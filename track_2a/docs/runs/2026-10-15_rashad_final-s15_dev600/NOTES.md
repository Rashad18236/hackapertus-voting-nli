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

**Local time and REF SCORE** (`scripts/local_time.py` through the same image, 2 CPUs pinned to CPUs 2–3, 4 GB, the fake
model replaying the new reference's answers, 0 replay misses; 18:08 to 19:07 UTC, no model run at the same time; the
`local_time_*.json` files here, `ref_score.json`):

| Delay per request | Task A local time per case (measurements) | Task B (measurements) | Peak memory A / B (MiB) | REF SCORE |
|---|---|---|---|---|
| 1.0 s | 0.0198 s (0.0199, 0.0196) | 0.0119 s (0.0105, 0.0133) | 206 / 1,674 | **0.904** |
| 0.3 s | 0.0267 s (0.0228, 0.0305) | 0.0212 s (0.0195, 0.0228) | 363 / 1,650 | **0.893** |
| 0.1 s | 0.0616 s | 0.172 s | 206 / 1,164 | 0.864 |

REF SCORE parts at 1.0 / 0.3 s: task A T 1.000 / 1.000, K 0.471, S_A 0.907; task B T 0.420 / 0.236, K 0.971, S_B 0.899 /
0.872. Session 14's final image: 0.900 / 0.898; the difference is task A's Macro-F1 and evidence (A6, +0.007 and
+0.010) and task B's local time at 0.3 s (0.013 s then, 0.021 s now; task B's code is unchanged since session 11, so
this is the machine's window).
