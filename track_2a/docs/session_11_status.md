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

- (22:33) Step 3a: AP-structure on 93 booklets: 78.7 % of current-layout votes equal to the parser's (needs 95 %);
  1,796 + 176 tokens per booklet (`docs/runs/2026-10-12_rashad_ap-structure_booklets93`).
- (23:07, 23:19) Step 3 run 1: AP-all vs today, dev 0.960 / 0.891 vs 0.977 / 0.980 (1,655 + 91 vs 1,238 + 14.5 tokens);
  probe 0.951 / 0.877 vs 0.971 / 0.954. Apertus's part = rules' part 89 %. Step 3b: net gain 0 → run 4 not run.
- (23:20) Step 4 adopted (SAME-ANSWER RULE): light-first, lazy pages (one open reader), SHARE_CPUS; G1/G2 pass;
  task A local time at 0.3 s 0.202 → 0.101 s per case (`docs/runs/2026-10-12_rashad_local-time-step4_devA300`).
- Step 2 local work per fallback case: routed 0.29 s, today's fallback 1.74 s, VW 1.31 s, BW 1.61 s.

## Running

- Step 3 run 2 (from 23:19): 150 reworded dev cases, today / VW / AP-part; then run 3 (parser off: today's fallback,
  VW, AP-structure). Model runs on CPUs 0–1.
- CPUs 2–3: step 6a local time (full, L, H), then step 5 memory sweep, then step 6a (E, T, Q), then AP-all's local
  time (replay of run 1).

## Next

- Step 3: runs 2–3, image check (3d), HYBRID RULE decisions; step 5 memory fixes; step 6 dev run (today, E, the
  selectors within +0.005 s local time) and val; FINISH.

## Numbers so far

- Parser coverage: 88 of 93 booklets complete (64 before); probe routed 90 of 94 (83 before).
