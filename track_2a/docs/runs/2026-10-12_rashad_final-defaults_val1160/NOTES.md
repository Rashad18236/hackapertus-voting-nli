### FINISH: all 580 val task A and 580 val task B cases with the final defaults of session 10, through the published image

**What ran.** The same published image as `2026-10-12_rashad_final-defaults_dev600`
(`ghcr.io/rashad18236/hackapertus-voting-nli:sha-421d8c804677`, built from `421d8c8`), `make run` with the
organisers' command, task A and task B in separate containers, Public AI `swiss-ai/apertus-v1.5-8b`,
`LLM_MIN_INTERVAL=1`. Task A: `data/val/cases.jsonl` (580 cases), 17:30:53–17:41:59 UTC; task B:
`output/valB/cases.jsonl` (the task B cases of the same 580 val rows), 17:41:59–17:53:35 UTC. Both exit 0, 580
responses each. Val is for confirming only: no pattern, rule or threshold was written because of a val case.

**Scores** (the starter's `evaluate.py`: `task-*/official_score.json`, `.txt`; calls: `calls_summary.json`):

| Task | Macro-F1 | F1 E / N / C | Evidence | Neutral fallbacks | Input + output tokens per case | Mean / p95 time per case |
|---|---|---|---|---|---|---|
| A (580) | **0.959** | 0.976 / 0.955 / 0.946 | **0.955** (383/401) | 0 | 1,205.8 + 14.5 | 1.7 / 4.5 s |
| B (580) | **0.961** | 0.984 / 0.951 / 0.947 | not scored | 3 | 1,957.2 + 9.0 | 1.2 / 2.1 s |

- **Paths (task A):** 577 routed (council 175, summary 139, committee 102, law 87, detail 74), 3 fallbacks to
  `embed-e5-small`.
- **Neutral fallbacks:** 3 task B answers could not be read (a bare `1`, and two explanations in English
  without the JSON object); each became neutral. Task A: none.
- **Endpoint:** all 1,160 answers from one backend (blablador, `vllm-0.23.1rc1…dd237840`); 0 failed calls; one
  HTTP 502 (row 118, task A) answered on its retry; 0 HTTP 429; no gateway cache hits.
- **Compared with what (different runs, indicative only):** "today" of the step 5 and step 6 val runs scored task
  A 0.959 (evidence 0.955 and 0.958) and task B 0.957.

The task A answers are saved answers of the new replay reference `2026-10-12_rashad_prompt-snapshot-final-s10_devAB-valA`
(with the dev run's 600).

**Local time of the same image** (`scripts/local_time.py`, `local_time_val*_d*.json`, measured 18:06–18:53 UTC after
one warm-up run, nothing else running): the published image with the organisers' command, 2 CPUs, 4 GB, read-only,
against the fake model replaying the final runs' answers (`2026-10-12_rashad_prompt-snapshot-final-s10_devAB-valA`)
after 1.0 s or 0.3 s. The replay table holds dev's and val task A's answers only; where it has none (task B) the fake model gives its fixed answer, which changes the evidence built but not the local work that counts (the same requests, one per case).

| Task | 1.0 s per request: local time per case (in all) | 0.3 s per request | replay misses | peak memory (1.0 s) |
|---|---|---|---|---|
| A | 0.0116 s (6.7 s; first request 2.7 s) | 0.0335 s (19.4 s; first request 2.0 s) | 0 | not measured |
| B | 0.0069 s (4.0 s; first request 1.7 s) | 0.0052 s (3.0 s; first request 0.8 s) | 580 | not measured |

**REF SCORE** (`ref_score.json`, `scripts/official_score.py`; tokens = input + output; Macro-F1 and evidence from
this run):

| | T_A | K_A | S_A | T_B | K_B | S_B | REF SCORE |
|---|---|---|---|---|---|---|---|
| 1.0 s per request | 1.000 | 0.492 | 0.894 | 0.725 | 0.407 | 0.842 | **0.873** |
| 0.3 s per request | 1.000 | 0.492 | 0.894 | 0.962 | 0.407 | 0.878 | **0.888** |

With dev's local times instead (as `main`'s val REF SCORE was computed in step 1): 0.860 / 0.813. Local time per case is lower on val because the start (about 1–3 s) is shared by 580 cases and each booklet's reading by more cases.
