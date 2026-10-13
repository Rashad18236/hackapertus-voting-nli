### FINISH: all 600 dev cases with the final defaults of session 11, through the published image

**What ran.** The image published by `.github/workflows/publish-image.yml`, pulled from
`ghcr.io/rashad18236/hackapertus-voting-nli:sha-bb2d08fea0f1` (built from `bb2d08f`, also tagged `session-11` at
the time; `src/` unchanged since; id in `task-*/image.txt`), run by `make run` with the organisers' command, **task A
and task B in separate containers**, the real endpoint (Public AI, `swiss-ai/apertus-v1.5-8b` from `.env`),
`LLM_MIN_INTERVAL=1`. Task A: the 300 task A lines of `data/dev/cases.jsonl`, 02:15–02:21 UTC; task B: its 300 task B
lines, 02:21–02:27 UTC. Both exit 0, 300 responses each.

Final defaults: task A `section-route` with `A-v4-section-route-L1` and `json_schema`, AP-part after the rules,
evidence with halves, vote names by meaning; task B `v3-topic-first`, a reference over 3,000 characters cut to its
first line and the 4 paragraphs chosen by selector T, max_tokens 32; light-first lanes, lazy page reading, shared
onnxruntime threads, one lane under a 2.5 GiB memory limit, one kept connection.

**Scores** (the starter's `evaluate.py`: `task-*/official_score.*`; calls: `calls_summary.json`):

| Task | Macro-F1 | F1 E / N / C | Evidence | Neutral fallbacks | Input + output tokens per case |
|---|---|---|---|---|---|
| A (300) | **0.980** | 0.976 / 0.995 / 0.969 | **0.985** (198/201) | 0 | 1,237.8 + 14.5 |
| B (300) | **0.987** | 0.985 / 0.995 / 0.980 | not scored | 0 | 815.3 + 8.7 |

- **Paths (task A):** 299 routed (council 102, summary 67, committee 48, detail 43, law 39), 1 to embed-e5-small. No
  case asked Apertus for its part (the rules name one for every claim).
- **Endpoint:** all 600 answers from one backend (blablador, `vllm-0.23.1rc1`); 0 failed calls, 0 retries, 0 HTTP
  429, no gateway cache hits.
- **Session 10's final image on the same dev cases** (`2026-10-12_rashad_final-defaults_dev600`, a different run):
  task A 0.983 / 0.980 with the same 1,238 + 14.5 tokens; task B 0.967 with 1,994 + 8.4.

These answers and the val task A answers are the saved answers of the new replay reference
`2026-10-13_rashad_prompt-snapshot-final-s11_devAB-valA` (the replay reproduces them exactly).

**Local time of the same image** (`scripts/local_time.py`, `local_time_dev*_d*.json`, 03:00–03:12 UTC after one
warm-up run, nothing else running, 2 CPUs pinned to CPUs 2–3, 4 GB, fake model replaying these answers):

| Task | 1.0 s per request | 0.3 s | 0.1 s | replay misses | peak memory (1.0 s) |
|---|---|---|---|---|---|
| A | 0.018 s per case | 0.155 s (a repeat at 03:46: 0.108 s) | 0.316 s | 0 | 2,287 MiB |
| B | 0.0104 s | 0.0093 s | 0.130 s | 0 | 1,673 MiB |

The two task A values at 0.3 s show how much one measurement varies. Under the same conditions on CPUs 0–1
(`local_time_same_conditions/`), session 10's image needs 0.223 s per case at 0.3 s and this image 0.129 s (0.123 s
with e5's files mounted from the host).

**REF SCORE** (`ref_score.json`; reference "best" values 600 / 800 tokens, 0.05 / 0.005 s): **0.909** at 1.0 s per
request (S_A 0.909, S_B 0.908), **0.851** at 0.3 s (0.864 with the repeat measurement), 0.806 at 0.1 s. Session 10:
0.870 / 0.824 (different runs).

**Memory of the final image** (the grid of step 5 on this image, `memory_final.txt`): task A
answers every case at 2 GiB and 1.5 GiB with 2 CPUs and with 1 CPU, not at 1 GiB; task B (selector T loads e5 for long
references) at 1.5 GiB, not at 1 GiB.
