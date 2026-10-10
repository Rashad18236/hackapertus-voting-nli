### 2026-10-09, session 9 reference for the final defaults: request snapshot and replay (no model calls)

- Code: `3e7063d` (`src/` as in `50cb320`; defaults: section-route with `A-v4-section-route-L1`, evidence
  halves, task B `--context-b cut`). Commands (from `track_2a/`): `python3 scripts/prompt_snapshot.py run --out
  <dir>` (fixed fake answers), then `python3 scripts/prompt_snapshot.py table --snapshot snapshot.json --runs
  docs/runs/2026-10-09_rashad_final-defaults_dev600 docs/runs/2026-10-09_rashad_label-errors-confirm_valA580/L1
  --out replay_table.json`, then `python3 scripts/prompt_snapshot.py run --out <this folder> --replay
  replay_table.json`. `.env` never read, no key used.
- `snapshot.json`: per case, the SHA-256 of the whole request body and, for task A, the path: dev 299 routed
  and 1 fallback, val 577 routed and 3 fallbacks (the same paths as the session 8 reference). It equals the
  snapshot of the gate run for the L1 default (`s9_D1`): no code changed in between.
- `replay_table.json`: **1,180** request hashes, every request of both sets, with the answer the final
  defaults got from the real endpoint: dev from `2026-10-09_rashad_final-defaults_dev600` (all 600 cases,
  through the Docker image, 21:22–21:44 UTC), val from the L1 arm of
  `2026-10-09_rashad_label-errors-confirm_valA580` (all 580 cases, 19:28–20:16 UTC; the same task A settings
  as the final defaults). No request has two different saved answers. Unlike the session 8 reference, every
  case is answered from the table (no fixed answers), and task B and all 580 val cases are covered.
- **The replay reproduces the saved answers exactly:** 0 label and 0 evidence differences against the final
  dev run (600) and the val L1 arm (580). The starter's `evaluate.py` on the replay (`scores/`): dev task A
  Macro-F1 0.9799, evidence 0.9801 (197 of 201); task B 0.9666; val task A 0.9606, evidence 0.9576 (384 of
  401).
- **This folder replaces `2026-10-09_rashad_prompt-snapshot_devAB-valA` as the anchor for G1 and G2** from now
  on: `python3 scripts/prompt_snapshot.py run --out <dir> --replay <this folder>/replay_table.json`, then
  `compare --reference <this folder> --new <dir>`. Metrics in `dev/` and `val/` come from the fake model and
  mean nothing.
