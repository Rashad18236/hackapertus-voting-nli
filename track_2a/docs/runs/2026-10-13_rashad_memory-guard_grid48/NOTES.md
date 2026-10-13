### Memory guard (session 12 step 2): both tasks answer every case from 4 GiB down to 512 MiB, with 2 CPUs and with 1

**The guard** (`src/rankers.py`, `src/cli.py`): before the worker processes start, every embedding model whose need
(`rankers.MIN_MEMORY`: e5 1.5 GiB, the smallest limit at which session 11's runs with e5 answered every case; model S
0.5 GiB) is above the container's memory limit (cgroup), or whose files are missing, is marked unusable for the whole
run. Where a model would be used, an exception while loading or running it (MemoryError included) marks it the same
way for the rest of the run. Without the model: a long routed part sends its first 8 paragraphs, the fallback ranks
the booklet's chunks by BM25 alone (word overlap), a vote name is not placed by meaning, and task B sends a long
reference whole. Each case that went without its model carries `ranker_guard` in its raw answer; the run log counts
them. Before this step, session 11's image lost 24 task A responses (and 190 task B responses) at 1 GiB to the
kernel's out-of-memory kill.

**Grid** (`ghcr.io/rashad18236/hackapertus-voting-nli:sha-c3cbaac54b15`, today's defaults; `scripts/local_time.py`,
fake model replaying the session 11 reference's answers after 0.1 s per request, CPUs pinned to 2-3; all 300 dev
cases of each task):

| Task | CPUs | Memory limit | Exit | Responses | Guard | Cases without e5 | Peak memory (MiB) | Local time per case (s) |
|---|---|---|---|---|---|---|---|---|
| A | 2 | 4g | 0 | 300 of 300 | no | 0 | 2287 | 0.3343 |
| A | 2 | 2g | 0 | 300 of 300 | no | 0 | 1195 | 0.4566 |
| A | 2 | 1.5g | 0 | 300 of 300 | no | 0 | 1195 | 0.4442 |
| A | 2 | 1g | 0 | 300 of 300 | yes | 300 | 91 | 0.1511 |
| A | 2 | 768m | 0 | 300 of 300 | yes | 300 | 90 | 0.1569 |
| A | 2 | 512m | 0 | 300 of 300 | yes | 300 | 90 | 0.1532 |
| A | 1 | 4g | 0 | 300 of 300 | no | 0 | 1194 | 0.6959 |
| A | 1 | 2g | 0 | 300 of 300 | no | 0 | 1195 | 0.7224 |
| A | 1 | 1.5g | 0 | 300 of 300 | no | 0 | 1194 | 0.7247 |
| A | 1 | 1g | 0 | 300 of 300 | yes | 300 | 91 | 0.1741 |
| A | 1 | 768m | 0 | 300 of 300 | yes | 300 | 90 | 0.1655 |
| A | 1 | 512m | 0 | 300 of 300 | yes | 300 | 90 | 0.1673 |
| B | 2 | 4g | 0 | 300 of 300 | no | 0 | 1164 | 0.1407 |
| B | 2 | 2g | 0 | 300 of 300 | no | 0 | 1164 | 0.1477 |
| B | 2 | 1.5g | 0 | 300 of 300 | no | 0 | 1164 | 0.142 |
| B | 2 | 1g | 0 | 300 of 300 | yes | 300 | 51 | 0.007 |
| B | 2 | 768m | 0 | 300 of 300 | yes | 300 | 51 | 0.0077 |
| B | 2 | 512m | 0 | 300 of 300 | yes | 300 | 51 | 0.0077 |
| B | 1 | 4g | 0 | 300 of 300 | no | 0 | 1164 | 0.3153 |
| B | 1 | 2g | 0 | 300 of 300 | no | 0 | 1164 | 0.3004 |
| B | 1 | 1.5g | 0 | 300 of 300 | no | 0 | 1164 | 0.3061 |
| B | 1 | 1g | 0 | 300 of 300 | yes | 300 | 51 | 0.0078 |
| B | 1 | 768m | 0 | 300 of 300 | yes | 300 | 51 | 0.0073 |
| B | 1 | 512m | 0 | 300 of 300 | yes | 300 | 51 | 0.0071 |

Every response is written at every limit. At 2 GiB and above (and at 1.5 GiB) nothing changes: the guard does not act
and the answers equal the 4 GB run's; on the host, without a limit, G1/G2 pass against the replay reference.
Below 1.5 GiB the whole run goes without e5 (this image counts every case of such a run; from `6baf3a4` on, only
the cases that would have used the model). The fake model's labels differ there for 16 task A and 131 task B cases
only because those requests (first 8 paragraphs, whole references) are not in its replay table; the guard's effect on
real answers is measured in FINISH (`memory_final.txt` of the final runs).

The local time under the guard is lower (no embedding); at 1.5 GiB and 2 GiB task A runs one lane (session 11,
`pipeline.MEMORY_FOR_TWO_LANES`).
