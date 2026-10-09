# Task B canary log

`scripts/canary_taskb.py` appends one section per check: the time, the 30
answers to the canary request (v3-topic-first, max_tokens 32, no response_format, temperature 0; cases and baseline in
`docs/canary_taskb.json`), the endpoint identity of each call, and which
earlier results it matches (all 30 answer texts identical). The same results,
machine-readable, are in `docs/canary_results.jsonl`.

Since 2026-10-09 02:00 UTC the canary no longer blocks runs: it runs
immediately before and immediately after each task B run, and if the two
differ, `docs/results.md` marks the run "endpoint changed during run".

The first three sections were written by hand from earlier records, when the
canary did not yet keep a log; their endpoint identity was not recorded.

## 2026-10-09 01:25:24 UTC: baseline

- The answers of run 1 of the task B confirmation
  (`2026-10-09_rashad_v3-topic-first_devB300-run1`, 01:25 to 01:33 UTC); run 2
  (01:33 to 01:36) gave the same 30 texts. 0 failed calls.
- Endpoint identity: not recorded.

| Case | Gold | Answer | Same as the baseline (01:25) |
|---|---|---|---|
| `v1.1-row-134-B` | 0 | `{"label": 0}` | yes |
| `v1.1-row-168-B` | 0 | `{"label": 0}` | yes |
| `v1.1-row-170-B` | 0 | `{"label": 0}` | yes |
| `v1.1-row-180-B` | 0 | `{"label": 0}` | yes |
| `v1.1-row-228-B` | 0 | `{"label": 0}` | yes |
| `v1.1-row-240-B` | 0 | `{"label": 0}` | yes |
| `v1.1-row-260-B` | 0 | `{"label": 0}` | yes |
| `v1.1-row-471-B` | 0 | `{"label": 0}` | yes |
| `v1.1-row-49-B` | 0 | `{"label": 0}` | yes |
| `v1.1-row-80-B` | 0 | `{"label": 0}` | yes |
| `v1.1-row-510-B` | 1 | `{"label": 1}` | yes |
| `v1.1-row-511-B` | 1 | `{"label": 1}` | yes |
| `v1.1-row-549-B` | 1 | `{"label": 1}` | yes |
| `v1.1-row-637-B` | 1 | `{"label": 1}` | yes |
| `v1.1-row-640-B` | 1 | `{"label": 1}` | yes |
| `v1.1-row-767-B` | 1 | `{"label": 2}` | yes |
| `v1.1-row-821-B` | 1 | `{"label": 1}` | yes |
| `v1.1-row-843-B` | 1 | `{"label": 1}` | yes |
| `v1.1-row-869-B` | 1 | `{"label": 2}` | yes |
| `v1.1-row-965-B` | 1 | `{"label": 1}` | yes |
| `v1.1-row-1014-B` | 2 | `{"label": 2}` | yes |
| `v1.1-row-1115-B` | 2 | `{"label": 2}` | yes |
| `v1.1-row-1128-B` | 2 | `{"label": 2}` | yes |
| `v1.1-row-1265-B` | 2 | `{"label": 2}` | yes |
| `v1.1-row-1342-B` | 2 | `{"label": 2}` | yes |
| `v1.1-row-1350-B` | 2 | `{"label": 2}` | yes |
| `v1.1-row-1383-B` | 2 | `{"label": 2}` | yes |
| `v1.1-row-1416-B` | 2 | `{"label": 2}` | yes |
| `v1.1-row-1456-B` | 2 | `{"label": 2}` | yes |
| `v1.1-row-1464-B` | 2 | `{"label": 2}` | yes |

## 2026-10-09 01:50:33 UTC: check before run 1 of the cheap fixes

- From `docs/runs/2026-10-09_rashad_v3-schema_devB300/canary.txt`, which kept
  only the 3 differing answers, cut at 60 characters; the other 27 were
  identical to the baseline. 0 failed calls. The run was not started (the
  canary still blocked runs then).
- Endpoint identity: not recorded.
- **Matches no earlier result.** Closest: 2026-10-09 01:25:24 (27 of 30 identical).

| Case | Gold | Answer | Same as the baseline (01:25) |
|---|---|---|---|
| `v1.1-row-134-B` | 0 | `{"label": 0}` | yes |
| `v1.1-row-168-B` | 0 | `{"label": 0}` | yes |
| `v1.1-row-170-B` | 0 | `{"label": 0}` | yes |
| `v1.1-row-180-B` | 0 | `{"label": 0}` | yes |
| `v1.1-row-228-B` | 0 | `{"label": 0}` | yes |
| `v1.1-row-240-B` | 0 | `{"label": 0}` | yes |
| `v1.1-row-260-B` | 0 | `{"label": 0}` | yes |
| `v1.1-row-471-B` | 0 | `{"label": 0}` | yes |
| `v1.1-row-49-B` | 0 | `{"label": 0}` | yes |
| `v1.1-row-80-B` | 0 | `{"label": 0}` | yes |
| `v1.1-row-510-B` | 1 | `{"label": 1}` | yes |
| `v1.1-row-511-B` | 1 | `{"label": 1}` | yes |
| `v1.1-row-549-B` | 1 | `{"label": 1}` | yes |
| `v1.1-row-637-B` | 1 | `{"label": 1}` | yes |
| `v1.1-row-640-B` | 1 | `{"label": 1}` | yes |
| `v1.1-row-767-B` | 1 | `{"label": 1}` | **no** |
| `v1.1-row-821-B` | 1 | `{"label": 1}` | yes |
| `v1.1-row-843-B` | 1 | `{"label": 1}` | yes |
| `v1.1-row-869-B` | 1 | `{"label": 1}` | **no** |
| `v1.1-row-965-B` | 1 | `{"label": 1}` | yes |
| `v1.1-row-1014-B` | 2 | `{"label": 2}` | yes |
| `v1.1-row-1115-B` | 2 | `{"label": 2}` | yes |
| `v1.1-row-1128-B` | 2 | `{"label": 2}\n**Reasoning:**\nThe reference text explicitly st` (cut at 60 characters in the log) | **no** |
| `v1.1-row-1265-B` | 2 | `{"label": 2}` | yes |
| `v1.1-row-1342-B` | 2 | `{"label": 2}` | yes |
| `v1.1-row-1350-B` | 2 | `{"label": 2}` | yes |
| `v1.1-row-1383-B` | 2 | `{"label": 2}` | yes |
| `v1.1-row-1416-B` | 2 | `{"label": 2}` | yes |
| `v1.1-row-1456-B` | 2 | `{"label": 2}` | yes |
| `v1.1-row-1464-B` | 2 | `{"label": 2}` | yes |

## 2026-10-09 01:51:32 UTC: repeat of the 01:50 check

- From `canary_repeat.txt` in the same folder: the same three differences.
- Endpoint identity: not recorded.
- **Matches the earlier results of 2026-10-09 01:50:33** (all 30 answers
  identical; row 1128 compared on its first 60 characters).
