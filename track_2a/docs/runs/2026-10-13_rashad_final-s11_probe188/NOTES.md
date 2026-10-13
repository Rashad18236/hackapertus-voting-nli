### FINISH: the probe (94 test rows of 2021-03-07 and 2025-09-28, task A and task B) with the final defaults of session 11

Same image, command and settings as `2026-10-13_rashad_final-s11_dev600` (`sha-bb2d08fea0f1`). Task A:
`output/probeA/cases.jsonl` (booklets in `output/booklets_probe`), 02:48–02:50 UTC; task B: `output/probeB/cases.jsonl`,
02:50–02:51 UTC. Both exit 0, 94 responses each. The other three test dates stay sealed.

| Task | Macro-F1 | F1 E / N / C | Evidence | Neutral fallbacks | Input + output tokens per case |
|---|---|---|---|---|---|
| A (94) | **0.971** | 1.000 / 0.949 / 0.965 | **0.954** (62/65) | 0 | 1,135.5 + 14.5 |
| B (94) | **0.977** | 0.977 / 0.966 / 0.989 | not scored | 0 | 788.7 + 8.9 |

- **Paths (task A):** 90 routed (session 10: 83), 4 to embed-e5-small: the rules route these claims to the committee,
  and their votes of 2025-09-28 have no committee part; Apertus is not asked (the rules named a part).
- **Endpoint:** all 188 answers from one backend; 0 failed calls, 0 retries.
- **Before (session 10's final image, `2026-10-12_rashad_final-defaults_probe188`, a different run):** task A 0.960,
  evidence 0.908 (59/65), task B 0.971 with 1,831 + 8.3 tokens. Step 1's parser fixes (the first vote of
  `2025_09_28_fr`) and task B's selector T account for the changes.

**Local time** (`local_time_probe*_d*.json`; no saved answers in the replay table for the probe, so every request gets
the fake model's fixed answer; the local work does not depend on it): task A 0.026 / 0.237 s per case at 1.0 / 0.3 s
(six booklets for 94 cases: each booklet's reading and embedding is shared by few cases), task B 0.015 / 0.015 s.
**REF SCORE** (`ref_score.json`): **0.897 / 0.825** (session 10: 0.850 / 0.777).
