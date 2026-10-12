# Session 11 status

Updated after every step. If the session is restarted with "continue", work goes on from "Next".

- **Branch:** `rashad/session-11` from `main` at `014f691` (draft pull request, never merged, no tag).
- **Clock:** experiments stop on Tuesday 13 October at 09:30 UTC; everything pushed by 10:30 UTC.
- **Decisions:** `docs/decisions/2026-10-12-2010_rashad_session-11.md`.

## Done

- (20:10 UTC, Mon) Branch, status and decisions files, draft pull request #18; publish workflow builds `session-11`.
- (20:40) Step 1: 93 booklets (2016–2026, sealed dates never downloaded); parser fixes (older layout, unreadable fonts,
  lost arguments heading, per-part validity). Booklets complete 64 → 88 of 93, votes passing 178 → 244 of 249, all
  249 with a usable part, cross-language disagreements 2 → 0; probe routed 83 → 90 of 94. G1/G2 pass; adopted
  (`docs/runs/2026-10-12_rashad_parser-coverage_booklets93`).

- (21:22) Step 2, dev: forced fallback run on 300 dev task A cases (`docs/runs/2026-10-12_rashad_fallbacks_devA300`,
  one backend). Macro-F1 / evidence / input + output tokens: today-routed 0.977 / 0.980 / 1,238 + 14.5;
  today's fallback ("no part") 0.900 / 0.672 / 1,868 + 15.8; VW ("no part") 0.927 / 0.766 / 1,078 + 14.4;
  BW ("no vote") 0.857 / 0.647 / 939 + 14.3. BW is lower on dev: fails the FALLBACK RULE (off). VW goes to val.

## Running

- Step 2, val (from 21:22): balanced val sample, today's fallback, VW ("no part"), BW ("no vote", for the record)
  (`docs/runs/2026-10-12_rashad_fallbacks_valA300`). Queued after it (`chain1`): step 3a (AP-structure on the 93
  booklets).
- Code for steps 2–6 is written and committed (`4a4c14f`, all off by default; G1/G2 pass, tests pass).

## Next

- Step 2 decision (FALLBACK RULE) and probe; step 3 runs 1–3 (and 4 if 3b allows), 3d image check; step 4 profile
  and fixes; step 5 memory; step 6 selectors; FINISH.

## Numbers so far

- Parser coverage: 88 of 93 booklets complete (64 before); probe routed 90 of 94 (83 before).
