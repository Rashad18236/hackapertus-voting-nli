### FINISH: all 600 dev cases with the final defaults of session 10, through the published image

**What ran.** The image published by `.github/workflows/publish-image.yml`, pulled from
`ghcr.io/rashad18236/hackapertus-voting-nli:sha-421d8c804677` (built from `421d8c8`; `src/`, `Dockerfile` and
`requirements.txt` unchanged since; id in `task-*/image.txt`), run by `make run` with the organisers' command,
**task A and task B in separate containers** (as the organisers run them), the real endpoint (Public AI,
`swiss-ai/apertus-v1.5-8b` from `.env`), `LLM_MIN_INTERVAL=1`. Task A: the 300 task A lines of
`data/dev/cases.jsonl`, 17:19:11–17:25:13 UTC; task B: its 300 task B lines, 17:25:13–17:30:53 UTC. Both exit 0,
300 responses each.

Final defaults: task A `section-route` with `A-v4-section-route-L1` and `json_schema`, evidence with halves,
vote names by meaning when the title match fails (step 8); task B `v3-topic-first` with the whole reference (no
cut, step 2), max_tokens 32, no schema; two worker processes ("lanes") prepare the cases, one kept connection.

**Scores** (the starter's `evaluate.py`: `task-*/official_score.json`, `.txt`; calls: `calls_summary.json`):

| Task | Macro-F1 | F1 E / N / C | Evidence | Neutral fallbacks | Input + output tokens per case | Mean / p95 time per case |
|---|---|---|---|---|---|---|
| A (300) | **0.983** | 0.985 / 0.990 / 0.974 | **0.980** (197/201) | 0 | 1,237.8 + 14.5 | 2.0 / 4.9 s |
| B (300) | **0.967** | 0.985 / 0.963 / 0.951 | not scored | 3 | 1,994.2 + 8.4 | 1.1 / 2.1 s |

- **Paths (task A):** 299 routed (council 102, summary 67, committee 48, detail 43, law 39), 1 fallback to
  `embed-e5-small`.
- **Neutral fallbacks:** the only labels Python wrote are 3 task B answers it could not read (a bare `1`, and two
  answers that began with an explanation in English instead of the JSON object); each became neutral.
- **Endpoint:** all 600 answers from one backend (blablador, `vllm-0.23.1rc1…dd237840`); 0 failed calls, 0
  retries, 0 HTTP 429, no gateway cache hits.
- **Compared with what (different runs, indicative only):** "today" scored task A 0.980 and 0.983 in the step 5
  and step 6 dev runs, and task B 0.967 with 1,994 input tokens in step 5. Every default of this image was adopted
  by its own rule (an interleaved run, or the same-answer gates G1/G2 with measured local time), not on this run.

These answers (task A and task B) and the val task A answers (`2026-10-12_rashad_final-defaults_val1160`) are
the saved answers of the new replay reference `2026-10-12_rashad_prompt-snapshot-final-s10_devAB-valA`.

**Local time of the same image** (`scripts/local_time.py`, `local_time_dev*_d*.json`, measured 18:06–18:53 UTC after
one warm-up run, nothing else running): the published image with the organisers' command, 2 CPUs, 4 GB, read-only,
against the fake model replaying the final runs' answers (`2026-10-12_rashad_prompt-snapshot-final-s10_devAB-valA`)
after 1.0 s or 0.3 s.

| Task | 1.0 s per request: local time per case (in all) | 0.3 s per request | replay misses | peak memory (1.0 s) |
|---|---|---|---|---|
| A | 0.0171 s (5.1 s; first request 3.0 s) | 0.1538 s (46.1 s; first request 2.9 s) | 0 | 2308 MiB |
| B | 0.0100 s (3.0 s; first request 1.8 s) | 0.0068 s (2.0 s; first request 0.9 s) | 0 | 58 MiB |

**REF SCORE** (`ref_score.json`, `scripts/official_score.py`; tokens = input + output; Macro-F1 and evidence from
this run):

| | T_A | K_A | S_A | T_B | K_B | S_B | REF SCORE |
|---|---|---|---|---|---|---|---|
| 1.0 s per request | 1.000 | 0.479 | 0.909 | 0.500 | 0.400 | 0.811 | **0.870** |
| 0.3 s per request | 0.325 | 0.479 | 0.808 | 0.735 | 0.400 | 0.847 | **0.824** |
