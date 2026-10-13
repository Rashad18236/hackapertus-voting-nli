### 2026-10-13, session 11 reference for the final defaults: request snapshot and replay (no model calls)

- Code: `src/` as in `bb2d08f`, the code of the published image `sha-bb2d08fea0f1` (defaults: section-route with
  `A-v4-section-route-L1` and `json_schema`, evidence halves, vote names by meaning, AP-part after the rules; task B
  `v3-topic-first` with selector T for references over 3,000 characters; light-first lanes, lazy pages, shared
  onnxruntime threads, one lane under 2.5 GiB; one kept connection). Commands (from `track_2a/`):
  `python3 scripts/prompt_snapshot.py run --out <dir>` (fixed fake answers), then `python3 scripts/prompt_snapshot.py
  table --snapshot <dir>/snapshot.json --runs docs/runs/2026-10-13_rashad_final-s11_dev600/task-A
  docs/runs/2026-10-13_rashad_final-s11_dev600/task-B docs/runs/2026-10-13_rashad_final-s11_val1160/task-A --out
  replay_table.json`, then `python3 scripts/prompt_snapshot.py run --out <this folder> --replay replay_table.json`.
  `.env` never read, no key used.
- `snapshot.json`: per case, the SHA-256 of the whole request body (and of any parsing call, `ap_request_sha256`;
  none in these sets) and, for task A, the path: dev 299 routed and 1 fallback, val 577 routed and 3 fallbacks.
  Against the session 10 reference, all 880 task A requests and 82 of 300 task B requests are the same; the other 218
  are the long task B references, now cut by selector T (step 6).
- `replay_table.json`: **1,180** request hashes, every request of both sets, with the answer the final defaults got
  from the real endpoint through the published image (`2026-10-13_rashad_final-s11_dev600`, task A and task B;
  `2026-10-13_rashad_final-s11_val1160/task-A`). No request has two different saved answers.
- **The replay reproduces the saved answers exactly** (`replay_vs_final_runs.json`): 0 label and 0 evidence
  differences in 1,180 cases. The starter's `evaluate.py` on the replay (`scores/`): dev task A Macro-F1 0.9800,
  evidence 0.9851 (198 of 201); task B 0.9867; val task A 0.9589, evidence 0.9551 (383 of 401).
- **This folder replaces `2026-10-12_rashad_prompt-snapshot-final-s10_devAB-valA` as the anchor for G1 and G2** from
  now on: `python3 scripts/prompt_snapshot.py run --out <dir> --replay <this folder>/replay_table.json`, then
  `compare --reference <this folder> --new <dir>`. Metrics in `dev/` and `val/` come from the fake model and mean
  nothing.
