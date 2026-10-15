# Session 16 (final): the sealed test dates once, the report's fields, the submission prepared

Branch `rashad/session-16` from `main` at `71a6d6a` (session 15b merged in step 0), 2026-10-15 from 11:31 UTC,
unattended. Status log: `docs/session_16_status.md`; decisions, each written before the step it concerns (the
after-the-run ones say when they were written): `docs/decisions/2026-10-15-1131_rashad_session-16.md`. No code in
`src/`, no default, prompt or threshold changed. Draft PR, not merged, no tag: Rashad merges, tags `submission`,
submits and rotates the keys.

## In short

**The sealed test dates were run once through the submission image, after every default was frozen; nothing was
changed afterwards.** 173 rows (2020-02-09 42, 2022-02-13 90, 2022-05-15 41), one task A and one task B case each:

| Sealed, run once | pooled | 2020-02-09 | 2022-02-13 | 2022-05-15 |
|---|---|---|---|---|
| Task A Macro-F1 (F1 ent / neu / con) | **0.9886** (0.991 / 0.991 / 0.984) | 0.9734 | 1.0000 | 0.9746 |
| Task A evidence | **0.975** (115 of 118) | 1.000 (26 of 26) | 0.984 (60 of 61) | 0.935 (29 of 31) |
| Task A tokens per case, input + output | 1,276 + 19.2 | 1,239 + 14.6 | 1,283 + 23.2 | 1,299 + 15.2 |
| Task A local time per case, 1.0 / 0.3 s per request | 0.025 / 0.035 s | 0.057 / 0.051 s | 0.050 / 0.048 s | 0.160 / 0.152 s |
| Task B Macro-F1 (F1 ent / neu / con) | **0.9598** (0.952 / 0.972 / 0.955) | 0.9263 | 0.9652 | 0.9777 |
| Task B tokens per case, input + output | 845 + 9.8 | 786 + 8.2 | 836 + 10.6 | 928 + 9.7 |
| Task B local time per case, 1.0 / 0.3 s per request | 0.011 / 0.013 s | 0.035 / 0.081 s | 0.017 / 0.019 s | 0.034 / 0.121 s |
| REF SCORE at 1.0 / 0.3 s per request | **0.898 / 0.893** | 0.863 / 0.866 | 0.894 / 0.892 | 0.808 / 0.803 |

Both tasks pass their minimums (0.60 and 0.75). For comparison (not a choice: nothing could change), the final
defaults scored task A 0.977 / 0.981 / 0.990 and task B 0.987 / 0.968 / 0.977 on dev / val / probe; REF SCORE dev
0.904 / 0.893. Per date, start-up and the first booklet fall on fewer cases (task A 1.8–6.3 s to the first request);
the pooled column is the organisers' setting (one container per task).

0 failed calls, 0 unreadable answers, 0 labels written by Python (of 346); all 354 calls answered by one backend
(blablador, `vllm-0.23.1rc1…`), 0 gateway cache hits. Run: `docs/runs/2026-10-15_rashad_sealed-once`.

**Found, not changed (for Rashad).** (1) Without `MODEL`, the image asks for `swiss-ai/Apertus-v1.5-8B` (the
contract's spelling); Public AI refuses that name with **HTTP 403** ("key not allowed to access model"), which
`src/llm.py`'s model-name fallback does not handle (it reads `BASE_URL/models` only after a 404, or a 400 once
`response_format` was dropped), so every case gets the neutral fallback. With `-e MODEL` (`swiss-ai/apertus-v1.5-8b`)
the published image answers. The README command is unchanged; a note under it, and a sentence in the submission
message, say to set `MODEL`. Whether the organisers' proxy accepts the default name is not known
(`docs/organiser_questions.md`, question 5). (2) The parser misreads one ballot's title on 2022-02-13 (all
three languages); Apertus reading the contents placed its 23 cases, all answered correctly.

## Step 0: session 15b merged

PR #24 (head `d3a5fdd`) open, draft, `mergeable_state` clean, checks green; marked ready and merged with a merge commit:
**MAIN_COMMIT `71a6d6a`**, branch kept, `origin/main` contains `d3a5fdd`. publish-image on `main` (run 107) green:
`latest`, `sha-71a6d6ad61f5`. `latest` pulled with an empty Docker configuration: **IMAGE_DIGEST
`sha256:0c1a10cd92261cdfede7eb8c191a16eab3f94770f0a7386b45a06ebc06f088be`**, revision label `71a6d6a`. Branch
`rashad/session-16`, draft PR #25. dockerd was restarted (stale pid files).

## Step 1: the sealed run, once

**Cases (1b).** `scripts/make_sealed.py` (new; `scripts/make_probe.py`'s method and functions): only the lines of
`data/test/cases.jsonl` naming a sealed booklet are parsed; the rows' task B lines and expected labels picked by id
text; copied to `data/sealed/` (`data/test/` unchanged). 173 rows → 173 task A + 173 task B cases, 346 expected labels.
Task A booklet languages fr 63, de 56, it 54; claim languages de 61, it 58, fr 54; 66 same-language. The 9 booklets
(de, fr, it of each date) downloaded from the dataset's `booklet_url` into `/home/user/sealed_booklets`, outside the
repository; no PDF or page text committed.

**The run (1c).** The image pinned by IMAGE_DIGEST, `make run` with the organisers' command, task A then task B in
separate containers pinned to CPUs 0–1, Public AI's `swiss-ai/apertus-v1.5-8b`, `LLM_MIN_INTERVAL=1`, `--raw` kept.

- **Attempt 1 (11:37, task A) failed outside the code and was stopped after 23 cases:** the gateway refused 16 of 23
  answer calls and 4 of 5 parsing calls with HTTP 400 ("Unsupported model or no available clients: alias-apertus");
  the first refusal also made `src/llm.py` drop `response_format` for the rest of the run. No score was read. Files:
  `aborted-attempt-1/task-A/` (run.json kind "stopped").
- **The one rerun waited for a health check** (rule written before it: the same image on the first 5 task A and 5 task
  B dev cases, every call answered, `response_format` kept; every 10 minutes from 11:53 until 18:30): 11:53, 12:03,
  12:13, 12:23 failed (5, 7, 5, 5 of 10 calls refused; Public AI's status page: the 8B "Degraded"); **12:33 passed**
  (10 of 10). The rerun started at once: task A 12:33:52–12:37:53, task B 12:37:53–12:41:12 UTC, both exit 0, 173 of
  173 responses each, 0 failed calls (`health_checks.json`). It is the run; there is no other.

**Scoring and local time (1d).** The starter's `evaluate.py` (pooled `official_score.*` in `task-A/` and `task-B/`;
per date in `sealed_report.json` by `scripts/sealed_report.py`, new). Local time: `scripts/local_time.py` through the
same image (2 CPUs pinned to 2–3, 4 GB) at 1.0 and 0.3 s per request, pooled and per date, with a replay table of the
sealed run's own answers (`scripts/prompt_snapshot.py run --set sealed=data/sealed/cases.jsonl`, the new option, two
passes, then `table`; `replay_table.json`). The replay reproduces 345 of 346 labels and every evidence; the
difference, row 1077-A, is A6's second look in a chain of three calls (AP-structure → answer → second look) that two
passes do not pair; local time counts it as 1 replay miss (same number of requests). REF SCORE:
`scripts/official_score.py`.

**What the run shows (1e).**

- *Task A paths:* every case routed, 0 fallbacks (so 0 AP-translate calls). Parts: council 48, summary 37, committee
  34, law 28, detail 26. The rules named the part of 171 of 173 claims; **AP-part** the other 2 (rows 14, 360).
  The parser placed the vote of 148 + 2 = 150 cases; for 23 cases (one ballot of 2022-02-13: de 9, fr 6, it 8) it did
  not, because it read the ballot's title wrongly in all three booklets (a notice on the contents page taken as the
  title); **AP-structure** (3 calls, one per booklet) placed them. All 25 cases placed or routed by Apertus were
  answered correctly. Calls: task A 181 (173 + 3 AP-structure + 2 AP-part + 3 A6), task B 173.
- *A6:* 3 second looks (rows 209, 1077, 1330), all three changed neutral to the gold label (0 / 2 / 2).
- *Parser coverage of the sealed booklets* (`coverage.json`, `scripts/parser_coverage.py --include-sealed`, a new
  flag; page numbers only): 9 of 9 booklets complete; 27 of 27 votes found and valid, every vote with a usable part
  (de, fr, it 9 each: 2020 2 votes, 2022 7); 0 cross-language disagreements. The check compares parts and start
  pages, not titles: it did not see the misread title above.
- *Errors* (ids and labels only):

| Id | Gold | Answer | Path | Class |
|---|---|---|---|---|
| v1.1-row-1222-A | contradiction | entailment | route:summary | reading (gold passage in the part sent) |
| v1.1-row-1303-A | contradiction | neutral | route:summary | reading (gold passage in the part sent) |
| v1.1-row-771-B | neutral | contradiction | task B | another ballot (unrelated passage called a contradiction) |
| v1.1-row-866-B | neutral | contradiction | task B | another ballot |
| v1.1-row-201-B | entailment | contradiction | task B | reading |
| v1.1-row-349-B | entailment | contradiction | task B | reading |
| v1.1-row-488-B | entailment | contradiction | task B | reading |
| v1.1-row-1160-B | contradiction | entailment | task B | reading |
| v1.1-row-221-B | entailment | neutral | task B | reading |

  Task A: 2 errors, both reading, 0 routing (`error_types_A.json`, `scripts/error_types.py` without a model call).
  Task B: 7, of which 2 "another ballot"; by date 3 (2020-02-09), 3 (2022-02-13), 1 (2022-05-15).

**Nothing changed (1f).** Status log, 12:42: "The sealed numbers have been read. NOTHING is changed after reading
them: no code, default, prompt, threshold, rule or run."

## Step 2: report and submission files

- `technical_report.md`: title line "# Technical report — Abstimmungsbüchlein Check: NLI over Swiss federal voting
  booklets with Apertus"; header fields (track, event, project, team, repository, image with IMAGE_DIGEST and
  MAIN_COMMIT, demo); first paragraph "the sealed test dates were run once, after the freeze (section 1)"; no TODO
  left. §1: the sealed table (pooled and per date) and "Run once through the submission image after every default was
  frozen; nothing was changed afterwards." The sealed column did not fit the final-defaults table within 6 pages
  (every row wrapped), so the sealed table stands alone. §4: "Who did what". §5: the sealed set. §6: "Sealed test"
  (coverage, routing, errors by class). §7: "traceable to the booklet". §8: IMAGE_DIGEST, MAIN_COMMIT, "Submission
  tag: `submission` (set on main after this PR)". References: SEALED, K.
- **Page count.** With the sealed table the PDF had 7 pages. Changes, in order: §3 prose shortened (bullets of
  `src/cli.py` and `src/pipeline.py`, parsing and selection merged into one paragraph, the router, parser, A6 and
  evidence sentences, one diagram line), the negative table's "why not" column shortened ("lower; 1.7–3 calls",
  "< +0.015 bar", "Python sets no label", "more breaks"), the session's own new text shortened, the sealed column
  removed from the final-defaults table; then the style (`docs/report/report.css`): §1's two tables compact
  (8.5 pt, as §4's), code blocks 8.5 pt (the architecture diagram no longer wraps), line height 1.3 → 1.26. No number,
  table or row was removed. **PDF: 6 pages** (`bash scripts/build_report_pdf.sh`).
- **Numbers check** (`scripts/report_numbers_check.py`, new; full list in `docs/report_numbers_check.md`), output:

      577 numbers, 575 OK, 2 MISSING -> docs/report_numbers_check.md
      | 311 | 2402.05672 | MISSING |  |
      | 312 | 2009 | MISSING |  |

  Both MISSING are traced to the citations (the arXiv id of Wang et al. 2024 and the year of Robertson and Zaragoza
  2009); they are identifiers, not results, and stay. No number was changed because of the check. (The check says
  where a number can be found, rounded; a reader still reads the line and the file side by side.)
- Required sentences present: "Not political advice", "traceable to the booklet" (§7), licence (§8: code Apache-2.0,
  report CC-BY-4.0). No key, no endpoint other than the public ones, no booklet text beyond the short quotes already
  there.
- `README.md`: title "Abstimmungsbüchlein Check", subtitle, team line, "Sealed test results: see technical_report.md
  §1.", one sentence on `examples/predictions.jsonl`; image line and run command unchanged. **The command tested as
  written** (13:03–13:05): `docker pull` and `docker run` of `latest` (= IMAGE_DIGEST) exit 0 with one line per id.
  In this sandbox the container reaches the endpoint only with the proxy flags (as written: connection errors, neutral
  fallbacks); with them, HTTP 403 on the default model name (above); with `-e MODEL` both example cases are answered.
  A note under the command says to add `-e MODEL` for Public AI.
- `examples/predictions.jsonl`: the submission image (by digest) on `examples/cases.jsonl` through `make run`, the
  real endpoint, 13:03, fresh answers (an earlier run at 12:42 was answered from the gateway's cache): 2 lines, both
  entailment; `scripts/check_format.py` clean.
- `docs/organiser_questions.md`: "Answer received: none as of 15 October 2026" under each question.
- `docs/submission_message.md`: the form's message (image, separate containers, `submission` tag, the 8B only, the two
  embedding models and licences, the MODEL sentence, the sealed numbers, the Discord questions file).

## Step 3: checks

- `python3 -m pytest tests` (pypdf 6.17.0): 357 passed, 1 skipped.
- `python3 scripts/build_docs.py --check`: passes (results.md and decisions.md regenerated).
- `python3 scripts/self_checks.py --starter <starter>`: 17 PASS, exit 0.
- `scripts/check_format.py`: sealed task A and task B predictions (173 each) and `examples/predictions.jsonl` (2):
  no errors, no warnings.
- No key value in any committed file (checked against `.env`); no booklet PDF added.
- Workflows on the final commit: see the PR.

## After merging (Rashad)

Merging this PR changes only documents and data under `track_2a/`, but the publish workflow rebuilds `latest` from
`main`: same `src/`, a **new digest** (the report and this file name IMAGE_DIGEST, the image the sealed run used).
The PR description lists the steps: tag `submission` on the merge commit, check publish-image and the new `latest`
digest, make the package public, fill the form, rotate the keys.
