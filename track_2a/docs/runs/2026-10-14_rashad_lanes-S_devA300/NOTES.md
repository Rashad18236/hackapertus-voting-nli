### Two worker lanes with model S (session 14, step 2): the limit for S, and local time before and after

**The change** (`src/pipeline.py`, `src/cli.py`): a run in which no case can load e5 (`cli.loads_no_e5`: every case is
task A, section-route, a ranker without e5, the fallback bm25-ap or embed, L2 off) prepares its cases in one lane only
below `pipeline.MEMORY_FOR_TWO_LANES_S`; every other run keeps `MEMORY_FOR_TWO_LANES` (2.5 GiB, e5's load peak). Task B
is unchanged (selector T uses e5). The default number of lanes is computed after the input is read; `--workers` wins.

**The limit for S** (`peak_runs/`, 08:42–08:54 UTC): two lanes forced (`--workers 2`) in `main`'s image
`sha-3c609435dce7` at 4g, 2 CPUs: peaks dev 230 / 204, val 217 / 211, probe 92 / 120 MiB at 0.1 / 0.3 s per request;
P = 230 MiB, 2 × P = 460 MiB → the next grid limit, **512 MiB**. Forced two-lane dev runs at 2g, 1.5g, 1g, 768m and
512m (0.1 s): every response, labels equal to the 4g run, peaks 197–206 MiB. Their times are not used (G1/G2 ran on the
same CPUs meanwhile). During the rounds below, two 4g rounds of the before code peaked at 363 and 366 MiB (and two 1g
rounds of the before code, one lane, at 291–293 MiB), as session 13's final dev run did once (364 MiB): 512 MiB is
1.4 × that spike. The grid's two-lane runs at 768m and 512m test the limit under real memory pressure
(`2026-10-14_rashad_memory-grid-lanes-s14_grid24`).

**Local time** (`local_time/`, 08:54–10:27 UTC): `scripts/local_time.py` on all 300 dev task A cases, `main`'s image with
`--src` set to `main`'s own `src/` (before) or the working tree's (after; a frozen copy), 2 CPUs on CPUs 2–3, fake model
replaying session 13's reference answers (0 replay misses, every run 300 responses, exit 0), before and after
alternating, three rounds, medians (`lane_rule.json`). Uncompiled `src/` in both, so the absolute values are higher
than the published image's at 0.1 s. Lanes after: the CLI's log ("Worker processes: 2" in every after run); before:
from `main`'s code (2 at 4g, 1 under 2.5 GiB), which logs no count.

| Memory, s per request | Before (median; rounds) | After (median; rounds) | After − before | Lanes before → after |
|---|---|---|---|---|
| 4g, 1.0 | 0.0217 (0.0193, 0.0217, 0.0228) | 0.0186 (0.0171, 0.0186, 0.0193) | −0.0031 | 2 → 2 |
| 4g, 0.3 | 0.0192 (0.0207, 0.0192, 0.0178) | 0.0190 (0.0189, 0.0190, 0.0193) | −0.0002 | 2 → 2 |
| 4g, 0.1 | 0.0564 (0.0521, 0.0564, 0.0578) | 0.0571 (0.0504, 0.0633, 0.0571) | +0.0007 | 2 → 2 |
| 1g, 1.0 | 0.0203 (0.0184, 0.0203, 0.0222) | 0.0182 (0.0182, 0.0187, 0.0178) | −0.0021 | 1 → 2 |
| 1g, 0.3 | 0.0188 (0.0188, 0.0180, 0.0190) | 0.0200 (0.0200, 0.0192, 0.0200) | +0.0012 | 1 → 2 |
| 1g, 0.1 | **0.2108** (0.2108, 0.2130, 0.2061) | **0.0704** (0.0709, 0.0623, 0.0704) | **−0.1404** | 1 → 2 |

**LANE RULE** (decisions file): (1) at 4g after not above before + 0.002 s at any speed: −0.0031 / −0.0002 / +0.0007,
**holds**; (2) lower at 0.1 s where the change acts (1g): 0.2108 → 0.0704, **holds**; (3) the grid: see
`2026-10-14_rashad_memory-grid-lanes-s14_grid24`. pytest ran on CPUs 0–1 during two 4g rounds at 0.3 s (both
versions ran during the overlap).
