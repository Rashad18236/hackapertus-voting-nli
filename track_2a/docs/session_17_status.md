# Session 17 status (the model-name fallback on HTTP 403, then freeze)

One line per event, UTC. If the session is restarted with "continue", work goes on from "Running".

- **Branch:** `rashad/session-17` from `origin/main` after PR #25 is merged (draft pull request, never merged by
  Claude, no tag).
- **What it is:** `src/llm.py`'s model-name fallback also covers HTTP 403 and an HTTP 400/422 that names the model;
  tests; one verification run; documents. Nothing else changes.
- **Clock:** everything pushed by Thursday 15 October 22:30 UTC.
- **Decisions:** `docs/decisions/2026-10-15-1942_rashad_session-17.md`.

## Done

- (19:42 Thu) The instruction ends with "END OF SESSION 17 INSTRUCTION": complete. dockerd started again.
- (19:44) Step 0: PR #25 checks green but its merge state "dirty": `main` moved after session 16 (Kaan's `5095048`,
  15:51 UTC: plain-language rewrite of the technical report, diagram, four charts, `report.css`, the PDF). Decision
  written: merge `origin/main` into `rashad/session-16`, keep Kaan's text and carry session 16's content into it.
- (19:47) Merge resolved on `rashad/session-16`: `report.css` merged by git (Kaan's figure rule and session 16's
  changes); `technical_report.md` = Kaan's rewrite plus session 16's title, header fields, sealed sentence, §1 sealed
  table, "Who did what", §5 sealed line, §6 "Sealed test dates", "traceable to the booklet", §8 digest and tag line,
  sealed run in the references. To stay within 6 pages: §1's two tables compact, the sealed table's labels shorter,
  the charts slightly narrower (diagram 70 → 65 %, ablation 90 → 70 %, scores 55 → 40 %, fallbacks 60 → 40 %, local
  time 50 → 38 %), body text 10 → 9.5 pt; no number, table or figure removed. PDF 6 pages. Kaan's placeholder
  "Qualitative examples. TODO" (§6) left as he wrote it (his open item; reported).

- (19:48) Checks of the merge: `build_docs.py --check` passes; pytest 357 passed, 1 skipped; numbers check of the
  merged report 395 numbers, 395 found, 0 MISSING; PDF 6 pages.

- (19:53) PR #25 checks green on `790a465` (tests, image); marked ready, merged with a merge commit: `d1513a0`, branch
  kept; `origin/main` contains `7bf5e25`. Branch `rashad/session-17` from `origin/main`; `publish-image.yml` gets
  `rashad/session-17` (tag `session-17`).
- (19:55) Step 1 decisions written; `src/llm.py` changed (`_model_name_refused`, `_replace_model`; (b) first on HTTP
  403 or a 400/422 naming the model); `scripts/stub_llm.py` gets `model_error_message`; tests: 5 in
  `tests/test_llm_fallbacks.py` (class `ModelRefused`; one existing test's expected order updated: a 400 that names the
  model now gets (b) before (a)), 2 in `tests/test_contract.py`. pytest: 364 passed, 1 skipped.
- (19:57) publish-image on `main` (run 109) green: `latest` and `sha-d1513a02e99b`; `latest` pulled with an empty
  Docker configuration: digest `sha256:f368637b98e9369c377a185921bbba86bef2125db6bbd3335ac2da71222a3ea7`, revision
  `d1513a0` (a new build of the same `src/` as the sealed run's `sha256:0c1a10cd…`). CLAUDE.md: session 17 current.

- (19:59) G1/G2 (`scripts/prompt_snapshot.py run --replay` with the session 15 reference's replay table, then
  `compare` against `docs/runs/2026-10-15_rashad_prompt-snapshot-final-s15_devAB-valA`): G1_request_or_path_differs 0,
  G2_label_differs 0, G2_evidence_differs 0 ("G1 pass | G2 pass"); val 580 cases, 592 model calls, all replayed. The
  fake model accepts every model name, so the new fallback never fires there.

## Running

- Step 2: commit, push, publish-image on the branch (tag `session-17`).
