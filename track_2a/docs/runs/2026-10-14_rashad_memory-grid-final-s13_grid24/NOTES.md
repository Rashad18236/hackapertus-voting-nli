### Memory grid of the final session 13 image (model S for task A): every response at every limit, task A peaks at 206 MiB

**Set-up** (as session 12's grid, `docs/runs/2026-10-13_rashad_memory-guard_grid48`): the final image
`ghcr.io/rashad18236/hackapertus-voting-nli:sha-54032b4a7970` (defaults: model S ranks task A's long parts, H, e5 for
task B's selector T), `scripts/local_time.py` against the fake model replaying session 12's reference answers after
0.1 s per request, CPUs 2–3, all 300 dev cases of each task, memory limits 4g … 512m with 2 CPUs and with 1, every limit
run. 00:27 to 00:57 UTC, beside the final model runs (the local time column is indicative only). `local_time/` holds
each run's `local_time.json`.

| Task | CPUs | Memory limit | Exit | Responses | Guard | Peak memory (MiB) | Local time per case (s) |
|---|---|---|---|---|---|---|---|
| A | 2 | 4g | 0 | 300 of 300 | no | 206 | 0.0161 |
| A | 2 | 2g | 0 | 300 of 300 | no | 130 | 0.1262 |
| A | 2 | 1.5g | 0 | 300 of 300 | no | 130 | 0.1240 |
| A | 2 | 1g | 0 | 300 of 300 | yes | 129 | 0.1244 |
| A | 2 | 768m | 0 | 300 of 300 | yes | 129 | 0.1255 |
| A | 2 | 512m | 0 | 300 of 300 | yes | 129 | 0.1304 |
| A | 1 | 4g | 0 | 300 of 300 | no | 129 | 0.1279 |
| A | 1 | 2g | 0 | 300 of 300 | no | 128 | 0.1304 |
| A | 1 | 1.5g | 0 | 300 of 300 | no | 128 | 0.1407 |
| A | 1 | 1g | 0 | 300 of 300 | yes | 128 | 0.1338 |
| A | 1 | 768m | 0 | 300 of 300 | yes | 129 | 0.1377 |
| A | 1 | 512m | 0 | 300 of 300 | yes | 129 | 0.1293 |
| B | 2 | 4g | 0 | 300 of 300 | no | 1164 | 0.1191 |
| B | 2 | 2g | 0 | 300 of 300 | no | 1164 | 0.1109 |
| B | 2 | 1.5g | 0 | 300 of 300 | no | 1164 | 0.1139 |
| B | 2 | 1g | 0 | 300 of 300 | yes | 51 | 0.0062 |
| B | 2 | 768m | 0 | 300 of 300 | yes | 52 | 0.0060 |
| B | 2 | 512m | 0 | 300 of 300 | yes | 51 | 0.0063 |
| B | 1 | 4g | 0 | 300 of 300 | no | 1164 | 0.2706 |
| B | 1 | 2g | 0 | 300 of 300 | no | 1164 | 0.2594 |
| B | 1 | 1.5g | 0 | 300 of 300 | no | 1164 | 0.2647 |
| B | 1 | 1g | 0 | 300 of 300 | yes | 52 | 0.0059 |
| B | 1 | 768m | 0 | 300 of 300 | yes | 51 | 0.0060 |
| B | 1 | 512m | 0 | 300 of 300 | yes | 51 | 0.0062 |

**Before → after** (session 12's final image `sha-828429cab766` → this one): task A peak memory 2,287 → **206 MiB**
at 4g with 2 CPUs (model S instead of e5; with one worker process 1,195 → 130 MiB); task B unchanged (1,164 MiB, e5
for selector T; 51 MiB below 1.5 GiB, where the guard sends long references whole). Image size 2,216.2 → 2,216.3 MB
(e5 stays for task B). Labels "differing from 4g" in the log at task B ≤ 1g are replay misses (the whole reference is
a new request), not new answers.

**For the team:** below 2.5 GiB the pipeline still runs task A with one worker process
(`pipeline.MEMORY_FOR_TWO_LANES`, set in session 11 for e5's 1.2 GiB per lane); with model S a lane needs about
130 MiB, and the second lane is what keeps local time low at a fast model (0.016 against 0.126 s per case at 0.1 s
per request). Not changed in this session (no rule was set for it).
