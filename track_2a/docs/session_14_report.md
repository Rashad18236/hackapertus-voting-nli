# Session 14: A6 confirmed on the final defaults, two worker lanes with model S

Branch `rashad/session-14` from `main` at `3c60943` (session 13 merged in step 0), 2026-10-14 08:32 to 16:00 UTC,
unattended. Status log: `docs/session_14_status.md`; decisions, each written before the run it concerns:
`docs/decisions/2026-10-14-0832_rashad_session-14.md`. Rules as in session 13 (only the 8B on Public AI, one request
per second, one model run at a time; sealed dates never opened; every label from an answer of Apertus).

## In short

**Finished:** step 0, steps 1 and 2, and FINISH; nothing was dropped for time (the last model call ended at 11:14 UTC;
experiments stop at 15:00).

**Defaults changed, each by its rule:** **two worker lanes with model S** (step 2): task A keeps two lanes down to a
512 MiB memory limit when no case of the run can load e5 (before: one lane under 2.5 GiB, set for e5). Under a 1 GB
limit task A's local time at 0.1 s per request falls from 0.211 to 0.070 s per case; at 4 GB nothing changes; every
response is written at every limit. Requests and answers do not change (G1/G2 identical).

**Not adopted:** **A6** (step 1), the second look after a neutral answer that cites paragraphs, confirmed on the final
defaults: val 0.969 → 0.981, probe 0.981 → 0.990, 9 fixes / 1 break (p = 0.011), +0.6 % input tokens, 0 unreadable,
at most one second look per case; but 3 of the 46 on-topic neutral cases flipped to contradiction, and the team's bar was
2. It fails by one case, as in session 13.

**Final defaults through the published image** `sha-228822b2e6fa` (dev600 only: the lane change alters no request; val
and probe keep session 13's final runs): dev task A **0.970** (evidence 0.980), task B **0.987**; tokens per case (input + output) A 1,251 + 14.7, B 815 + 8.9; REF SCORE **0.900 / 0.898** at 1.0 / 0.3 s per request (session 13: 0.915 / 0.911; the drop comes from task B's local time measured in a slower window, which session 13's own image showed too, and one task A label that changed at the endpoint, not from the lane change). Python wrote 0 of 600 labels.

**Left for the team:** A6 (twice now just over its on-topic bar: 2 of 46 flips in session 13, 3 here; strong on real
cases), and whether 512 MiB for two lanes is enough margin given the 363–366 MiB peaks seen at 4 GB (every limit down to
512 MiB passed in the grid).

## Step 0: session 13 merged

PR #21 (`rashad/session-13`, head `b0b88f6`) was open, a draft, `mergeable_state` clean, with all four checks green
(tests, image, publish, pull-and-run). It was marked ready for review and merged with a merge commit: `main` =
`3c60943`, branch kept; `origin/main` contains `b0b88f6`. publish-image on `main` (run 87) succeeded with the tags
`latest` and `sha-3c609435dce7`. `latest` pulls without a login (an empty Docker configuration): digest
`sha256:3572bfdebce7…`, the same image as `sha-3c609435dce7`, revision label `3c60943` = `main`. The publish workflow
also builds `rashad/session-14` (tag `session-14`).

## Step 1: A6 confirmed on the final defaults

**Why again:** in session 13, A6 (a second look after a neutral answer that cites paragraphs) ran on session 12's
defaults (e5 ranker, no hedge) and scored val 0.973 against 0.959 (val 9 fixes / 1 break, dev 1 / 0), +0.8 % input
tokens, and failed only the on-topic condition (2 flips, at most 1 allowed). The team decided to confirm it once more
on the final defaults (model S + hedge H) with the on-topic bar raised to 2, because on val's real neutrals A6 made 1
break in 11 changes and neutral F1 rose 0.957 → 0.981, while the on-topic set is 46 synthetic cases. The flag is
`--second-look-a6` (the instruction's `--second-look-a` names L2, session 9); A6's code is unchanged.

**Run** (`docs/runs/2026-10-14_rashad_A6-confirm_valA580-probeA94-ontopic46`, 08:36 to 09:05 UTC): arms `today`
(session 13's final defaults) and `today+A6`, interleaved, on all 580 val, all 94 probe and the 46 on-topic neutral task
A cases (720), 1,464 calls (1,440 first answers, 14 second looks, 10 AP-translate calls of fallback cases), one backend (blablador `vllm-0.23.1rc1`), 0 failed calls. **Both arms share every first
answer** (720 of 720): in each case the arm sent second repeated the first arm's request and got it from the gateway's
cache, so the two arms differ exactly by A6's second looks.

| Set, arm | Macro-F1 | F1 ent / neu / con | Evidence | Input + output tokens per case | Unreadable | Gold contradiction answered neutral |
|---|---|---|---|---|---|---|
| val, today | 0.9691 | 0.984 / 0.965 / 0.958 | 0.965 | 1,224.9 + 14.7 | 0 | 12 |
| val, today+A6 | **0.9812** | 0.984 / 0.983 / 0.976 | 0.985 | 1,233.1 + 14.9 | 0 | 4 |
| probe, today | 0.9808 | 1.000 / 0.966 / 0.977 | 0.985 | 1,171.8 + 16.5 | 0 | 1 |
| probe, today+A6 | **0.9903** | 1.000 / 0.983 / 0.989 | 1.000 | 1,177.4 + 16.6 | 0 | 0 |
| dev (session 13's run, session 12's defaults), today / today+A6 | 0.983 / 0.987 | | 0.985 / 0.990 | 1,240.4 / 1,242.1 + 14.7 | 0 / 0 | 1 / 0 |

**Second looks:** 14 (val 10 = 1.7 per 100 cases, probe 1 = 1.1 per 100, on-topic 3), 0 unreadable, 0 failed, 314–592
input + 8 output tokens each. 13 of 14 changed the answer to a contradiction ("different"): **val 8 fixes** (rows 1053,
1151, 1210, 1226, 1309, 1318, 1404, 1467), **val 1 break** (row 950, gold neutral), **probe 1 fix** (row 1453), and
**all 3 on-topic second looks** (rows 85, 232, 1026). One kept neutral (row 991, gold neutral).

**A6 CONFIRMATION RULE** (written before the run):

| Condition | Result | Holds |
|---|---|---|
| (a) val Macro-F1 at least +0.005 | 0.9691 → 0.9812 (+0.0121) | yes |
| (b) probe Macro-F1 not below today | 0.9808 → 0.9903 | yes |
| (c) fixes > breaks over val + probe, sign test p ≤ 0.10 | 9 / 1, p = 0.011 (one-sided; 0.021 two-sided) | yes |
| (d) mean input tokens per case at most +3 % (val + probe) | 1,217.5 → 1,225.3 (+0.64 %) | yes |
| (e) no more unreadable answers than today | 0 / 0 | yes |
| (f) at most 2 on-topic answers flip away from neutral | **3** (rows 85, 232, 1026; neutral 31 → 28 of 46) | **no** |
| (g) A6 never fires more than once per case | one record per case; tokens per case equal its recorded calls | yes |

**Verdict: A6 is not adopted** ((f) fails by one case); `second_look_a6` stays off. Rows 232 and 1026 flipped in
session 13 too; row 85 is new. What A6 does well is clear: it removes 8 of val's 12 "gold contradiction answered
neutral" errors and probe's one; what it does badly is the same move on a passage that is on topic but does not settle
the claim, where every one of its 3 on-topic looks said "different".

**Session 12's 15 val errors answered neutral** (`2026-10-13_rashad_final-s12_val1160`; another run, so indicative):
today fixes 3 (rows 341, 1025, 1159); today+A6 fixes 11 (also 1053, 1151, 1210, 1226, 1309, 1318, 1404, 1467); still
wrong with A6: rows 235, 1200, 1347, 1351; one new error answered neutral in both arms (row 1175).

## Step 2: two worker lanes with model S

**The change** (`src/pipeline.py`, `src/cli.py`, unit tests in `tests/test_pipeline.py`): `MEMORY_FOR_TWO_LANES` (2.5 GiB)
was set in session 11 for e5's load peak (two lanes each loading e5). With model S as task A's ranker a run of task A
cases never loads e5, so its limit can be lower. `cli.loads_no_e5` says when no case of a run can load e5 (every case
task A, section-route, a ranker without e5, the fallback bm25-ap or embed, L2 off); then `pipeline.default_workers`
uses `MEMORY_FOR_TWO_LANES_S`, otherwise 2.5 GiB as before (any task B case: selector T uses e5). The number of lanes is
now chosen after the input is read, and the CLI logs it ("Worker processes: N"). G1 and G2 against the session 13
reference: identical (0 requests, labels or evidence differ), as expected: the lanes change when a case is prepared,
never what is sent.

**The limit for S** (`docs/runs/2026-10-14_rashad_lanes-S_devA300/peak_runs`): two lanes forced (`--workers 2`) in
`main`'s image at 4g peaked at dev 230 / 204, val 217 / 211, probe 92 / 120 MiB (0.1 / 0.3 s per request). The rule
fixed before: twice the highest peak (460 MiB), rounded up to the next grid limit: **512 MiB**, provided a forced
two-lane dev run there writes every response with the 4g labels (it does, at 2g … 512m, peaks 197–206 MiB). Below
512 MiB model S is not used anyway (memory guard). **A caveat, reported:** during the local-time rounds, a few 4g runs of
both versions peaked at 363–366 MiB (as session 13's final dev run did once), so 512 MiB is 1.4 × the highest peak seen
at 4g, not 2 ×; under a 512m–1g limit the two lanes peaked at 205–208 MiB in every run (page cache gives way under
pressure), and every response was written.

**Local time** (`docs/runs/2026-10-14_rashad_lanes-S_devA300`, `scripts/local_time.py`, all 300 dev task A cases, `main`'s
image with `main`'s `src/` (before) or the change (after) mounted, 2 CPUs, three alternating rounds, medians; s per case):

| Memory, s per request | Before | After | After − before | Lanes before → after |
|---|---|---|---|---|
| 4g, 1.0 | 0.0217 | 0.0186 | −0.0031 | 2 → 2 |
| 4g, 0.3 | 0.0192 | 0.0190 | −0.0002 | 2 → 2 |
| 4g, 0.1 | 0.0564 | 0.0571 | +0.0007 | 2 → 2 |
| 1g, 1.0 | 0.0203 | 0.0182 | −0.0021 | 1 → 2 |
| 1g, 0.3 | 0.0188 | 0.0200 | +0.0012 | 1 → 2 |
| 1g, 0.1 | **0.2108** | **0.0704** | **−0.1404** | 1 → 2 |

**Grid** (`docs/runs/2026-10-14_rashad_memory-grid-lanes-s14_grid24`, the after code, 0.1 s per request): every run exits
0 with all 300 responses at 4g, 2g, 1.5g, 1g, 768m and 512m, with 2 CPUs and with 1, for both tasks. Task A with 2 CPUs
now runs two lanes at every limit (peak 205–207 MiB under a limit); with 1 CPU one lane, as before; task B unchanged.

**LANE RULE:** (1) not higher at any speed at 4 GB (tolerance +0.002 s): −0.0031 / −0.0002 / +0.0007, holds; (2) lower at
0.1 s where the change acts (1 GB): 0.2108 → 0.0704, holds; (3) the grid passes. **Adopted** (commit `228822b`).

## FINISH

**Default changed:** the lane limit only (A6 stays off). Committed as `228822b` after G1/G2 (identical) and pytest;
the publish workflow built `ghcr.io/rashad18236/hackapertus-voting-nli:sha-228822b2e6fa` (also `session-14`), image size
2,216.3 MB (unchanged).

**Final run through the published image** (`docs/runs/2026-10-14_rashad_final-s14_dev600`, 11:01 to 11:14 UTC, `make run`,
task A and task B in separate containers, one backend, 0 failed calls, 0 gateway cache hits). **Only dev600:** the lane
change alters no request (G1/G2 identical), as the instruction allows; val and probe keep session 13's final runs.

| | Macro-F1 | Evidence | Input + output tokens per case | Python labels | Session 13's final dev run |
|---|---|---|---|---|---|
| Task A | **0.970** | **0.980** (197 of 201) | 1,251 + 14.7 | 0 | 0.973 / 0.985 |
| Task B | **0.987** | — | 815 + 8.9 | 0 | 0.987 |

One task A label differs from session 13's final dev run, row 1161 (gold contradiction, now neutral), from an identical
request. `scripts/check_format.py` on both prediction files: no errors.

**Local time and REF SCORE** (the final image, `scripts/local_time.py`, 2 CPUs on CPUs 2–3, 4 GB, fake model replaying
the new reference; at 1.0 and 0.3 s the mean of two measurements):

| Latency per request | Task A (s per case) | Task B | S_A | S_B | REF SCORE |
|---|---|---|---|---|---|
| 1.0 s | 0.0205 (0.0182, 0.0227) | 0.0124 (0.0130, 0.0118) | 0.9020 | 0.8968 | **0.8999** |
| 0.3 s | 0.0217 (0.0221, 0.0212) | 0.0134 (0.0150, 0.0117) | 0.9020 | 0.8922 | **0.8981** |
| 0.1 s | 0.0601 | 0.1614 | 0.8768 | 0.8409 | 0.8624 |

Task A under 1 GB (two lanes now): 0.0189 / 0.0239 / 0.0633 s at 1.0 / 0.3 / 0.1 s. **Why REF SCORE is below session
13's 0.9149 / 0.9107:** task B's code has not changed since session 11, but its local time measured 0.012–0.015 s here
against 0.008–0.009 s in session 13; session 13's own image, measured for task B in the same window as a control, gave
0.0157 / 0.0425 s. The machine was slower in this window (T_B 0.625 → 0.403 at 1.0 s); the rest is the one task A label.
At 4 GB the lane change does not act.

**Memory grid of the final image** (`docs/runs/2026-10-14_rashad_memory-grid-final-s14_grid24`): every response at 4g,
2g, 1.5g, 1g, 768m and 512m with 2 CPUs and with 1, both tasks; task A with 2 CPUs in two lanes at every limit (peak
206–207 MiB under a limit), task B unchanged.

**Replay reference:** `docs/runs/2026-10-14_rashad_prompt-snapshot-final-s14_devAB-valA` (dev answers from the final
dev600 run, val task A answers from session 13's final val run, whose requests are the same) reproduces both exactly (0 of
1,180 labels or evidence differ); it is G1/G2's anchor and `scripts/local_time.py`'s default.

**Technical report:** A6's row in the negative-results table carries this run's numbers; the architecture, summary table
(dev from the session 14 image), local time and memory paragraphs, reproducibility and references are updated; PDF
rebuilt, 6 pages. README's memory paragraph updated. CLAUDE.md: session 14 is the current stage.

**Checks:** pytest 348 passed, 1 skipped (unittest: 349 tests, 0 failures); self-checks 17 of 17; `scripts/build_docs.py --check`; pypdf 6.17.0;
`.env.example` unchanged (no new variable); publish-image and clean-machine workflows: green on `228822b` (the final image) and on the final commit.
`latest` (from `main`, step 0): digest `sha256:3572bfdebce7…` = `sha-3c609435dce7`, pulled without a login.

**Not done:** nothing from the instruction. Left for the team: A6 (val +0.012 and probe +0.010 here, but over the
on-topic bar both times it was tried), and whether 512 MiB leaves enough margin for two lanes given the occasional
363–366 MiB peaks at 4 GB (every limit down to 512 MiB passed both grids).
