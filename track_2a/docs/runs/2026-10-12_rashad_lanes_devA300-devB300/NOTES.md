### Two worker processes owning whole booklets ("lanes") against one (session 10, after step 2)

**What changed (same requests and answers).** Since step 2 one forked worker process prepared all cases. With two,
each would read most booklets again (each process has its own caches), so each lane now owns whole booklets:
task A cases go to lane `booklet rank % 2` (booklets in order of first appearance), task B cases to lane 0. The
lanes are forked with their list of cases before the main process starts any thread, and send each prepared case
back through a pipe (`src/pipeline.py` Lanes). G1 and G2 against the step 2 snapshot: pass (all 1,180 dev and val
requests, labels and evidence unchanged; the replay of dev and val took 288 s instead of 477 s). Unit, contract and
pipeline tests pass.

**Local time per case** (`scripts/local_time.py`, image `s10-lanes`, 2 CPUs, 4 GB; one lane = the same image with
`--workers 1`; the 1.0 s pairs were measured back to back while a light model run went on):

| | two lanes | one lane |
|---|---|---|
| task A, 0.3 s per request | **0.206 s** (local 61.8 s; first request 3.4 s) | 0.316 s (94.8 s) |
| task A, 1.0 s per request | 0.018 s (twice: 5.4 s and 5.4 s) | 0.015 / 0.016 s (4.6 s, 4.8 s) |
| task A, peak memory | 2.3 GB | 1.2 GB |
| task B, 1.0 s / 0.3 s | 0.007 / 0.008 s (one lane either way: no booklets) | |
| K4 (task A), 1.0 s / 0.3 s | 0.080 / 0.772 s | 0.215 / 0.837 s (step 5) |

At 1.0 s per request two lanes cost about 0.8 s more per 300 cases: small gaps between requests (p95 18 ms
against 8 ms) while both lanes are busy on the two CPUs. Running the lanes at a lower CPU priority (`os.nice`) did
not change it (0.0179 against 0.0146 s, measured back to back) and was taken out again. At 0.3 s per request two
lanes read two PDFs at the same time and cut task A's local time by a third.

**Decision: two lanes by default (one on a single CPU).** Under REF SCORE task A's local time at 1.0 s is below the
reference best (0.05 s) either way, so T_A is 1.0 with one lane or two; at 0.3 s T_A rises from 0.16 to 0.24. Task
B is unchanged. Peak memory stays under 4 GB with room to spare.
