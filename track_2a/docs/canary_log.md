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

## 2026-10-09 02:11:06 UTC: before the four-arm run `2026-10-09_rashad_taskb-4arm_devB300`

- 30 calls (v3-topic-first, max_tokens 32, no response_format, temperature 0), 0 failed, 0 answered HTTP 429 first.
- Endpoint identity: the same in all calls:

  - 30 calls: `{"cf_ray_datacentre": "IAD", "headers": {"cf-placement": "remote-MXP", "llm_provider-server": "openresty/1.27.1.2", "server": "cloudflare", "x-litellm-attempted-fallbacks": "0", "x-litellm-attempted-retries": "0", "x-litellm-model-api-base": "https://api.blablador.fz-juelich.de/v1", "x-litellm-model-group": "swiss-ai/apertus-v1.5-8b", "x-litellm-model-id": "8c4216b403b79005fdefac315cf65b2320c880e4b6822877ebc8a613af2962ca", "x-litellm-model-name": "openai/alias-apertus", "x-litellm-version": "1.98.0"}, "model": "swiss-ai/apertus-v1.5-8b", "system_fingerprint": "vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840"}`

- **Matches no earlier result.** Closest: 2026-10-09 01:50:33 (29 of 30 identical), 2026-10-09 01:51:32 (29 of 30 identical), 2026-10-09 01:25:24 (26 of 30 identical).

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
| `v1.1-row-1014-B` | 2 | `{"label": 2}\n**Reasoning:**\nThe reference text explicitly states: "Während die Verrechnungssteuer für die Stimmberechtigten bestehen` | **no** |
| `v1.1-row-1115-B` | 2 | `{"label": 2}` | yes |
| `v1.1-row-1128-B` | 2 | `{"label": 2}\n**Reasoning:**\nThe reference text explicitly states: "Für Schweizer Frauen ist der Dienst in der Armee oder im Zivilschutz freiwill` | **no** |
| `v1.1-row-1265-B` | 2 | `{"label": 2}` | yes |
| `v1.1-row-1342-B` | 2 | `{"label": 2}` | yes |
| `v1.1-row-1350-B` | 2 | `{"label": 2}` | yes |
| `v1.1-row-1383-B` | 2 | `{"label": 2}` | yes |
| `v1.1-row-1416-B` | 2 | `{"label": 2}` | yes |
| `v1.1-row-1456-B` | 2 | `{"label": 2}` | yes |
| `v1.1-row-1464-B` | 2 | `{"label": 2}` | yes |

## 2026-10-09 02:39:43 UTC: after the four-arm run `2026-10-09_rashad_taskb-4arm_devB300`

- 30 calls (v3-topic-first, max_tokens 32, no response_format, temperature 0), 0 failed, 0 answered HTTP 429 first.
- Endpoint identity: 3 different identities:

  - 19 calls: `{"cf_ray_datacentre": "IAD", "headers": {"cf-placement": "remote-MXP", "llm_provider-server": "openresty/1.27.1.2", "server": "cloudflare", "x-litellm-attempted-fallbacks": "0", "x-litellm-attempted-retries": "0", "x-litellm-model-api-base": "https://api.blablador.fz-juelich.de/v1", "x-litellm-model-group": "swiss-ai/apertus-v1.5-8b", "x-litellm-model-id": "8c4216b403b79005fdefac315cf65b2320c880e4b6822877ebc8a613af2962ca", "x-litellm-model-name": "openai/alias-apertus", "x-litellm-version": "1.98.0"}, "model": "swiss-ai/apertus-v1.5-8b", "system_fingerprint": "vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840"}`
  - 10 calls: `{"cf_ray_datacentre": "IAD", "headers": {"cf-placement": "remote-MXP", "server": "cloudflare", "x-litellm-attempted-fallbacks": "0", "x-litellm-attempted-retries": "0", "x-litellm-model-api-base": "https://api.blablador.fz-juelich.de/v1", "x-litellm-model-group": "swiss-ai/apertus-v1.5-8b", "x-litellm-model-id": "8c4216b403b79005fdefac315cf65b2320c880e4b6822877ebc8a613af2962ca", "x-litellm-model-name": "openai/alias-apertus", "x-litellm-version": "1.98.0"}, "model": "swiss-ai/apertus-v1.5-8b", "system_fingerprint": "vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840"}`
  - 1 calls: `{"cf_ray_datacentre": "IAD", "headers": {"cf-placement": "remote-MXP", "server": "cloudflare", "x-litellm-attempted-fallbacks": "0", "x-litellm-attempted-retries": "0", "x-litellm-model-api-base": "https://api.blablador.fz-juelich.de/v1", "x-litellm-model-group": "swiss-ai/apertus-v1.5-8b", "x-litellm-model-id": "8c4216b403b79005fdefac315cf65b2320c880e4b6822877ebc8a613af2962ca", "x-litellm-model-name": "openai/alias-apertus", "x-litellm-version": "1.98.0"}, "model": "swiss-ai/apertus-v1.5-8b", "system_fingerprint": "fp1-nst-nes"}`

- **Matches no earlier result.** Closest: 2026-10-09 01:50:33 (29 of 30 identical), 2026-10-09 01:51:32 (29 of 30 identical), 2026-10-09 02:11:06 (28 of 30 identical). (Corrected by hand: the script first wrote "matches 01:50:33 and 01:51:32", because it let row 1128's short answer match the 60-character start kept from 01:50; fixed in `scripts/canary_taskb.py`.)

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
| `v1.1-row-1128-B` | 2 | `{"label": 2}\n` | **no** |
| `v1.1-row-1265-B` | 2 | `{"label": 2}` | yes |
| `v1.1-row-1342-B` | 2 | `{"label": 2}` | yes |
| `v1.1-row-1350-B` | 2 | `{"label": 2}` | yes |
| `v1.1-row-1383-B` | 2 | `{"label": 2}` | yes |
| `v1.1-row-1416-B` | 2 | `{"label": 2}` | yes |
| `v1.1-row-1456-B` | 2 | `{"label": 2}` | yes |
| `v1.1-row-1464-B` | 2 | `{"label": 2}` | yes |

**Note on the two checks of 02:11 and 02:39 (added by hand after the run).**
Public AI's gateway answers a request identical to one sent in the last ~10
minutes from its cache, and the canary request is the same as arm A's of the
run. So 11 of the 30 answers at 02:39 are copies of the run's arm A answers
(sent 02:30 to 02:39), among them both differing rows: row 1014 was written
by the featherless backend, row 1128 by the blablador backend, both without
the reasoning paragraph of 02:11; the labels are the same. 12 of the run's
arm A answers are likewise copies of the 02:11 answers. The canary script
records these cache hits since this run. The answers of 02:11 all came from
the blablador backend; how the backends' answers differ is in
`docs/runs/2026-10-09_rashad_taskb-4arm_devB300/NOTES.md`.
