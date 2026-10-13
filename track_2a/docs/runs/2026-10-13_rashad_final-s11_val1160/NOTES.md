### FINISH: all 580 val rows (task A and task B) with the final defaults of session 11, through the published image

Same image, command and settings as `2026-10-13_rashad_final-s11_dev600` (`sha-bb2d08fea0f1`, task A and task B in
separate containers, real endpoint, `LLM_MIN_INTERVAL=1`). Task A: `data/val/cases.jsonl`, 02:26–02:37 UTC; task B:
`output/valB/cases.jsonl`, 02:37–02:48 UTC. Both exit 0, 580 responses each.

| Task | Macro-F1 | F1 E / N / C | Evidence | Neutral fallbacks | Input + output tokens per case |
|---|---|---|---|---|---|
| A (580) | **0.959** | 0.976 / 0.955 / 0.946 | **0.955** (383/401) | 0 | 1,205.8 + 14.5 |
| B (580) | **0.968** | 0.982 / 0.963 / 0.958 | not scored | 1 | 819.5 + 9.3 |

- **Paths (task A):** 577 routed, 3 to embed-e5-small; no case asked Apertus for its part.
- **Neutral fallback:** the only label Python wrote is 1 task B answer it could not read.
- **Endpoint:** all 1,160 answers from one backend (blablador, `vllm-0.23.1rc1`); 0 failed calls, 0 retries, 0 HTTP 429.
- **Session 10's final image** (`2026-10-12_rashad_final-defaults_val1160`, a different run): task A 0.959 / 0.955,
  task B 0.961 with 1,957 + 9.0 tokens.

**Local time of the same image** (`local_time_val*_d*.json`; 2 CPUs, 4 GB; the replay table holds the val task A
answers; task B's requests are not in it and get the fake model's fixed answer, which does not change the local
work): task A 0.0083 / 0.0103 s per case at 1.0 / 0.3 s per request, task B 0.0070 / 0.0074 s. **REF SCORE**
(`ref_score.json`): **0.908 / 0.906** (session 10: 0.873 / 0.888).
