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

## Running

- Step 0: G1/G2 of the merge against the replay reference.

## Next

- Step 1: model S (static-similarity-mrl-multilingual-v1, tokenizers + numpy), rankers e5 / S / BM25 / S+BM25 /
  e5+BM25 offline, cost of S through the image, selection of R.
- Step 2: memory guard (no embedding model below the limit or when it cannot load).
- Step 3: task B selectors (B-R, H, third version; reading in the decisions file).
