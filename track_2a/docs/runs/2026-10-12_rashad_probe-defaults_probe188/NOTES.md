### Probe: two unseen voting dates with today's defaults (session 10, step 4)

**The probe set** (`data/probe/`, `scripts/make_probe.py`): the 94 test rows dated 2021-03-07 and 2025-09-28,
copied as 94 task A and 94 task B cases with their expected labels (`data/test/` unchanged). The other three test
dates (2020-02-09, 2022-02-13, 2022-05-15) stay sealed: no line of theirs was parsed (lines were chosen by the
booklet path and the row id before parsing). Six booklets (de, fr, it for both dates) in `output/booklets_probe/`.
No pattern, rule or threshold in `src/` was written for these dates; from now on the probe may be used like dev.

**Without the model** (`offline/route_check_summary.json`, `scripts/route_check.py`):

- Booklets: 5 of 6 parse completely; `2025_09_28_fr`, vote 1: "contents entry without arguments" (14 of 15
  votes pass the checks).
- Router: all 94 claims get a part (council 34, summary 20, law 16, committee 14, detail 10).
- Routed: 83 of 94 cases; 11 fall back to embed-e5-small (8: the vote's structure not found, all in
  `2025_09_28_fr`; 3: the committee part empty for that vote).
- Every routed case with a gold passage (57) has it among the sent paragraphs (hit 1.000); mean 2,848
  characters sent.
- Local time (`local_time_*.json`, image `s10-step2-c`, 2 CPUs): task A 0.037 s per case at 1.0 s per request,
  0.236 s at 0.3 s; task B 0.015 / 0.014 s. Per case higher than dev for task B because the fixed start-up
  (about 0.9 s) is shared by 94 cases instead of 300.

**With the model** (image `s10-step2-c`, the organisers' command via `make run`, task A and task B in separate
containers, Public AI `apertus-v1.5-8b`, one request per second; every answer from one backend, blablador; 0
failed calls, 0 unreadable answers, so 0 neutral-fallback labels):

| | Macro-F1 | F1 E / N / C | evidence | input + output tokens | probe | dev (session 9) | val (session 9) |
|---|---|---|---|---|---|---|---|
| task A | **0.960** | 0.978 / 0.949 / 0.952 | **0.908** (59 of 65) | 1,232 + 14.4 | | 0.980, ev. 0.980 | 0.961, ev. 0.958 |
| task B | **0.961** | 1.000 / 0.926 / 0.956 | | 1,831 + 8.6 | | 0.967 (no cut) | 0.957 (no cut) |

The probe lands on val's level for both tasks (task A a little below dev, as val was).

**Every error, by mechanism** (`errors.json`):

| task | case | gold → answer | path | mechanism |
|---|---|---|---|---|
| A | row-1058 | 2 → 0 | fallback (2025_09_28_fr) | entailment and contradiction mixed up |
| A | row-763 | 1 → 2 | law | called contradiction, gold neutral (a claim about a 2019 Japan agreement) |
| A | row-1453 | 2 → 1 | committee | neutral although a paragraph was cited ([6]) |
| A | row-1176 | 2 → 1 | law | neutral, nothing cited |
| B | row-536, 644, 763, 918 | 1 → 2 | task B | called contradiction, gold neutral (claims about another ballot or fact) |

Task B's four errors are all session 9's main pattern (a neutral claim called a contradiction); row 763 is wrong
in both tasks. Task A's errors are spread over the mechanisms; one comes from the fallback path.

**Evidence misses** (`evidence_misses.json`): 6 of 65. Four are on the fallback path (rows 485, 1058, 1123, 1220;
three in `2025_09_28_fr`, whose first vote the parser does not find), two are neutral answers to contradictions
(rows 1176, 1453: no evidence). On the routed path every answered contradiction or entailment cites the gold
passage. The parser gap in `2025_09_28_fr` costs 3 evidence hits and probably the 2 → 0 error.

**REF SCORE on the probe** (`ref_score.json`; the probe's own local times):

| | S_A | T_A | K_A | S_B | T_B | K_B | REF SCORE |
|---|---|---|---|---|---|---|---|
| 1.0 s per request | 0.884 | 1.000 | 0.481 | 0.789 | 0.343 | 0.435 | **0.846** |
| 0.3 s per request | 0.765 | 0.212 | 0.481 | 0.790 | 0.347 | 0.435 | **0.775** |

Files: `predictions.jsonl`, `raw_answers.jsonl`, `official_score.*` (both tasks; task A in `run.json`),
`task-B/` (task B's own run), `cli.log`, `errors.json`, `evidence_misses.json`, `local_time_*.json`,
`offline/route_check_summary.json`.
