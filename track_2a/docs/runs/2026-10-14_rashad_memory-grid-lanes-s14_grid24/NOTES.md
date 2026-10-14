### Memory grid of the lane change (session 14, step 2): every response at every limit; task A keeps two lanes down to 512 MiB

**Set-up** (as session 13's grid, `docs/runs/2026-10-14_rashad_memory-grid-final-s13_grid24`): `main`'s image
`sha-3c609435dce7` with the working tree's `src/` mounted (`--src`, the after code of
`2026-10-14_rashad_lanes-S_devA300`), `scripts/local_time.py --peak-memory` against the fake model replaying session 13's
reference answers after 0.1 s per request, CPUs 2–3, all 300 dev cases of each task, memory limits 4g … 512m with 2 CPUs
and with 1, every limit run, 10:27 to 10:55 UTC. "Lanes" is the CLI's log line ("Worker processes"); "Guard" means the
memory guard marked e5 unusable (below 1.5 GiB; task A with model S does not use e5 anyway). `local_time/` holds each
run's `local_time.json`, `grid.json` this table. Times are from uncompiled `src/` (higher than the image's).

| Task | CPUs | Memory limit | Exit | Responses | Lanes | Guard | Peak memory (MiB) | Local time per case (s) |
|---|---|---|---|---|---|---|---|---|
| A | 2 | 4g | 0 | 300 of 300 | 2 | no | 366 | 0.0691 |
| A | 2 | 2g | 0 | 300 of 300 | 2 | no | 205 | 0.0551 |
| A | 2 | 1.5g | 0 | 300 of 300 | 2 | no | 207 | 0.0544 |
| A | 2 | 1g | 0 | 300 of 300 | 2 | yes | 207 | 0.0510 |
| A | 2 | 768m | 0 | 300 of 300 | 2 | yes | 207 | 0.0534 |
| A | 2 | 512m | 0 | 300 of 300 | 2 | yes | 207 | 0.0602 |
| A | 1 | 4g | 0 | 300 of 300 | 1 | no | 130 | 0.1967 |
| A | 1 | 2g | 0 | 300 of 300 | 1 | no | 129 | 0.1916 |
| A | 1 | 1.5g | 0 | 300 of 300 | 1 | no | 130 | 0.1969 |
| A | 1 | 1g | 0 | 300 of 300 | 1 | yes | 129 | 0.1868 |
| A | 1 | 768m | 0 | 300 of 300 | 1 | yes | 130 | 0.1950 |
| A | 1 | 512m | 0 | 300 of 300 | 1 | yes | 129 | 0.2077 |
| B | 2 | 4g | 0 | 300 of 300 | 2 | no | 1650 | 0.1835 |
| B | 2 | 2g | 0 | 300 of 300 | 1 | no | 1164 | 0.1455 |
| B | 2 | 1.5g | 0 | 300 of 300 | 1 | no | 1164 | 0.1465 |
| B | 2 | 1g | 0 | 300 of 300 | 1 | yes | 51 | 0.0086 |
| B | 2 | 768m | 0 | 300 of 300 | 1 | yes | 51 | 0.0082 |
| B | 2 | 512m | 0 | 300 of 300 | 1 | yes | 51 | 0.0082 |
| B | 1 | 4g | 0 | 300 of 300 | 1 | no | 1164 | 0.3219 |
| B | 1 | 2g | 0 | 300 of 300 | 1 | no | 1164 | 0.3117 |
| B | 1 | 1.5g | 0 | 300 of 300 | 1 | no | 1164 | 0.3240 |
| B | 1 | 1g | 0 | 300 of 300 | 1 | yes | 52 | 0.0081 |
| B | 1 | 768m | 0 | 300 of 300 | 1 | yes | 51 | 0.0086 |
| B | 1 | 512m | 0 | 300 of 300 | 1 | yes | 51 | 0.0084 |

**LANE RULE part (3) holds:** every run exits 0 and writes all 300 responses. Task A with 2 CPUs now runs two lanes at
every limit down to 512 MiB (before: one lane under 2.5 GiB; session 13's grid, compiled image: 0.124–0.130 s per case at
2g … 512m against 0.016 s at 4g); its peak stays at 205–207 MiB under every limit, 366 MiB once at 4g (no memory
pressure there). With 1 CPU task A has one lane, as before. Task B is unchanged: two lanes at 4g, one under 2.5 GiB;
below 1.5 GiB without e5 (51 MiB).
