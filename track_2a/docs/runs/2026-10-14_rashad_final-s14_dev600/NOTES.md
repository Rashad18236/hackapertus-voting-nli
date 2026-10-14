### Final defaults through the published image, dev (session 14 FINISH: the lane change alone)

**Image** `ghcr.io/rashad18236/hackapertus-voting-nli:sha-228822b2e6fa` (built by the publish workflow from `228822b`,
also tagged `session-14`; pulled from ghcr.io, run with `make run`, the container pinned to CPUs 0–1; task A and task B
in separate containers; the real endpoint, Public AI's `swiss-ai/apertus-v1.5-8b`, one request per second, 11:01 to
11:14 UTC). Cases: 300 task A and 300 task B cases. Every answer and the one translation call from one backend
(blablador `vllm-0.23.1rc1`); 0 failed calls; 0 gateway cache hits; 0 unreadable answers, so Python wrote 0 labels.
`scripts/check_format.py`: no errors (300 + 300 responses).

The only default changed since session 13's final image: task A keeps two worker lanes down to 512 MiB when no case can
load e5 (step 2). It changes when a case is prepared, never its request (G1/G2 identical), so dev600 is the only final
run, as the instruction allows; val and probe keep session 13's final runs (`2026-10-14_rashad_final-s13_val1160`,
`..._probe188`). Session 13's final image in the last column (another run; not a comparison):

| | Macro-F1 | Evidence | Input + output tokens per case | Session 13's final image |
|---|---|---|---|---|
| Task A | **0.970** | **0.980** (197 of 201) | 1,251 + 14.7 | 0.973 / 0.985 |
| Task B | **0.987** | — | 815 + 8.9 | 0.987 |

One task A label differs from session 13's final dev run: row 1161 (gold contradiction) is answered neutral now,
contradiction then, from the identical request (the endpoint, not the code). Task A paths: council 102, summary 67,
committee 48, detail 43, law 39, fallback (bm25-ap) 1, with 1 translation call; no case needed AP-part or AP-structure
(`apertus_roles.json`).

Local time and REF SCORE: measured through the same image (`scripts/local_time.py`, 2 CPUs pinned to CPUs 2–3, the fake
model replaying the new reference's answers after the given delay, 11:31 to 12:15 UTC, 0 replay misses; `local_time_*.json`;
REF SCORE with its parts in `ref_score.json`). At 1.0 and 0.3 s two measurements each (the second after 11:52, see the
decisions file) and their mean:

| Model latency per request | Task A local time per case (s) | Task B | S_A | S_B | REF SCORE |
|---|---|---|---|---|---|
| 1.0 s | 0.0205 (0.0182, 0.0227) | 0.0124 (0.0130, 0.0118) | 0.9020 | 0.8968 | **0.8999** |
| 0.3 s | 0.0217 (0.0221, 0.0212) | 0.0134 (0.0150, 0.0117) | 0.9020 | 0.8922 | **0.8981** |
| 0.1 s | 0.0601 | 0.1614 | 0.8768 | 0.8409 | **0.8624** |

Task A under a 1 GB limit (where the lane change acts; two lanes, "Worker processes: 2"): 0.0189 / 0.0239 / 0.0633 s per
case at 1.0 / 0.3 / 0.1 s (session 13's code there: one lane, 0.21 s at 0.1 s, `2026-10-14_rashad_lanes-S_devA300`).
Peak memory at 4 GB: task A 205–366 MiB, task B 1,164–1,674 MiB (it varies from run to run).

**Why REF SCORE is lower than session 13's (0.9149 / 0.9107):** task B's local time, whose code has not changed since
session 11, measured 0.012–0.015 s per case here against 0.008–0.009 s in session 13's measurement; session 13's own image,
measured for task B in the same window as a control, gave 0.0157 / 0.0425 s (`local_time_s13img_devB_*.json`). The
machine was slower in this window, which lowers T_B (0.625 → 0.403 at 1.0 s). The rest is task A's one changed label
(Macro-F1 0.9733 → 0.9698, evidence 0.9851 → 0.9801). The lane change does not act at 4 GB.
