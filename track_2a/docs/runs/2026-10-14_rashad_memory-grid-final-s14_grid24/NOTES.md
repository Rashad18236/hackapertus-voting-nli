### Memory grid of the final session 14 image: every response at every limit; task A in two lanes down to 512 MiB

**Set-up** (as `2026-10-14_rashad_memory-grid-lanes-s14_grid24`, now through the published image itself): the final
image `ghcr.io/rashad18236/hackapertus-voting-nli:sha-228822b2e6fa` (session 13's defaults plus the lane change),
`scripts/local_time.py --peak-memory` against the fake model replaying session 13's reference answers after 0.1 s per
request, CPUs 2–3, all 300 dev cases of each task, memory limits 4g … 512m with 2 CPUs and with 1, every limit run,
11:02 to 11:30 UTC, beside the final dev600 model run on CPUs 0–1 (the local time column is indicative only). "Lanes"
is the CLI's log line; "Guard": the memory guard marked e5 unusable (below 1.5 GiB). `local_time/` holds each run's
`local_time.json`, `grid.json` this table. Replay misses: 0, except 190 in each task B run below 1.5 GiB (the memory
guard sends the 190 long references whole, requests the reference has no answer for; as in session 13's grid).

| Task | CPUs | Memory limit | Exit | Responses | Lanes | Guard | Peak memory (MiB) | Local time per case (s) |
|---|---|---|---|---|---|---|---|---|
| A | 2 | 4g | 0 | 300 of 300 | 2 | no | 207 | 0.0535 |
| A | 2 | 2g | 0 | 300 of 300 | 2 | no | 206 | 0.0528 |
| A | 2 | 1.5g | 0 | 300 of 300 | 2 | no | 207 | 0.0528 |
| A | 2 | 1g | 0 | 300 of 300 | 2 | yes | 207 | 0.0507 |
| A | 2 | 768m | 0 | 300 of 300 | 2 | yes | 206 | 0.0491 |
| A | 2 | 512m | 0 | 300 of 300 | 2 | yes | 207 | 0.0572 |
| A | 1 | 4g | 0 | 300 of 300 | 1 | no | 128 | 0.2019 |
| A | 1 | 2g | 0 | 300 of 300 | 1 | no | 129 | 0.2107 |
| A | 1 | 1.5g | 0 | 300 of 300 | 1 | no | 128 | 0.1994 |
| A | 1 | 1g | 0 | 300 of 300 | 1 | yes | 129 | 0.1949 |
| A | 1 | 768m | 0 | 300 of 300 | 1 | yes | 129 | 0.2025 |
| A | 1 | 512m | 0 | 300 of 300 | 1 | yes | 129 | 0.2091 |
| B | 2 | 4g | 0 | 300 of 300 | 2 | no | 1164 | 0.1870 |
| B | 2 | 2g | 0 | 300 of 300 | 1 | no | 1164 | 0.1753 |
| B | 2 | 1.5g | 0 | 300 of 300 | 1 | no | 1164 | 0.1829 |
| B | 2 | 1g | 0 | 300 of 300 | 1 | yes | 51 | 0.0084 |
| B | 2 | 768m | 0 | 300 of 300 | 1 | yes | 51 | 0.0095 |
| B | 2 | 512m | 0 | 300 of 300 | 1 | yes | 51 | 0.0082 |
| B | 1 | 4g | 0 | 300 of 300 | 1 | no | 1164 | 0.3493 |
| B | 1 | 2g | 0 | 300 of 300 | 1 | no | 1164 | 0.3487 |
| B | 1 | 1.5g | 0 | 300 of 300 | 1 | no | 1164 | 0.3522 |
| B | 1 | 1g | 0 | 300 of 300 | 1 | yes | 51 | 0.0081 |
| B | 1 | 768m | 0 | 300 of 300 | 1 | yes | 51 | 0.0090 |
| B | 1 | 512m | 0 | 300 of 300 | 1 | yes | 51 | 0.0080 |

**Every run exits 0 and writes all 300 responses.** Task A with 2 CPUs runs two lanes at every limit (peak 206–207 MiB);
with 1 CPU one lane. Task B as before: two lanes at 4g, one under 2.5 GiB, without e5 below 1.5 GiB (51 MiB). Image
size 2,216.3 MB (unchanged).
