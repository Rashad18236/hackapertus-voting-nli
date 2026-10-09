# Task B cheap fixes

2026-10-09, from 01:40 UTC, branch `claude/eager-cannon-08bx1h-taskb`. Run by
Rashad, with Claude Code. The test split was never used. Decisions:
`docs/decisions/2026-10-09-0140_rashad_taskb-cheap-fixes.md`.

## 1. In short

- **The stage stopped before its first run: the canary showed that the
  endpoint changed again.** Before run 1, 3 of the 30 canary answers came
  back different from the baseline of 01:25 UTC, and a repeat a minute later
  gave the same three differences. The change happened between 01:36 and
  01:50 UTC. As the stage rule says, no run was started.
- The setup is done and committed: the old-endpoint marks in
  `docs/results.md`, the canary, the HTTP 429 retries (with tests), the new
  acceptance rule, and the task B settings for strict JSON.
- **Run 2 (the vote name) is skipped on its merits:** `vote` always names the
  passage's own ballot, which the passage already opens with.
- **Run 3's prompt, v5-min, is written (86 fixed tokens) but not run.**
- **Recommendation: freeze nothing new; task B stays on v3-topic-first** until
  a new baseline exists on the current endpoint.

## 2. Setup

**a. Old endpoint behaviour.** Every task B run that started before
2026-10-08 13:25 UTC is now marked "old endpoint behaviour, not comparable",
in the task B table and in the main table of `docs/results.md`. The mark is
computed from each run's date and start time, so new rows get it right
automatically. The baseline of this stage is
`2026-10-09_rashad_v3-topic-first_devB300-run1` (v3-topic-first, 0.919).

**b. Canary.** 30 dev task B cases (10 per gold label, seed 42) and the answer
text v3 gave for each in the baseline run are stored in
`docs/canary_taskb.json`. `scripts/canary_taskb.py` re-sends exactly the
baseline request for them (v3-topic-first, max_tokens 32, no
response_format, temperature 0) and compares the answers character by
character.

**c. Retries for HTTP 429.** `src/llm.py` now retries a rate-limited call up
to twice: after the server's Retry-After time if it sends one, otherwise
after 2 s and then 4 s, never more than 10 s. The waiting time is part of
the case's `inference_time_ms`, and tokens of every attempt count in the
metrics. Six new tests in `tests/test_llm.py` cover this.

- **Parallel requests: one.** `src/cli.py` (and `scripts/paired_run.py`)
  sends one request at a time, case after case.
- **Lowering it would not have avoided the 429.** Parallelism is already at
  its minimum. The 429 of the confirmation stage came at request 299 of a run
  that sent 300 requests in 188 s (about 96 per minute), because the endpoint
  answered in about 0.6 s. A pause between requests, or the retry now in
  place, avoids it.

**d. Acceptance rule** (in `docs/decisions.md`; it replaces the earlier "more
than 0.02 lower loses"):

- a change that removes tokens is kept if Macro-F1 falls by no more than
  0.01 and no label's F1 falls by more than 0.03;
- a change that adds tokens is kept only if Macro-F1 rises by at least 0.01;
- each run is compared with the best version kept so far.

Tokens mean input plus output tokens per case, as the organisers' proxy
counts both.

## 3. The canary before run 1

| Case | Baseline answer (01:25 and 01:33) | 01:50 and 01:51 |
|---|---|---|
| `v1.1-row-767-B` | `{"label": 2}` | `{"label": 1}` |
| `v1.1-row-869-B` | `{"label": 2}` | `{"label": 1}` |
| `v1.1-row-1128-B` | `{"label": 2}` | `{"label": 2}` and a "Reasoning" paragraph |

The other 27 answers were identical. Both baseline runs (01:25 and 01:33) had
given identical answers in all 299 cases they both answered, so the endpoint
was stable then. It changed between 01:36 and 01:50 and gave the new answers
again at 01:51. The status page shows the model as "Operational" and says
nothing more. Rows 767 and 869 are gold neutral and were baseline errors, so
the new behaviour may score differently; that is not measured. Logs:
`docs/runs/2026-10-09_rashad_v3-schema_devB300/` (`canary.txt`,
`canary_repeat.txt`).

## 4. The three runs

**Run 1, v3 with strict JSON (max_tokens 10): not run.** Everything for it is
ready: `--schema-b` sends a JSON schema whose only field is `label`, an
integer limited to 0, 1, 2 (the same mechanism as task A), and
`--max-tokens-b 10`. The 20-case check of whether the schema changes
usage.prompt_tokens comes first, but it also needs model calls, so it was not
made.

**Run 2, the vote name: skipped, not because of the canary.**

- **Is `vote` always there?** Yes. The official contract lists "Reference
  passage, vote name, claim" as task B's input, and `vote` as "Vote name in
  the source language".
- **Which ballot does it name?** The passage's own. `docs/neutral_analysis.md`
  found that `vote` is exactly the passage's first line in all 300 dev
  cases. It is the same in all 886 dataset rows outside the test split, and
  never empty.
- **So it carries no signal.** The passage already starts with that title,
  and the vote name cannot show that a neutral claim is about another ballot.

**Run 3, v5-min: written, not run.** `nli.PROMPTS_B["v5-min"]`, meant for use
with strict JSON (no format instructions):

> Compare the CLAIM with the REFERENCE TEXT from a Swiss voting booklet
> (German, French or Italian). Use only the reference text.
> 0: the reference supports the claim.
> 2: claim and reference cannot both be true.
> 1: otherwise, including when the reference is about a different ballot or
> subject than the claim. Missing information is 1, never 2.

Fixed instructions: 77 tokens for the system prompt plus 9 for the user
message's labels, **86** in all (at most 90 asked; v3's are 203). It keeps
the three rules: another ballot or subject is neutral; contradiction only
when both cannot be true; missing information is neutral, never
contradiction. The passage is untouched.

## 5. The table

Only the baseline has numbers; nothing else was run.

| | Baseline: v3-topic-first (run 1 of the confirmation) | Run 1: v3 + strict JSON | Run 2: vote name | Run 3: v5-min |
|---|---|---|---|---|
| Status | measured, 01:25 UTC | not run (canary failed) | skipped (no signal) | not run (canary failed) |
| Macro-F1 | 0.919 | – | – | – |
| F1 entailment / neutral / contradiction | 0.990 / 0.877 / 0.891 | – | – | – |
| Confusion, gold E (pred E/N/C) | 100 / 1 / 1 | – | – | – |
| Confusion, gold N | 0 / 82 / 17 | – | – | – |
| Confusion, gold C | 0 / 5 / 94 | – | – | – |
| Input tokens, mean / p95 | 1,994 / 4,463 | – | – | – |
| Time, mean / p95 | 1,574 / 2,764 ms | – | – | – |
| Failed calls | 0 | – | – | – |
| Right → wrong / wrong → right | (reference) | – | – | – |

## 6. Recommendation

**Freeze nothing new: task B stays on v3-topic-first, the current default.**
No change was measured, so none can be kept. The 0.919 baseline no longer
describes the current endpoint. The next steps, in order:

1. Run v3-topic-first on all 300 dev task B cases on the current endpoint.
   This becomes the new baseline.
2. Rebuild the canary from that run
   (`scripts/canary_taskb.py --make --from-run <new baseline>`).
3. Then run 1 (strict JSON, with its 20-case token check first) and run 3
   (v5-min, compared with the best version kept), each preceded by the
   canary.

## 7. What stays unverified

- What changed at the endpoint between 01:36 and 01:50 UTC, and whether it
  will change back; Public AI's status page says nothing.
- Whether the new endpoint behaviour scores better or worse than 0.919: two
  of the three changed answers fix baseline errors, but 3 of 30 cases say
  little.
- How the schema affects usage.prompt_tokens (the 20-case check was not made).
- The organisers' endpoint and its rate limits; the HTTP 429 retry was
  tested with fakes only.
