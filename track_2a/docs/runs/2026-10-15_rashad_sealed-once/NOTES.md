### The sealed test dates, run once through the submission image (session 16)

**What ran.** The test rows of the three sealed dates (2020-02-09, 2022-02-13, 2022-05-15; 173 rows, copied to
`data/sealed/` by `scripts/make_sealed.py`, the method of `data/probe/`) through the submission image pinned by its
digest, `ghcr.io/rashad18236/hackapertus-voting-nli@sha256:0c1a10cd92261cdfede7eb8c191a16eab3f94770f0a7386b45a06ebc06f088be`
(= `latest` after PR #24, built from `main` at `71a6d6a`; `src/` as the session 15 image `sha-7ae78ad87cfd`). `make run`
with the organisers' command, task A (173 cases, the 9 booklets in a folder outside the repository) and task B (173
cases) in separate containers pinned to CPUs 0–1, the real endpoint (Public AI, `swiss-ai/apertus-v1.5-8b`),
`LLM_MIN_INTERVAL=1`, `--raw` kept. Task A 12:33:52–12:37:53 UTC, task B 12:37:53–12:41:12 UTC. Both exit 0, 173 of 173
responses each (`scripts/check_format.py`: no errors, no warnings). Every default was frozen before; nothing was changed
after the numbers were read (status log, 12:42).

**Attempt 1 and the health checks.** The first attempt (task A, 11:37) was stopped after 23 cases: the gateway refused
16 of its 23 answer calls and 4 of its 5 parsing calls with HTTP 400 ("Unsupported model or no available clients:
alias-apertus"), and the first refusal made `src/llm.py` drop `response_format` for the rest of the run. No score was
read; its files are in `aborted-attempt-1/task-A/` (run.json kind "stopped"). By the rule written before the rerun
(decisions file), the one rerun waited for a health check of the same image on 10 dev cases with every call answered:
checks at 11:53, 12:03, 12:13 and 12:23 failed (5, 7, 5 and 5 of 10 calls refused, the same error; Public AI's status
page listed the 8B as "Degraded"), the check at 12:33 passed (10 of 10 answered), and the rerun started at once
(`health_checks.json`). The rerun is the run below; there is no other.

| Task | Macro-F1 | F1 ent / neu / con | Evidence | Unreadable | Calls | Mean input + output tokens |
|---|---|---|---|---|---|---|
| A (173) | **0.9886** | 0.991 / 0.991 / 0.984 | **0.975** (115 of 118) | 0 | 181 (173 + 3 A6 second looks + 3 AP-structure + 2 AP-part) | 1,276 + 19.2 |
| B (173) | **0.9598** | 0.952 / 0.972 / 0.955 | — | 0 | 173 | 845 + 9.8 |

Per date (`sealed_report.json`, the starter's `evaluate.py` on each date's cases; a task B case's date is its row's):

| Date (rows) | Task A Macro-F1 | Evidence | Task A tokens | Task B Macro-F1 | Task B tokens |
|---|---|---|---|---|---|
| 2020-02-09 (42) | 0.9734 | 1.000 (26 of 26) | 1,239 + 14.6 | 0.9263 | 786 + 8.2 |
| 2022-02-13 (90) | 1.0000 | 0.984 (60 of 61) | 1,283 + 23.2 | 0.9652 | 836 + 10.6 |
| 2022-05-15 (41) | 0.9746 | 0.935 (29 of 31) | 1,299 + 15.2 | 0.9777 | 928 + 9.7 |

**Endpoint.** All 354 calls answered by one backend (blablador, `vllm-0.23.1rc1…`); 0 failed calls, 0 gateway cache
hits (these requests had never been sent); Python wrote 0 of 346 labels.

**Task A paths.** Every case routed, none fell back (bm25-ap 0, so no AP-translate call). The rules named the part of
171 of 173 claims, Apertus (AP-part) the other 2 (rows 14, 360). The parser placed the vote of 150 cases; for 23 cases,
all of one ballot of 2022-02-13 in de (9), fr (6) and it (8), it did not: it read the ballot's title wrongly in all three
booklets (a notice on the contents page taken as the title), so the vote name matched no title. Apertus read the
contents (AP-structure, one call per booklet, 3 calls) and the 23 cases were routed to the named part. Parts: council
48, summary 37, committee 34, law 28, detail 26. All 25 cases placed or routed by Apertus were answered correctly. A6
looked again 3 times (rows 209, 1077, 1330); all three answers changed from neutral and are correct.

**Parser coverage of the sealed booklets** (`coverage.json`, `scripts/parser_coverage.py --include-sealed`, page
numbers only): 9 of 9 booklets complete, 27 of 27 votes found with every part valid (9 per language), 0 cross-language
disagreements. The check compares parts and pages, not titles; it did not see the misread title above.

**Errors** (ids and labels only; `sealed_report.json`, `error_types_A.json`):

- Task A, 2: `v1.1-row-1222-A` gold contradiction, answered entailment (route summary); `v1.1-row-1303-A` gold
  contradiction, answered neutral (route summary). Both reading errors: the gold passage was in the part sent
  (`scripts/error_types.py`, no model call).
- Task B, 7 (all reading errors; task B has no routing): `v1.1-row-771-B` and `v1.1-row-866-B` gold neutral, answered
  contradiction (an unrelated passage called a contradiction: the "other ballot" class); `v1.1-row-201-B`,
  `v1.1-row-349-B`, `v1.1-row-488-B` gold entailment, answered contradiction; `v1.1-row-1160-B` gold contradiction,
  answered entailment; `v1.1-row-221-B` gold entailment, answered neutral.

**Replay table** (`replay_table.json`, `scripts/prompt_snapshot.py run --set sealed=data/sealed/cases.jsonl`, two passes,
then `table`): the replay reproduces 345 of 346 labels and every evidence (`replay_vs_run.json`). The one difference,
`v1.1-row-1077-A`, is A6's second look: that case is a chain of three dependent calls (AP-structure's reading routes
the answer request, whose cited paragraphs make the second look's request), and two passes pair chains of two, so the
second look's request is not in the table and the fake model gives its fixed answer. The case makes the same number of
requests; local time counts it as one replay miss.
