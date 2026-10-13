# Session 12 status

Updated after every step. If the session is restarted with "continue", work goes on from "Next".

- **Branch:** `rashad/session-12` from `main` at `37904b3` (draft pull request, never merged, no tag).
- **Clock:** experiments stop on Wednesday 14 October at 02:00 UTC; everything pushed by 03:00 UTC.
- **Decisions:** `docs/decisions/2026-10-13-1035_rashad_session-12.md`.
- **Replay reference for G1/G2:** `docs/runs/2026-10-13_rashad_prompt-snapshot-final-s11_devAB-valA`.

## Done

- (10:35 UTC, Tue) Branch, status and decisions files; publish workflow builds `session-12`.
- (10:50) Step 0: `kaan/robustness-experiments` merged whole (everything off by default); 292 tests pass, 1 skipped.
  Dataset README unchanged (`fc2b276`): field table, no label definitions beyond the names.

- (11:20) Step 1a/b: model S (`src/static_embed.py`) equals sentence-transformers on 50 claims (3e-8); rankers
  offline (`docs/runs/2026-10-13_rashad_rankers-S_offline`): first cited paragraph among the 8 best, cross-language,
  e5 0.980, **S 0.993**, S+BM25 0.985, BM25 0.945 → **R = S** (256 dimensions; 1,024 adds at most 0.5 points).
  Vote names by meaning with S: margin 0.50 (71 right, 0 wrong of 264).
- (11:20) Code for steps 2, 3 and 5 written and tested (all off by default; `Settings.ranker` "e5" default): memory guard
  (`src/rankers.py` run_guard / failed), task B `cut4-r` (B-R) and `cut4-bm25` (B-BM25, Apertus translates
  cross-language claims), task A `--fallback-a bm25-ap`. G1/G2 pass; 310 tests pass. Commit `c3cbaac`.

- (11:47) Step 3 (`docs/runs/2026-10-13_rashad_taskb-selectors-s12_devB300`, one backend): T 0.987, B-R 0.973,
  H 0.993 (+13 % tokens), B-BM25 0.967: **none passes TASK B RULE 2; T stays**, no val run.
- (12:20) Step 1c (`docs/runs/2026-10-13_rashad_S-cost_devAB600`): task A local time per case at 1.0 / 0.3 / 0.1 s per
  request: e5 0.017 / 0.144 / 0.365, S 0.016 / 0.018 / 0.043; peak memory 2,286 → 200 MiB.
- (12:45) Steps 4 and 5 on dev (`docs/runs/2026-10-13_rashad_S-and-fallbacks_devA300`, one backend): **S fails S
  RULE (a)** (0.973 / 0.970 against 0.980 / 0.980; 2 breaks, 0 fixes): off, no val run, step 8 not done. **bm25-ap
  passes on dev** (forced fallback 0.956 / 0.736 against 0.900 / 0.672).
- (13:00) Step 2 (`docs/runs/2026-10-13_rashad_memory-guard_grid48`): memory guard on by default; both tasks write
  every response from 4g to 512m with 2 and 1 CPUs.

- (13:56) Step 5 val (`docs/runs/2026-10-13_rashad_bm25ap-fallback_valA300`): bm25-ap 0.957 / 0.755 against
  0.875 / 0.588 (forced): **passes the FALLBACK RULE; default.**
- (14:28) Step 6 dev and val (`docs/runs/2026-10-13_rashad_ap-structure-ask_{devA300,valA300}`): AP-structure asked
  after the parser, parser forced off: dev 0.946 / 0.925 vs 0.896 / 0.672, val 0.939 / 0.917 vs 0.872 / 0.593:
  **passes the STRUCTURE RULE; default.** Fixes found on the way: AP-part kept with it; a bm25-ap error goes on to
  embed-e5-small.
- (14:35) Final defaults committed (`828429c`): memory guard, bm25-ap fallback, AP-structure asked after the parser;
  G1/G2 differ only on the 4 dev/val cases that fall back (bm25-ap). Not adopted: B-R, H, B-BM25 (step 3), S (step 4).
  Step 8 not done (no default uses S). No separate probe run (the final runs include the probe).

- (15:18) FINISH final runs through `sha-828429cab766` (`docs/runs/2026-10-13_rashad_final-s12_*`): dev A 0.977 /
  0.980, B 0.987; val A 0.961 / 0.960, B 0.969; probe A 0.971 / 0.969, B 0.977; one backend, 0 failed calls,
  1 unreadable answer.
- (15:30) New replay reference `docs/runs/2026-10-13_rashad_prompt-snapshot-final-s12_devAB-valA` (0 of 1,180 differ).
- (16:30) Local time and REF SCORE: dev 0.903 / 0.845, val 0.913 / 0.907, probe 0.897 / 0.896 (1.0 / 0.3 s).
- (17:05) Memory grid of the final image: every response at every limit (4g to 512m, 2 and 1 CPUs).
- (17:05) Self-checks 17/17 (317 tests, after the ranker-state reset for unittest); technical report (6 pages) and
  PDF, session report, README, CLAUDE.md.

## Running

- Nothing. Session 12 is finished; the pull request stays a draft (never merged, no tag).

## Next

- For the team: decide whether model S's local-time gain (0.144 → 0.018 s per case at 0.3 s per request) is worth one
  dev case (`--ranker S`); see the session report.
