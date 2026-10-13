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

## Running

- Step 3 dev run (`docs/runs/2026-10-13_rashad_taskb-selectors-s12_devB300`, from 11:19): today (T), B-R, H, B-BM25.
- The image with model S (publish workflow, `c3cbaac`), for step 1c (local time, memory of S) and step 2 (memory grid).

## Next

- Step 1c through the image; step 2 grid (4g … 512m × 2/1 CPUs).
- Step 3 val run of the best version (TASK B RULE 2 in the decisions file).
- Step 4 (R = S in task A) and step 5 (bm25-ap fallback): forced and cut-case runs on dev, then val.
