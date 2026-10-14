# Session 15 status

One line per event, UTC. If the session is restarted with "continue", work goes on from "Next".

- **Branch:** `rashad/session-15` from `main` at `4f19500` (draft pull request, never merged, no tag).
- **Clock:** experiments stop on Thursday 15 October at 02:00 UTC; everything pushed by 03:00 UTC.
- **Decisions:** `docs/decisions/2026-10-14-1313_rashad_session-15.md`.
- **Replay reference for G1/G2:** `docs/runs/2026-10-14_rashad_prompt-snapshot-final-s14_devAB-valA`.

## Done

- (13:13 Wed) The instruction ends with "END OF SESSION 15 INSTRUCTION": complete. dockerd restarted (container
  restarted).
- (13:15) Step 0: PR #22 checked: open, draft, `mergeable_state` clean, head `ec7a6c1`, all four checks green. Marked
  ready (second attempt; the first hit a connection reset), merged with a merge commit: `main` = `4f19500` (branch kept).
  `origin/main` contains `ec7a6c1`.
- (13:16) Branch `rashad/session-15` from `origin/main`; the publish workflow also builds `session-15`.
- (13:22) Step 1: `second_look_a6 = True` by default; five tests that assumed A6 off say so explicitly; pytest 348
  passed, 1 skipped. G1/G2 against the session 14 reference: first requests and paths identical in all 1,180 cases;
  A6's second looks added in 15 cases (dev 5, val 10); G2 0 differences (stub second looks unreadable).
- (13:24) Step 0: publish-image on `main` (run 92) succeeded: `latest` and `sha-4f1950002ca0`. `latest` pulls without a
  login: digest `sha256:e3e61af166c0…`, the same image as `sha-4f1950002ca0`, revision label `4f19500` = `main`.
- (13:29) Step 2 code: A6b (`--second-look-a6-prompt A-v6-second-look-b`, off); test. Decisions for steps 0–2 written; G1/G2 with
  the A6b code identical to step 1's. Technical report: A6's role row, its negative-results row removed, the team's sentence in Limitations.
- (13:30) Step 2 run started (`docs/runs/2026-10-14_rashad_A6b_devA300-valA580-probeA94-ontopic46`: today (A6), A6b;
  1,020 cases, CPUs 0–1, 1 request per second).
- (13:36) Steps 3–4 code: `v7-same-ballot-f` (B1 with the format fixed) and B6 (`--second-look-b6`), both off; tests;
  pytest 356 passed, 1 skipped; G1/G2 identical to step 1's snapshot. Decisions for steps 3 and 4 written.
- (14:10) Step 2 run done (`docs/runs/2026-10-14_rashad_A6b_devA300-valA580-probeA94-ontopic46`, one backend, 0 failed
  calls, first answers shared): A6 and A6b gave the same finding in all 19 second looks; dev 0.977, val 0.981, probe
  0.990 for both; on-topic flips 3 and 3 (rows 85, 232, 1026). **A6b fails (2): not adopted.** Session 14's four
  still-wrong val cases get no second look (their first answer cites no paragraph).
- (14:11) Step 3 format check (`docs/runs/2026-10-14_rashad_format-check-B1f_devB10`): all 10 B1f answers readable,
  fields in order (6 ballot names cut at 40 characters, still closed): not void.
- (14:12) Step 3 dev run started (`docs/runs/2026-10-14_rashad_B1f_devB300`: today, B1f; 300 task B cases).

## Running

- Step 3 dev run (started 14:12).

## Next
