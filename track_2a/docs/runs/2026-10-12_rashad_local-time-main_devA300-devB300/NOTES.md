### Local time of `main`, the organisers' way, and its REF SCORE (session 10, step 1)

**What was measured.** `main`'s image (`42b2a3c`, built at `50cb320` with the same `src/`) ran with the
organisers' command (`--input /data/cases.jsonl --output /output/predictions.jsonl`) on all 300 dev task A
cases and, in a separate container, all 300 dev task B cases, with 2 CPUs and 4 GB, a read-only root, /tmp in
memory and the data read-only (`scripts/local_time.py`). The fake model (`scripts/stub_llm.py`) answered every
request with session 9's saved real answer for exactly that request (replay; 0 misses in all four runs) after a
fixed delay of 1.0 s, then 0.3 s, standing in for the model's latency. Local time = wall-clock of `docker run`
minus the union of the intervals during which a request was in flight (the organisers' rule,
`docs/official_scoring.md`). Page cache warm (one short warm-up run first).

| | task A, 1.0 s | task A, 0.3 s | task B, 1.0 s | task B, 0.3 s |
|---|---|---|---|---|
| wall-clock | 541.3 s | 312.8 s | 595.7 s | 372.0 s |
| in flight | 300.3 s | 90.3 s | 300.3 s | 90.3 s |
| **local time** | 241.0 s | 222.5 s | 295.5 s | 281.7 s |
| **local time per case** | **0.803 s** | **0.742 s** | **0.985 s** | **0.939 s** |
| to the first request | 3.43 s | 3.44 s | 1.11 s | 1.20 s |
| gaps between requests | 236.6 s | 218.1 s | 293.8 s | 279.9 s |
| gap median / p95 / max | 0.044 / 3.41 / 22.9 s | 0.044 / 3.15 / 21.9 s | 0.004 / 4.70 / 8.9 s | 0.004 / 4.55 / 9.0 s |
| after the last answer | 0.95 s | 1.02 s | 0.59 s | 0.64 s |

The two delays give the same local time within about 8 % (241.0 against 222.5 s for task A): that is the
measurement's noise on this machine, not an effect of the delay (the local work does not depend on it).

**Where task A's local time goes.** The first case of each of the 44 booklets waits for the PDF to be read
(pypdf; 108 s in all, median 2.0 s per booklet); a few cases embed a long part or, on the fallback path, a
whole booklet with e5 (the largest gaps, 11 to 23 s); every other case costs about 0.04 s. A profile of the
preparation on the host (`cProfile`, all 300 cases): PDF text extraction 80 %, e5 10 % (model load 3.4 s once),
`booklet.parse` 3 % (it ran on every case).

**Where task B's local time goes.** Almost all of it is B-cut (session 9): the 105 references over 8,000
characters are cut to the 8 paragraphs most similar to the claim, which embeds every paragraph with e5 (median
gap 0.004 s for the others, p95 4.7 s). The first case of the run also loads the e5 model.

**Cold start.** The very first run after the Docker daemon started read the 470 MB e5 model file from this
sandbox's slow disk: one task B case then took 54 s instead of about 10 s. The measurements above are warm.

**REF SCORE of `main`** (`scripts/official_score.py`, fixed reference values: 600 / 800 tokens and 0.05 /
0.005 s per case for A / B; tokens = input + output per case; Macro-F1, evidence and tokens from session 9's
runs on all 600 dev cases (`2026-10-09_rashad_final-defaults_dev600`) and on val (`label-errors-confirm_valA580`
L1, `taskb-cut-confirm_valB580` B-cut); local time from the dev runs above, for both sets):

| | Macro-F1 A | evidence | tokens A | K_A | T_A | S_A | Macro-F1 B | tokens B | K_B | T_B | S_B | **REF SCORE** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dev, delay 1.0 s | 0.980 | 0.980 | 1,252 | 0.479 | 0.062 | 0.767 | 0.967 | 1,240 | 0.645 | 0.005 | 0.774 | **0.770** |
| dev, delay 0.3 s | 0.980 | 0.980 | 1,252 | 0.479 | 0.067 | 0.768 | 0.967 | 1,240 | 0.645 | 0.005 | 0.774 | **0.770** |
| val, delay 1.0 s | 0.961 | 0.958 | 1,220 | 0.492 | 0.062 | 0.755 | 0.961 | 1,239 | 0.646 | 0.005 | 0.770 | **0.761** |
| val, delay 0.3 s | 0.961 | 0.958 | 1,220 | 0.492 | 0.067 | 0.756 | 0.961 | 1,239 | 0.646 | 0.005 | 0.770 | **0.762** |

Tokens per case, input + output: task A dev 1,237.8 + 14.5, val 1,205.8 + 14.5; task B dev 1,231.2 + 8.4,
val 1,230.3 + 8.9. **T is almost zero for both tasks**: 15 % of each task's score is local time, and `main`
spends 0.74 to 0.99 s per case where the reference best is 0.05 s (A) and 0.005 s (B).

Files: `local_time_<task>_d<delay>.json` (each run's numbers, from `scripts/local_time.py`), `ref_score.json`.
