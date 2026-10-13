# Session 13 status

One line per event, UTC. If the session is restarted with "continue", work goes on from "Next".

- **Branch:** `rashad/session-13` from `main` at `c85a119` (draft pull request, never merged, no tag).
- **Clock:** experiments stop on Wednesday 14 October at 08:00 UTC; everything pushed by 09:00 UTC.
- **Decisions:** `docs/decisions/2026-10-13-1956_rashad_session-13.md`.
- **Replay reference for G1/G2:** `docs/runs/2026-10-13_rashad_prompt-snapshot-final-s12_devAB-valA`.

## Done

- (19:56 Tue) The instruction ends with "END OF SESSION 13 INSTRUCTION": complete.
- (19:57) Step 0: PR #20 checked: open, `mergeable_state` clean, head `668114f`, all four checks green (tests, image,
  publish, pull-and-run). It was a draft, which GitHub refuses to merge; marked ready for review, then merged with a
  merge commit: `main` = `c85a119` (branch kept).
- (19:58) Step 0: `origin/kaan/robustness-experiments` is an ancestor of `origin/main`; PR #19 closed with the comment
  "Contained in main via PR #20 (merged kaan/robustness-experiments in session 12)."
- (19:59) Step 0: publish-image on `main` (run 74, `c85a119`) succeeded: tags `latest` and `sha-c85a119b409a`.
  `origin/main` contains `668114f`.
- (20:00) Branch `rashad/session-13` from `origin/main`; publish workflow builds `session-13`; CLAUDE.md's current
  stage is session 13 (session 12 "merged as PR #20").

- (20:05) Step 1 code: prompts A1–A5 (`--prompt-a`), A6 (`--second-look-a6`), all off; pytest 332 passed; G1/G2 pass.
- (20:08) Step 1 format check (`docs/runs/2026-10-13_rashad_format-check-A_devA5`): all seven arms readable, fields
  in order; no arm void.
- (20:09) Step 1 dev run started (`docs/runs/2026-10-13_rashad_prompts-A_devA300-ontopic46`, 346 cases, 7 arms).
- (20:16) Step 2 code: prompts B1, B2, B4 (`--prompt-b v7-*`), B3 (`--context-b cut4-tf`), all off; G1/G2 pass.
  B3 offline (`docs/runs/2026-10-13_rashad_b3-picks_offline`): 383 of 539 long references (71 %) change a pick:
  B3 is an arm.
- (20:25) Step 3 code: H (`--evidence-hedge-a`, off); step 3 offline scoring started. Step 5:
  `docs/organiser_questions.md` written.
- (20:26) Step 4 groundwork: `scripts/error_types.py` offline part on session 12's val task A errors: 23 errors,
  13 reading, 10 routing (gold passage not in what Apertus read); of the 15 answered neutral, 9 reading, 6 routing.

- (20:30) G1/G2 with the H code (off): pass. With H on: G1 identical, 0 labels differ, evidence differs in 414 dev
  and val cases (as rebuilt offline).
- (20:36) **Step 3 done: H passes its rule** (`docs/runs/2026-10-13_rashad_evidence-pages_offline`): rule 3 (first
  gold page) dev 116 → 119, val 223 → 236, probe 44 → 46; text hit dev 197 → 198; nothing worse. Joins the combination.
  Rule 3 would cost about 40 % of today's evidence score (passages often start a page before the cited paragraph).

## Running

- Step 1 dev run (until about 21:40).

## Next

- Step 1 dev analysis, val run; step 2 format check and dev run.
