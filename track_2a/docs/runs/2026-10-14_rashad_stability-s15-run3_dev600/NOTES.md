### Stability run 3 of 3 (session 15, step 5), and the three runs compared: no label changed

**What ran.** As runs 1 and 2: the final image `ghcr.io/rashad18236/hackapertus-voting-nli:sha-7ae78ad87cfd`, `make run`,
task A and task B in separate containers pinned to CPUs 0–1, the real endpoint, `LLM_MIN_INTERVAL=1`, 16:57:59 to
17:11:01 UTC (task A to 17:05:22), 30 minutes after run 2 ended (the final probe188 run, other requests, in between).
Exit code 0, 600 responses; 0 unreadable, 0 failed calls, 0 cache hits; 306 task A calls (300 + 5 A6 second looks + 1
translation), 300 task B calls.

**The three runs** (`stability.json`, `scripts/stability.py`; bootstrap: `scripts/analysis_offline.py`'s method, 2,000
resamples of the 300 cases, seed 42):

| Run (start, UTC) | Task A Macro-F1 [95 % interval] | Evidence | Task B Macro-F1 [95 % interval] | Backend (calls) | Cache hits |
|---|---|---|---|---|---|
| 1 (15:23) | 0.9767 [0.958, 0.991] | 0.990 | 0.9867 [0.973, 0.997] | blablador `vllm-0.23.1rc1…dd237840` (606) | 0 |
| 2 (16:10) | 0.9767 [0.958, 0.991] | 0.990 | 0.9867 [0.973, 0.997] | the same (606) | 0 |
| 3 (16:58) | 0.9767 [0.958, 0.991] | 0.990 | 0.9867 [0.973, 0.997] | the same (606) | 0 |

**Labels that ever changed: 0 of 600** (task A 0 of 300, task B 0 of 300); the largest Macro-F1 difference between two
runs is 0. The answers are not byte-identical, though: 10 task A answers cite different paragraphs in one of the runs
(same label; the evidence text differs in 9 cases, the evidence score is 0.990 in all three), and 20 task B answers
differ only in trailing whitespace or a "**Reasoning:**" text after the JSON (same label; task B has no schema). The same
labels also came from the "today" arms of the session's interleaved runs earlier in the afternoon (task A 13:30, task B
14:11 and 14:38): 0 of 300 differ in each. Against session 14's final dev run (11:01, A6 off) only task A rows 1016 and 1161
differ, both A6's fixes; task B 0 of 300.

**Reading:** over about 3.7 hours on one backend, the endpoint gave the same labels to the same requests; the run-to-run
noise of the final defaults is below one case per task on dev. The 95 % intervals (0.032 wide for task A, 0.024 for task B)
describe the sampling of the 300 cases, not the endpoint; they are the error margin for comparing our dev numbers with
other cases (val, the official test set). Session 9's three points (16.5 hours, one backend) changed 2 of 600 labels.
