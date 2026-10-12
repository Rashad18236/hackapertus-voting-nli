### 2026-10-12, session 10 reference for the final defaults: request snapshot and replay (no model calls)

- Code: `29b1485` (`src/` as in `421d8c8`, the code of the published image `sha-421d8c804677`; defaults:
  section-route with `A-v4-section-route-L1` and `json_schema`, evidence halves, vote names by meaning; task B
  `v3-topic-first` with the whole reference; two worker processes, one kept connection). Commands (from
  `track_2a/`): `python3 scripts/prompt_snapshot.py run --out <dir>` (fixed fake answers), then `python3
  scripts/prompt_snapshot.py table --snapshot <dir>/snapshot.json --runs
  docs/runs/2026-10-12_rashad_final-defaults_dev600/task-A docs/runs/2026-10-12_rashad_final-defaults_dev600/task-B
  docs/runs/2026-10-12_rashad_final-defaults_val1160/task-A --out replay_table.json`, then `python3
  scripts/prompt_snapshot.py run --out <this folder> --replay replay_table.json`. `.env` never read, no key used.
- `snapshot.json`: per case, the SHA-256 of the whole request body and, for task A, the path: dev 299 routed and 1
  fallback, val 577 routed and 3 fallbacks. It equals the snapshot of the gate run for the two lanes (`g_lanes`,
  the last change to `src/`). Against the session 9 reference, all 880 task A requests and 195 of 300 task B
  requests are the same; the other 105 are the long task B references, now sent whole (step 2).
- `replay_table.json`: **1,180** request hashes, every request of both sets, with the answer the final defaults got
  from the real endpoint through the published image (`2026-10-12_rashad_final-defaults_dev600`, task A and task B,
  17:19–17:31 UTC; `2026-10-12_rashad_final-defaults_val1160/task-A`, 17:31–17:42 UTC). No request has two
  different saved answers.
- **The replay reproduces the saved answers exactly** (`replay_vs_final_runs.json`): 0 label and 0 evidence
  differences in 1,180 cases. The starter's `evaluate.py` on the replay (`scores/`): dev task A Macro-F1 0.9832,
  evidence 0.9801 (197 of 201); task B 0.9666; val task A 0.9589, evidence 0.9551 (383 of 401).
- **This folder replaces `2026-10-09_rashad_prompt-snapshot-final_devAB-valA` as the anchor for G1 and G2** from
  now on: `python3 scripts/prompt_snapshot.py run --out <dir> --replay <this folder>/replay_table.json`, then
  `compare --reference <this folder> --new <dir>`. Its table is also the default for `scripts/local_time.py`.
  Metrics in `dev/` and `val/` come from the fake model and mean nothing.
