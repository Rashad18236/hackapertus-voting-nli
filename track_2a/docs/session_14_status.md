# Session 14 status

One line per event, UTC. If the session is restarted with "continue", work goes on from "Next".

- **Branch:** `rashad/session-14` from `main` at `3c60943` (draft pull request, never merged, no tag).
- **Clock:** experiments stop on Wednesday 14 October at 15:00 UTC; everything pushed by 16:00 UTC.
- **Decisions:** `docs/decisions/2026-10-14-0832_rashad_session-14.md`.
- **Replay reference for G1/G2:** `docs/runs/2026-10-14_rashad_prompt-snapshot-final-s13_devAB-valA`.

## Done

- (08:32 Wed) The instruction ends with "END OF SESSION 14 INSTRUCTION": complete.
- (08:33) Step 0: PR #21 checked: open, draft, `mergeable_state` clean, head `b0b88f6`, all four checks green (tests,
  image, publish, pull-and-run). Marked ready for review, then merged with a merge commit: `main` = `3c60943` (branch
  kept). `origin/main` contains `b0b88f6`.
- (08:34) Branch `rashad/session-14` from `origin/main`; the publish workflow also builds `session-14`.
- (08:34) dockerd was not running (container restarted); started again. Session 13's local images still present.
- (08:35) Step 1 decisions written (A6 CONFIRMATION RULE readings); cases file (580 val + 94 probe + 46 on-topic task A)
  and booklet folder (51 booklets, no sealed date) prepared.

- (08:36) Step 1 run started (`docs/runs/2026-10-14_rashad_A6-confirm_valA580-probeA94-ontopic46`: today, today+A6;
  720 cases, CPUs 0–1, 1 request per second).
- (08:38) Step 0: publish-image on `main` (run 87, `3c60943`) succeeded: tags `latest` and `sha-3c609435dce7`. `latest`
  pulls without a login (empty Docker config): digest `sha256:3572bfdebce7…`, the same image as `sha-3c609435dce7`,
  revision label `3c60943` = `main`.
- (08:38) CLAUDE.md: session 14 is the current stage; session 13 "merged as PR #21".
- (08:41) Step 2 decisions written (lane limit for S, LANE RULE readings, local-time protocol, grid).
- (08:42–08:54) Step 2: two lanes forced in `main`'s image at 4g: peaks dev 230 / 204, val 217 / 211, probe 92 / 120
  MiB (0.1 / 0.3 s); forced two-lane dev runs at 2g … 512m write all responses with the 4g labels. Limit for S: 512 MiB
  (2 × 230 MiB → the next grid limit). Code: `pipeline.MEMORY_FOR_TWO_LANES_S`, `cli.loads_no_e5`, unit tests.
- (08:53) G1/G2 of the lane change: identical (0 requests, labels or evidence differ).
- (09:05) Step 1 run done (`docs/runs/2026-10-14_rashad_A6-confirm_valA580-probeA94-ontopic46`, one backend, 0 failed
  calls): val 0.969 → 0.981, probe 0.981 → 0.990, 9 fixes / 1 break, tokens +0.6 %, 0 unreadable; on-topic flips 3
  (rows 85, 232, 1026; bar 2). **A6 fails (f) by one case: not adopted.**
- (10:27) Step 2 local time done (`docs/runs/2026-10-14_rashad_lanes-S_devA300`): at 4g after − before −0.003 /
  −0.000 / +0.001 s at 1.0 / 0.3 / 0.1 s; at 1g and 0.1 s 0.211 → 0.070 s per case (two lanes). LANE RULE (1) and (2)
  hold. 4g rounds of both versions sometimes peak at 363–366 MiB (reported; the limit stays 512 MiB as fixed).
- (10:27) Step 2 memory grid started (after code, tasks A and B, 4g … 512m, 2 and 1 CPUs).
- (10:55) Step 2 memory grid done (`docs/runs/2026-10-14_rashad_memory-grid-lanes-s14_grid24`): every response at every
  limit, both tasks, 2 and 1 CPUs; task A with 2 CPUs in two lanes down to 512 MiB (peak 207 MiB). **LANE RULE holds:
  the lane change is adopted** (`MEMORY_FOR_TWO_LANES_S` = 512 MiB).
- (11:05) G1/G2 of the final `src/` (log line moved): identical; pytest 348 passed, 1 skipped.

## Running

## Next
