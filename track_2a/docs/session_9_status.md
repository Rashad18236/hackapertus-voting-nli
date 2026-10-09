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

## Running

- Phase C interleaved run on the 300 dev task B cases (B-current, B-cut, B-para), started 17:53 UTC.
- Phase B offline analyses (`scripts/analysis_offline.py`).

## Next

- Phase C: score the dev run, apply the rule; if B-cut (or B-para) passes, confirm on the 580 val task B cases
  (`output/valB`, built by `scripts/make_val_b.py`).
- Phase B: write `docs/analysis_offline.md` (B1–B6); B6 decides whether L2 has a threshold.
- Phase D: L1 and L2 code, interleaved run on 300 dev task A, val confirmation.
- Stability points 2 (about 02:00 UTC) and 3 (about 10:00 UTC): `stability.sh 2|3` with
  `IMAGE=hackapertus-voting-nli:stability`.
- Phase E, then FINISH from 11:30 UTC at the latest.

## Numbers so far

| What | Task A | Task B |
|---|---|---|
| Stability point 1 (600 dev, Docker, 17:28–17:48 UTC) | Macro-F1 0.966, evidence 0.930 (no halves in that image), 1,210 input tokens | Macro-F1 0.967, 3 unreadable, 1,994 input tokens |
| Backends in point 1 | all 300 answers from the blablador vllm backend | all 300 from the same backend |
| A2 replay (E5 / E6 answers) | evidence dev 0.906 → 0.925, val 0.946 → 0.956 | – |
