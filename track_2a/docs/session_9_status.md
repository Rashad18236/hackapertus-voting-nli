# Session 9 status

Updated after every phase. If the session is restarted with "continue", work goes on from "Next".

- **Branch:** `rashad/until-1600` from `main` at `418ebfa` (draft pull request, never merged).
- **Clock:** experiments stop at 11:30 UTC on 2026-10-10; everything pushed by 13:00 UTC.

## Done

- (17:07 UTC) Branch created from a fresh `main`; status and decisions files.
- (17:12) A0: PR #14 merged into the branch; gates equal `gates/merge.json`.
- (17:16) A1: `llm.py` fallbacks (refused `response_format`, refused model name), tests against the fake model.
- (17:21) A2: evidence halves kept and switched on (rule passed: G1 and labels unchanged; evidence dev 0.906 → 0.925,
  val 0.946 → 0.956).
- (17:26) A3: dataset README quoted, booklet terms recorded, README section on running with own cases.
- (17:48) A4: stability point 1, all 600 dev cases through the Docker image (`hackapertus-voting-nli:stability`,
  built at `7edbae4`).
- (17:53) Phase C code: `src/taskb_context.py` (B-cut, B-para, off by default), `--context-b`, tests; offline
  tokens per case on 300 dev B: full 1,994, B-cut 1,231 (−38 %), B-para 1,375 (−31 %).

- (18:05) Phase B: `docs/analysis_offline.md` (B1–B6); L2 threshold 0.845 from B6.
- (18:10) Phase D and E code (L1, L2, closed book, section-route top-k), all off by default; gates pass.
- (18:20) Phase C dev run: B-cut 0.967 = current, −38 % tokens (passes); B-para 0.963 (does not replace).
- (19:00) Phase C val run (580 cases): B-cut 0.961 vs 0.957, −37 % tokens: passes.
- (19:10) **Task B default changed to `--context-b cut`** (`13da75a`); G1 differs only in the 105 long dev
  task B requests; labels unchanged; 188 tests.

## Running

- Phase D interleaved run on the 300 dev task A cases (A-current, L1, L2), started 18:56 UTC (resumed 19:00).

## Next

- Phase D: score, apply rules L1 and L2; confirm a passing version on all 580 val task A cases.
- Stability points 2 (about 02:00 UTC) and 3 (about 10:00 UTC): `stability.sh 2|3` with
  `IMAGE=hackapertus-voting-nli:stability`.
- Phase E, then FINISH from 11:30 UTC at the latest.

## Numbers so far

| What | Task A | Task B |
|---|---|---|
| Stability point 1 (600 dev, Docker, 17:28–17:48 UTC) | Macro-F1 0.966, evidence 0.930 (no halves in that image), 1,210 input tokens | Macro-F1 0.967, 3 unreadable, 1,994 input tokens |
| Backends in point 1 | all 300 answers from the blablador vllm backend | all 300 from the same backend |
| A2 replay (E5 / E6 answers) | evidence dev 0.906 → 0.925, val 0.946 → 0.956 | – |
| Phase C dev (300 B, interleaved) | – | current 0.967 / B-cut 0.967 / B-para 0.963; tokens 1,994 / 1,231 / 1,375 |
| Phase C val (580 B, interleaved) | – | current 0.957 / B-cut 0.961; tokens 1,957 / 1,230 |
| B1 bootstrap | dev+val pooled 0.955 (0.938–0.970) | dev 0.967 (0.945–0.986) |
