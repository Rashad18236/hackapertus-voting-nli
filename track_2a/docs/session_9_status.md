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

- (19:27) Phase D dev run: L1 0.980 vs 0.966 (passes on dev), L2 0.976 (fails its +0.015 bar).
- (20:16) Phase D val run (580 cases): L1 0.961 vs 0.950, neutral recall 1.000: passes.
- (20:58) **Task A default changed to L1** (`label_rule_a`, prompt `A-v4-section-route-L1`; `50cb320`).
- (20:50) E1 context curve (100 dev): whole booklet 0.858 / embed 0.898 / section-route 0.989 / top-4 0.979 /
  top-2 0.940 / top-1 0.769.
- (21:09) E2 closed book 0.435 vs section-route 0.980 (300 dev).
- (21:22) E3 Apertus as router: 278/300 agree with the rules (dev); stress 283 vs 285 right, 17 vs 0 wrong part.
- (21:20) Final image `hackapertus-voting-nli:final` built at `50cb320` (defaults: B-cut, L1, halves).

- (21:44) FINISH final run: all 600 dev cases with the final defaults through the image: task A 0.980
  (evidence 0.980), task B 0.967.
- (21:56) New replay reference `2026-10-09_rashad_prompt-snapshot-final_devAB-valA` (1,180 saved real
  answers, replay exact); CLAUDE.md session 9; 189 tests pass.
- (22:05) Technical report (6 pages PDF) and session report drafted; only the stability points 2 and 3 are
  missing from them.

- (02:18) Stability point 2: task A 0.966 (evidence 0.935), task B 0.967; labels agree with point 1 in
  299/300 (A) and 300/300 (B); one backend.

- (10:16) Stability point 3: task A 0.966 (evidence 0.930), task B 0.963; labels equal to point 1 in 300/300 (A)
  and 299/300 (B); over the three points two of 600 labels ever changed; one backend.

## Running

- nothing (all model runs done).

## Next

- FINISH texts: rebuild `technical_report.pdf` (≤ 6 pages), tests, CI green on the last commit, push by 13:00.

## Numbers so far

| What | Task A | Task B |
|---|---|---|
| Stability point 1 (600 dev, Docker, 17:28–17:48 UTC) | Macro-F1 0.966, evidence 0.930 (no halves in that image), 1,210 input tokens | Macro-F1 0.967, 3 unreadable, 1,994 input tokens |
| Backends in point 1 | all 300 answers from the blablador vllm backend | all 300 from the same backend |
| A2 replay (E5 / E6 answers) | evidence dev 0.906 → 0.925, val 0.946 → 0.956 | – |
| Phase C dev (300 B, interleaved) | – | current 0.967 / B-cut 0.967 / B-para 0.963; tokens 1,994 / 1,231 / 1,375 |
| Phase C val (580 B, interleaved) | – | current 0.957 / B-cut 0.961; tokens 1,957 / 1,230 |
| B1 bootstrap | dev+val pooled 0.955 (0.938–0.970) | dev 0.967 (0.945–0.986) |
| Phase D dev (300 A, interleaved) | current 0.966 / L1 0.980 / L2 0.976; tokens 1,210 / 1,238 / 1,244 | – |
| Phase D val (580 A, interleaved) | current 0.950 / L1 0.961 / L2 0.954; tokens 1,178 / 1,206 / 1,217 | – |
| E1 (100 dev A) | full 0.858 (37.6k tokens), section-route 0.989 (1.2k) | – |
| E2 (300 dev A) | closed book 0.435, section-route 0.980 | – |
| Final defaults (600 dev, Docker, 21:22–21:44 UTC) | 0.980, evidence 0.980, 1,238 tokens | 0.967, 1,231 tokens |
| Stability point 2 (600 dev, Docker, 01:56–02:18 UTC) | 0.966, evidence 0.935, 1,210 tokens | 0.967, 4 unreadable, 1,994 tokens |
| Stability point 3 (600 dev, Docker, 09:56–10:16 UTC) | 0.966, evidence 0.930, 1,210 tokens | 0.963, 1 unreadable, 1,994 tokens |
