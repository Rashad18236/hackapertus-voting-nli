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

## Running

- Step 2, dev: forced fallback run, 300 dev task A cases, arms today-routed, today-fallback-nopart, VW-nopart,
  BW-novote (`docs/runs/2026-10-12_rashad_fallbacks_devA300`).

## Next

- Step 2 on val (balanced 300: today's fallback, VW, BW) and probe (today vs new defaults); then steps 3 to 6 and
  FINISH.

## Numbers so far

- Parser coverage: 88 of 93 booklets complete (64 before); probe routed 90 of 94 (83 before).
