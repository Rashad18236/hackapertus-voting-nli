## Task B branch: main merged, HTTP 429 in the fake model, task B results per run (2026-10-09, from 14:52 UTC)

Branch `claude/eager-cannon-08bx1h-taskb`, run with Claude Code on Rashad's instructions. No model calls; the test
split was not used.

- **Current `main` (`25ed5fa`, PR #12) was merged in, not `main` with the input hardening.** That pull request is open,
  not merged; the instruction allowed current `main` in that case.
- **The merge was a merge commit; `docs/results.md` and `docs/decisions.md` were regenerated with
  `scripts/build_docs.py`.** They were the only conflicts. `src/cli.py` and `src/llm.py` merged without conflict
  because `main` had not changed them since this branch started.
- **The fake model has two HTTP 429 markers: `STUB_429_ONCE` (the first attempt only) and `STUB_429` (every
  attempt). Both send `Retry-After: 1`.** The first is the case asked for: a rate limit, then an answer. The second
  shows that a limit that never lifts still ends in a valid fallback response after 1 + 2 attempts. One second keeps
  the test short and exercises `Retry-After` rather than the default 2 s and 4 s pauses.
- **The first-attempt bookkeeping of `STUB_FAIL_ONCE` and `STUB_429_ONCE` is one helper, keyed by marker and request
  hash.** The two markers cannot then use up each other's first attempt.
- **The 429 markers sit in their own tuple next to `decide()`, and the changes avoid the lines that the input-hardening
  branch (`STUB_SLOW`) and session 8 changed in the same file.** The three branches can then be merged in any order
  without conflicts in `scripts/stub_llm.py`.
- **The contract test checks that the wait is in `inference_time_ms` (at least 1,000 ms) and that the answered case
  keeps its label and tokens.** On `main`'s `src/llm.py` (no 429 retry) the same test fails: the case gets the
  neutral fallback.
- **`technical_report.md`: the task B headline 0.947 is replaced by one row per recorded run of `v3-topic-first` on all
  300 dev cases (2026-10-08 06:10, 2026-10-09 01:25 and 01:33, four-arm arm A at 02:11), each with its run folder.**
  The same prompt scored 0.947, 0.919, 0.916 and 0.867 as the endpoint changed; one number would hide that. All numbers
  come from the runs' `run.json` and notes.
- **Section 6 names both backends and the model name each reported (`x-litellm-model-name`: `openai/alias-apertus` on
  blablador.fz-juelich.de, `openai/swiss-ai/Apertus-8B-Instruct-2509` on featherless.ai).** These are the four-arm run's
  records. Runs before it recorded no backend, and the report says so.
- **Section 2's retry sentence now describes the HTTP 429 retries this branch added to `src/llm.py`.** It said "exactly
  one retry, for HTTP 5xx and timeouts only", which this branch's code no longer does.
