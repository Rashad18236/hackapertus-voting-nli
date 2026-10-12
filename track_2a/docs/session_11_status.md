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

- (22:18) Step 2, val (`docs/runs/2026-10-12_rashad_fallbacks_valA300`, one backend): today's fallback 0.875 /
  0.593 / 1,827 + 15.8; VW 0.873 / 0.716 / 1,079 + 14.4; BW 0.856 / 0.627 / 951 + 14.5. **FALLBACK RULE: VW fails
  (Macro-F1 −0.002, needs +0.02), BW fails; both off; no default changed; probe run not needed.**
- (22:08) Q (8-bit e5) for task A: changes the 8 paragraphs of 50 of 75 cut cases, so G1 cannot hold; off.

## Running

- Step 3a (from 22:18): AP-structure on the 93 booklets (`docs/runs/2026-10-12_rashad_ap-structure_booklets93`).
  Then (`chain2`) step 3 runs 1–3: AP-all on dev 300 and the probe 94; AP-part on 150 reworded dev cases (today, VW,
  AP-part); AP-structure with the parser off on dev 300 (today, VW, AP-structure). Model runs on CPUs 0–1.
- Step 4 (CPUs 2–3): local time of today, light-first, lazy pages, both, one ONNX thread per lane, in alternating
  rounds at 0.3 s per request. First single measurements at 0.3 s: today 0.225, light 0.185, lazy 0.181,
  light+lazy 0.131 s per case (beside a model run; noisy).
- Code for steps 2–6 is written and committed (`4a4c14f`, all off by default; G1/G2 pass, tests pass).

## Next

- Step 2 decision (FALLBACK RULE) and probe; step 3 runs 1–3 (and 4 if 3b allows), 3d image check; step 4 profile
  and fixes; step 5 memory; step 6 selectors; FINISH.

## Numbers so far

- Parser coverage: 88 of 93 booklets complete (64 before); probe routed 90 of 94 (83 before).
