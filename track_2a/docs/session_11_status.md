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

- (23:53) Step 3 run 2 (150 reworded dev openings): AP-part 0.967 / 0.880 vs VW 0.894 / 0.670 vs today 0.906 / 0.700;
  **passes the HYBRID RULE on dev** (+0.073); AP-part rebuilt for the worker processes (off; G1/G2 pass, 271 tests).
- (00:10) Step 6a timings (task B, local time per case at 1.0 / 0.3 / 0.1 s): full 0.0067 / 0.0066 / 0.0067; L 0.0065 /
  0.0066 / 0.0067; H 0.0072 / 0.0082 / 0.059; E 0.011 / 0.661. Agreement with E's 4 paragraphs (mean of 3.81): Q 3.36,
  T 3.06, H 2.78, L 2.03.

- (00:38) Step 3 run 3 (parser off, dev 300): AP-structure 0.970 / 0.955 vs VW 0.886 / 0.687; not adoptable (part a
  78.7 % < 95 %). Step 3d image check: accepted, heading not read.
- (01:09) Step 3, AP-part on 150 reworded val openings: 0.926 / 0.840 vs VW 0.876 / 0.650 (+0.051): **AP-part after the
  rules adopted** (b223653; G1/G2 pass, no dev or val case asks).
- (01:29) Step 5: before, task A needed 3 GiB with 2 CPUs (2 GiB: OOM); **one lane under 2.5 GiB adopted** (b9c1189):
  all responses, same labels at 2 GiB and 1.5 GiB; 1 GiB fails (e5 load peak 1.16 GiB). Task B runs in 1 GiB.
- Step 6a timings at 1.0 / 0.3 s: T 0.0077 / 0.0089 and H 0.0072 / 0.0082 pass (+0.005), E and Q fail at 0.3 s.

## Running

- Step 6 dev run (from 01:10): today, E, T, H on 300 dev task B cases; then val (today and the best) if one passes.
- CPUs 2–3: AP-all's local time (replay of run 1).

## Next

- Step 6 decision and val; FINISH: push, final runs through the image `session-11`, local time at 1.0 / 0.3 / 0.1 s,
  memory, REF SCORE, new replay reference, reports.

## Numbers so far

- Parser coverage: 88 of 93 booklets complete (64 before); probe routed 90 of 94 (83 before).
