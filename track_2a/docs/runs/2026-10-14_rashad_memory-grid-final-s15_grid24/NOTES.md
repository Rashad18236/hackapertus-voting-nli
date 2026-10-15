### Memory grid of the final session 15 image: every response at every limit, A6 on

**Set-up** (as `2026-10-14_rashad_memory-grid-final-s14_grid24`): the final image
`ghcr.io/rashad18236/hackapertus-voting-nli:sha-7ae78ad87cfd` (session 14's defaults plus A6 on), `scripts/local_time.py
--peak-memory` against the fake model replaying session 14's reference answers after 0.1 s per request, CPUs 2–3, all
300 dev cases of each task, memory limits 4g … 512m with 2 CPUs and with 1, every limit run, 15:01 to 15:33 UTC; from
15:23 beside stability run 1 on CPUs 0–1 (the local time column is indicative only). "Lanes" is the CLI's log line
("Worker processes"); "Guard": the memory guard marked e5 unusable (below 1.5 GiB). `local_time/` holds each run's
`local_time.json`, `grid.json` this table. Replay misses: task A 5 in every run, the A6 second looks of dev rows 629,
844, 1016, 1052 and 1161 (session 14's reference has no answers for them; the fake model's fixed answer is unreadable as a
finding, so A6 keeps the first answer, and the second request is still sent); task B 190 below 1.5 GiB (the memory
guard sends the 190 long references whole, requests the reference has no answer for; as in sessions 13 and 14).

| Task | CPUs | Memory limit | Exit | Responses | Lanes | Guard | Peak memory (MiB) | Local time per case (s) | Replay misses |
|---|---|---|---|---|---|---|---|---|---|
| A | 2 | 4g | 0 | 300 of 300 | 2 | no | 242 | 0.1055 | 5 |
| A | 2 | 2g | 0 | 300 of 300 | 2 | no | 206 | 0.0996 | 5 |
| A | 2 | 1.5g | 0 | 300 of 300 | 2 | no | 206 | 0.0861 | 5 |
| A | 2 | 1g | 0 | 300 of 300 | 2 | yes | 206 | 0.0856 | 5 |
| A | 2 | 768m | 0 | 300 of 300 | 2 | yes | 206 | 0.0799 | 5 |
| A | 2 | 512m | 0 | 300 of 300 | 2 | yes | 206 | 0.0825 | 5 |
| A | 1 | 4g | 0 | 300 of 300 | 1 | no | 128 | 0.2429 | 5 |
| A | 1 | 2g | 0 | 300 of 300 | 1 | no | 129 | 0.2369 | 5 |
| A | 1 | 1.5g | 0 | 300 of 300 | 1 | no | 129 | 0.2275 | 5 |
| A | 1 | 1g | 0 | 300 of 300 | 1 | yes | 128 | 0.2470 | 5 |
| A | 1 | 768m | 0 | 300 of 300 | 1 | yes | 128 | 0.2641 | 5 |
| A | 1 | 512m | 0 | 300 of 300 | 1 | yes | 131 | 0.2566 | 5 |
| B | 2 | 4g | 0 | 300 of 300 | 2 | no | 1165 | 0.2399 | 0 |
| B | 2 | 2g | 0 | 300 of 300 | 1 | no | 1164 | 0.2407 | 0 |
| B | 2 | 1.5g | 0 | 300 of 300 | 1 | no | 1164 | 0.2365 | 0 |
| B | 2 | 1g | 0 | 300 of 300 | 1 | yes | 51 | 0.0096 | 190 |
| B | 2 | 768m | 0 | 300 of 300 | 1 | yes | 51 | 0.0097 | 190 |
| B | 2 | 512m | 0 | 300 of 300 | 1 | yes | 51 | 0.0099 | 190 |
| B | 1 | 4g | 0 | 300 of 300 | 1 | no | 1165 | 0.4739 | 0 |
| B | 1 | 2g | 0 | 300 of 300 | 1 | no | 1164 | 0.4164 | 0 |
| B | 1 | 1.5g | 0 | 300 of 300 | 1 | no | 1164 | 0.3876 | 0 |
| B | 1 | 1g | 0 | 300 of 300 | 1 | yes | 51 | 0.0085 | 190 |
| B | 1 | 768m | 0 | 300 of 300 | 1 | yes | 51 | 0.0087 | 190 |
| B | 1 | 512m | 0 | 300 of 300 | 1 | yes | 52 | 0.0089 | 190 |

**Every run exits 0 and writes all 300 responses.** Task A with 2 CPUs runs two lanes at every limit (peak 206 MiB, 242
MiB once at 4g); with 1 CPU one lane. Task B as in session 14: two lanes at 4g, one under 2.5 GiB, without e5 below 1.5
GiB (51 MiB). Image size 2,216.3 MB (unchanged). The local times are higher than in session 14's grid (task A 0.08–0.11
against 0.05 s at 2 CPUs, also in the runs before the model run started); the grid is not the place to judge that: the
final local time is measured separately, twice, with the new reference (the final runs' NOTES). **A6 is not the
cause:** the same image with A6 on and off (`-- --no-second-look-a6`), alternating, task A dev at 4 GB, 2 CPUs, 0.1 s
per request, 15:34 to 15:38 UTC (beside stability run 1): on 0.084 / 0.077 s, off 0.077 / 0.092 s per case
(`a6_on_off/`; 306 against 301 requests).
