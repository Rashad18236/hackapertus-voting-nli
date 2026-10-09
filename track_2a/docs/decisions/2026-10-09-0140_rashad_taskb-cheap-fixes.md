## Task B cheap fixes (2026-10-09, from 01:40 UTC)

Rashad's instructions; report: `docs/taskb_cheap_fixes.md`. Branch
`claude/eager-cannon-08bx1h-taskb` (the task B branch). One change per run,
all 300 dev task B cases each time; the test split is never used.

**Acceptance rule (from this stage on; it replaces the earlier criterion "a variant more than 0.02 Macro-F1 lower loses", used in sessions 4 and 6):**

- **A change that removes tokens is kept if Macro-F1 falls by no more than 0.01 and no label's F1 falls by more than 0.03.**
- **A change that adds tokens is kept only if Macro-F1 rises by at least 0.01.**
- **Each run is compared with the best version kept so far.** The first comparison is with the baseline.

- **Baseline of this stage: `2026-10-09_rashad_v3-topic-first_devB300-run1`, v3-topic-first, Macro-F1 0.919.** Rashad's choice; the latest run on the current endpoint without a failed call.
- **"Tokens" in the rule are the mean input plus output tokens per case.** The organisers' proxy counts both; strict JSON mainly removes output tokens.
- **Task B rows from before 2026-10-08 13:25 UTC are marked "old endpoint behaviour, not comparable" in `docs/results.md`, computed from each run's date and start time by `scripts/build_docs.py`.** One rule, applied to every row, cannot be forgotten on a new row.
- **Canary: 30 dev task B cases (10 per gold label, seed 42) with v3's answer texts from the baseline run, in `docs/canary_taskb.json`; `scripts/canary_taskb.py` re-sends exactly the baseline request before each run and stops on any difference.** Run 2 of the confirmation stage showed identical texts for an unchanged endpoint, so any difference means the endpoint changed.
- **HTTP 429 is retried up to twice: Retry-After if the server sends it, otherwise 2 s then 4 s, never more than 10 s; waits count in the case time and tokens of every attempt count (`src/llm.py`, `tests/test_llm.py`).** One case was lost to a 429 in the confirmation stage; a rate limit is temporary, unlike a bad request.
- **We send one request at a time: `src/cli.py` and `scripts/paired_run.py` call the model case by case, with no parallelism.** Lowering parallelism could not have avoided the 429: run 2 sent 300 requests in 188 s (about 96 per minute, one after the other, because the endpoint answered in about 0.6 s), and the 429 came at request 299. A pause between requests or the retry avoids it; the retry costs nothing when no 429 comes.
- **New task B settings `schema_b` and `max_tokens_b` (`--schema-b`, `--max-tokens-b`); the defaults stay as they were (no schema, 32).** Each run names its settings; the defaults change only by a separate decision.
