## Task B confirmation (2026-10-09, from 01:20 UTC)

Rashad's instructions; report: `docs/taskb_confirmation.md`. Branch
`claude/eager-cannon-08bx1h-taskb`, from `main` after PR #11 (no task B branch
existed, so this one was created for the stage). No prompt changes in this step.

- **Every task B run's `run.json` gets a `task_b` block (prompt version, change against the previous version, number of cases, strict JSON, max_tokens), and `docs/results.md` gets a task B table built from it.** results.md is generated; the facts must live in the run records. Values come from each run's notes and from the code at its commit; what no record holds is shown as "not recorded".
- **No task B run so far used 120 cases.** Every finished run used all 300 dev task B cases; the stopped first attempt of Run A answered 5 (all failed calls) and kept no predictions.
- **No task B run used strict JSON.** At every run's commit the task B call sends no `response_format`; the prompt asks for `{"label": n}`. max_tokens was 400 for v1-json and 32 since v2-label-only.
- **The two v3 runs ran one after the other, not paired case by case.** Rashad asked for a run and then a second run on the same cases; this measures rerun noise over a few minutes.
- **Noise floor of task B on dev: 0.0033 Macro-F1** (run 1 0.9194, run 2 0.9161). All of it comes from one failed call (HTTP 429) in run 2; the 299 cases both runs answered have identical answer texts. A task B difference smaller than this is within rerun noise; failed calls, not the model, set it.
- **v3-topic-first on today's server: 0.919 (session 2's 0.947 came from the server before the 13:25 UTC change of 2026-10-08).** Only runs on the same server compare.
- **Tokens are counted with the ungated Apertus v1 tokenizer (`swiss-ai/Apertus-8B-Instruct-2509`, commit b946d40); the endpoint's own addition is measured on the endpoint (19 tokens for a system and a user message).** The v1.5 repository is gated; the v1 count matched usage.prompt_tokens within one token in all 300 cases, so it can be trusted for task B text.
- **HTTP 429 is not retried, and nothing was changed for it in this step.** The stage's rule allows one retry for 5xx and timeouts only; whether to retry a rate limit is a decision for later.
- **Errors are grouped by (gold, predicted) and described in plain words in `docs/taskb_errors_intro.md`; `docs/taskb_errors.md` is written by `scripts/taskb_analysis.py`.** The case list stays reproducible, the description is read from the cases.
