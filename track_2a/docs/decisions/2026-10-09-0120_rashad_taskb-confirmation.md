## Task B confirmation (2026-10-09, from 01:20 UTC)

Rashad's instructions; report: `docs/taskb_confirmation.md`. Branch
`claude/eager-cannon-08bx1h-taskb`, from `main` after PR #11 (no task B branch
existed, so this one was created for the stage). No prompt changes in this step.

- **Every task B run's `run.json` gets a `task_b` block (prompt version, change against the previous version, number of cases, strict JSON, max_tokens), and `docs/results.md` gets a task B table built from it.** results.md is generated; the facts must live in the run records. Values come from each run's notes and from the code at its commit; what no record holds is shown as "not recorded".
- **No task B run so far used 120 cases.** Every finished run used all 300 dev task B cases; the stopped first attempt of Run A answered 5 (all failed calls) and kept no predictions.
- **No task B run used strict JSON.** At every run's commit the task B call sends no `response_format`; the prompt asks for `{"label": n}`. max_tokens was 400 for v1-json and 32 since v2-label-only.
