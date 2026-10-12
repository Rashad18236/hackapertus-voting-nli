### Background preparation: local time before and after, B-cut against no cut (session 10, step 2)

**What changed (same requests and answers).** `src/cli.py`'s `predict()` was split into `prepare()` (the local
work of a case: booklet, routing, embedding, messages) and `complete()` (the model call and the response).
`src/pipeline.py` prepares the cases in the background while the main process sends the prepared ones, one
request at a time, in the order they become ready. Also: one kept connection per thread (`requests.Session`;
a connection error is sent once more on a new connection), each booklet parsed once (`booklet.parse` was run
on every case), pages kept in memory per booklet, pypdf imported on first use, ONNX threads = the
container's CPU limit (2 instead of 4: about 20 % faster under `--cpus 2`, vectors bit-identical), `src/`
compiled when the image is built. `--workers 0` keeps the sequential path.

**Gates.** G1 and G2 against the session 9 reference (`2026-10-09_rashad_prompt-snapshot-final_devAB-valA`):
pass for the thread version and for the process version (all 1,180 dev and val requests, paths, labels and
evidence equal). With task B's new default (no cut, below), the requests of exactly the 105 long dev task B
references differ, as expected; every other request, label and evidence is unchanged. Unit, contract and
pipeline tests pass (164 unit; 43 contract and pipeline, one slow test skipped).

**Local time per case** (same measurement as step 1: 2 CPUs, 4 GB, fake model replaying session 9's answers):

| | task A, 1.0 s | task A, 0.3 s | task B, 1.0 s | task B, 0.3 s |
|---|---|---|---|---|
| `main` (step 1) | 0.803 s | 0.742 s | 0.985 s | 0.939 s |
| two worker threads | 0.105 s | 0.373 s | 0.037 s | 0.664 s |
| **one worker process** | **0.015 s** | **0.300 s** | 0.008 s | 0.470 s |
| one worker process, task B without the cut | | | **0.008 s** | **0.009 s** |

One worker process, task A at 1.0 s: 4.5 s of local time in a 305 s run: 3.1 s to the first request (start-up
and the first booklet), 1.2 s of gaps (median 3.8 ms per request), 0.24 s after the last answer.

**Why a process.** With threads, the PDF reader (pure Python) and the creation of the ONNX session (it holds
Python's lock for up to 2.45 s, measured in the container) kept the thread that sends the requests waiting:
task B's second request left 7.6 s late, and two threads reading two booklets at once doubled the time to
task A's first request (3.4 to 6.3 s). In input order, the first 25 task A cases each needed a new booklet;
the cases are now prepared grouped by booklet (first appearance), task B's light cases first.

**When the model is fast, the preparation is the limit.** At 0.3 s per request the 300 requests are in flight
for 90 s, while the worker needs about 180 s for task A (reading 44 booklets, a few e5 embeddings) and about
225 s for task B with the cut (embedding every paragraph of the 105 long references). Without the cut, task B
has no local model work.

**B-cut against no cut under REF SCORE** (S_B = 0.70 Macro-F1 + 0.15 T + 0.15 K; Macro-F1 and tokens from
session 9's interleaved runs, `2026-10-09_rashad_taskb-context_devB300` and `taskb-cut-confirm_valB580`):

| | Macro-F1 | tokens per case | K | T at 1.0 s | S_B at 1.0 s | T at 0.3 s | S_B at 0.3 s | mean S_B |
|---|---|---|---|---|---|---|---|---|
| dev, B-cut | 0.967 | 1,239.6 | 0.645 | 0.625 | 0.868 | 0.011 | 0.775 | 0.821 |
| dev, no cut | 0.967 | 2,002.7 | 0.400 | 0.633 | 0.832 | 0.568 | 0.822 | **0.827** |
| val, B-cut | 0.961 | 1,239.2 | 0.646 | 0.625 | 0.863 | 0.011 | 0.771 | 0.817 |
| val, no cut | 0.957 | 1,966.1 | 0.407 | 0.633 | 0.826 | 0.568 | 0.816 | **0.821** |

The two delays disagree: B-cut wins when the model takes 1.0 s per request (its embedding hides behind the
requests), no cut wins at 0.3 s. B-cut is hidden only if a request takes at least about 0.75 s (225 s of
embedding over 300 requests); Public AI's server time per task B call was about 0.6 to 0.85 s in step 1's
connection check, right at that edge. **Decision: no cut**, by the mean S_B over both delays (dev +0.006, val
+0.004); it also does not depend on the model's speed, and task B no longer reads the 470 MB e5 file, which in
a freshly pulled image is read from disk on first use (54 s on this sandbox's disk in step 1).

**REF SCORE after step 2** (task A: one worker process; task B: no cut; local time measured on dev, used for
both sets):

| | S_A | T_A | S_B | T_B | K_B | **REF SCORE** | `main` |
|---|---|---|---|---|---|---|---|
| dev, 1.0 s per request | 0.908 | 1.000 | 0.832 | 0.633 | 0.400 | **0.877** | 0.770 |
| dev, 0.3 s | 0.783 | 0.167 | 0.822 | 0.568 | 0.400 | **0.799** | 0.770 |
| val, 1.0 s | 0.896 | 1.000 | 0.826 | 0.633 | 0.407 | **0.868** | 0.761 |
| val, 0.3 s | 0.771 | 0.167 | 0.816 | 0.568 | 0.407 | **0.789** | 0.762 |

Tokens are not changed by step 2 (G1: the same requests), except task B's long references, now sent whole.
The fake model reports fixed token counts, so the `input_tokens_per_case` in the `local_time_*.json` files
(100 and 10) are not real; the real counts are session 9's.

Files: `local_time_<version>_<task>_d<delay>.json`, `ref_score.json`.
