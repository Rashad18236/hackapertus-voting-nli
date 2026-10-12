### FINISH: the probe (94 task A and 94 task B cases) with the final defaults of session 10, through the published image

**What ran.** The same published image as `2026-10-12_rashad_final-defaults_dev600`
(`ghcr.io/rashad18236/hackapertus-voting-nli:sha-421d8c804677`, built from `421d8c8`), `make run` with the
organisers' command, task A and task B in separate containers, Public AI `swiss-ai/apertus-v1.5-8b`,
`LLM_MIN_INTERVAL=1`. Task A: `output/probeA/cases.jsonl`, 17:53:35–17:55:30 UTC; task B: `output/probeB/cases.jsonl`,
17:55:30–17:57:29 UTC. Both exit 0, 94 responses each. The probe is the test rows of 2021-03-07 and 2025-09-28
(`data/probe/`, session 10 step 4); the other three test dates stay sealed.

**Scores** (the starter's `evaluate.py`: `task-*/official_score.json`, `.txt`; calls: `calls_summary.json`):

| Task | Macro-F1 | F1 E / N / C | Evidence | Neutral fallbacks | Input + output tokens per case | Mean / p95 time per case |
|---|---|---|---|---|---|---|
| A (94) | **0.960** | 0.978 / 0.949 / 0.952 | **0.908** (59/65) | 0 | 1,232.2 + 14.4 | 2.0 / 2.9 s |
| B (94) | **0.971** | 1.000 / 0.945 / 0.966 | not scored | 0 | 1,830.5 + 8.3 | 1.3 / 2.1 s |

- **Paths (task A):** 83 routed, 11 fallbacks to `embed-e5-small` (8 in `2025_09_28_fr`, whose first vote the
  parser does not find; 3 committee claims on a vote without a committee part), as in step 4.
- **Errors:** task A the same 4 as in step 4 (rows 763, 1453, 1058, 1176); task B 3 (rows 644, 763, 918: neutral
  claims called a contradiction); row 536 (task B), wrong in step 4, is right here. What was sent equals step 4's
  in every case (same paths, paragraphs, pages and input tokens: vote names by meaning place no probe vote
  differently, and the lanes change no request); the endpoint answered 3 of 188 requests differently: row 536-B's label, and the cited paragraphs of rows 1044-A and 379-A (evidence
  changed, both still cite the gold passage: evidence 59 of 65 in both runs).
- **Endpoint:** all 188 answers from one backend (blablador); 0 failed calls, 0 unreadable answers, so 0
  neutral-fallback labels.

**Local time of the same image** (`scripts/local_time.py`, `local_time_probe*_d*.json`, measured 18:06–18:53 UTC after
one warm-up run, nothing else running): the published image with the organisers' command, 2 CPUs, 4 GB, read-only,
against the fake model replaying the final runs' answers (`2026-10-12_rashad_prompt-snapshot-final-s10_devAB-valA`)
after 1.0 s or 0.3 s. The replay table holds dev's and val task A's answers only; where it has none (task A, task B) the fake model gives its fixed answer, which changes the evidence built but not the local work that counts (the same requests, one per case).

| Task | 1.0 s per request: local time per case (in all) | 0.3 s per request | replay misses | peak memory (1.0 s) |
|---|---|---|---|---|
| A | 0.0385 s (3.6 s; first request 2.9 s) | 0.2485 s (23.4 s; first request 3.3 s) | 94 | not measured |
| B | 0.0138 s (1.3 s; first request 0.8 s) | 0.0142 s (1.3 s; first request 0.9 s) | 94 | not measured |

**REF SCORE** (`ref_score.json`, `scripts/official_score.py`; tokens = input + output; Macro-F1 and evidence from
this run):

| | T_A | K_A | S_A | T_B | K_B | S_B | REF SCORE |
|---|---|---|---|---|---|---|---|
| 1.0 s per request | 1.000 | 0.481 | 0.884 | 0.362 | 0.435 | 0.799 | **0.850** |
| 0.3 s per request | 0.201 | 0.481 | 0.764 | 0.352 | 0.435 | 0.797 | **0.777** |
