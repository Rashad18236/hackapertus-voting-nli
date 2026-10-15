# Session 16 status (final)

One line per event, UTC. If the session is restarted with "continue", work goes on from "Next".

- **Branch:** `rashad/session-16` from `main` at `71a6d6a` (draft pull request, never merged by Claude, no tag).
- **What it is:** the last session: the sealed test dates run once through the submission image; the report's
  fields; the submission files. No code in `src/`, no default, prompt or threshold changes.
- **Clock:** everything pushed by Thursday 15 October 20:00 UTC.
- **Decisions:** `docs/decisions/2026-10-15-1131_rashad_session-16.md`.

## Done

- (11:31 Thu) The instruction ends with "END OF SESSION 16 INSTRUCTION": complete. dockerd started again.
- (11:32) Step 0: PR #24 checked (open, draft, clean, head `d3a5fdd`, checks green), marked ready, merged with a
  merge commit: MAIN_COMMIT = `71a6d6a`; `origin/main` contains `d3a5fdd`.
- (11:33) Decisions for step 1 written, beginning with "The sealed dates are opened once, in this session, for one run
  through the submission image. No change follows from the result." Nothing of the sealed dates opened yet.
- (11:35) publish-image on `main` (run 107) succeeded: `latest`, `sha-71a6d6ad61f5`. `latest` pulled with an empty
  Docker configuration: IMAGE_DIGEST `sha256:0c1a10cd92261cdfede7eb8c191a16eab3f94770f0a7386b45a06ebc06f088be`,
  the same image as `sha-71a6d6ad61f5`, revision label `71a6d6ad61f5…` = MAIN_COMMIT.
- (11:36) Branch `rashad/session-16` from `origin/main`.
- (11:37) Step 1b: `scripts/make_sealed.py --fetch /home/user/sealed_booklets`: 173 sealed rows, 173 task A and 173
  task B cases, 346 expected labels (`data/sealed/`); 9 booklets (de, fr, it of each date) outside the repository.
  Rows per date: 2020-02-09 42, 2022-02-13 90, 2022-05-15 41. Task A booklet languages: fr 63, de 56, it 54; claim
  languages de 61, it 58, fr 54; 66 same-language.
- (11:37) Step 1c, attempt 1 (task A): 16 of the first 23 calls refused with HTTP 400 "Unsupported model or no
  available clients: alias-apertus" (a gateway deployment of the 8B down), 7 answered by blablador; the first 400
  also switched off response_format. Stopped at 11:37:56 (no score read); files in `aborted-attempt-1/`. Rule for
  the one rerun in the decisions file: not before 11:53, and only after a 10-case dev health check passes.

- (11:40) Step 1e, coverage of the sealed booklets (`scripts/parser_coverage.py --include-sealed`, a new flag; no model): 9 of 9 booklets complete, 27 of 27 votes found and valid (2020: 2 votes, 2022: 7, in each of de, fr, it), every vote with a usable part, 0 cross-language disagreements (`docs/runs/2026-10-15_rashad_sealed-once/coverage.json`, page numbers only).
- (11:45) Step 2 drafts (no sealed number in them yet): report title, header fields, "Who did what", §8 tag line; README title, team, sealed-results and example lines; `docs/organiser_questions.md` answers; `docs/submission_message.md`; `scripts/report_numbers_check.py` and `scripts/sealed_report.py` written.

- (11:53) Health check 1 (10 dev cases through the image): FAIL. 5 of 10 calls refused with the same HTTP 400 ("no available clients: alias-apertus"), the other 5 answered by blablador; task A's first 400 switched off response_format. The gateway still sends about half of the 8B's requests to a deployment without a client. Next check 12:03; the sealed rerun waits.

- (12:03) Health check 2: FAIL (7 of 10 calls HTTP 400, the same error; 3 answered by blablador). Public AI's status page (read 11:55) lists `swiss-ai/apertus-v1.5-8b` as "Degraded". Next check 12:13.

- (12:13) Health check 3: FAIL (5 of 10 calls HTTP 400, the same error). Next check 12:23.

- (12:23) Health check 4: FAIL (5 of 10 calls HTTP 400, the same error). Next check 12:33.

- (12:33) Health check 5: PASS (10 of 10 calls answered, no refused response_format). The one rerun of the sealed run started at once: task A, then task B, into `docs/runs/2026-10-15_rashad_sealed-once/`.

- (12:41) Sealed run done (task A 12:33:52–12:37:53, task B 12:37:53–12:41:12 UTC): both exit 0, 173 of 173 responses each, 0 failed calls, 0 unreadable answers; final by the rule (no rerun). Scored with the starter at 12:41:42: task A Macro-F1 0.9886, evidence 0.9746 (115 of 118); task B 0.9598.
- **(12:42) The sealed numbers have been read. NOTHING is changed after reading them: no code, default, prompt, threshold, rule or run.**

- (12:45–13:02) Step 1d, no model calls: replay table of the sealed run's own answers (two passes; reproduces 345 of 346 labels, every evidence: row 1077-A's second look is a chain of three calls); local time through the same image at 1.0 and 0.3 s per request, pooled and per date (CPUs 2–3, 4 GB): pooled task A 0.0253 / 0.0349 s, task B 0.0108 / 0.0130 s per case; REF SCORE pooled 0.898 / 0.893. `sealed_report.json`, `error_types_A.json` (task A errors: 2 reading, 0 routing), run.json and NOTES written.
- (13:03) `examples/predictions.jsonl`: the submission image (by digest) on `examples/cases.jsonl` through `make run`, real endpoint, fresh answers (no cache hit): 2 lines, both entailment, check_format clean.
- (13:05) README command tested as written: `docker pull` and `docker run` of `latest` (= IMAGE_DIGEST) exit 0 with one line per id. In this sandbox the container needs the proxy flags; with them, every call is refused with HTTP 403 because the default model name `swiss-ai/Apertus-v1.5-8B` is not one Public AI's key may use (`src/llm.py`'s model-name fallback handles 404 and 400, not 403). With `-e MODEL` (`swiss-ai/apertus-v1.5-8b`) both cases are answered. Command unchanged; one note added under it. No code changed (the session's rule); reported for Rashad.

- (13:10) Step 2: technical report: §1 sealed table (pooled and per date) with the sentence "Run once through the submission image after every default was frozen; nothing was changed afterwards."; the sealed column did not fit the final-defaults table within 6 pages, so the sealed table stands alone; §6 "Sealed test" paragraph; §3 prose shortened; report style: tables of §1 compact, code blocks 8.5 pt, line height 1.26 (no number or table removed). PDF 6 pages. `scripts/report_numbers_check.py`: 577 numbers, 575 found in run files or documents, 2 MISSING = the citations' arXiv id 2402.05672 and year 2009 (traced to the citations; unchanged). `docs/submission_message.md`: MODEL sentence and the sealed numbers.

- (13:15) Step 3: pytest 357 passed, 1 skipped (pypdf 6.17.0); build_docs --check passes; self_checks 17 PASS; check_format clean on the sealed predictions (173 + 173) and examples/predictions.jsonl; no key value in any committed file. Decisions for steps 1d–2 appended; `docs/session_16_report.md` written; CLAUDE.md updated.

## Closed

All steps done; the PR description holds the after-merge steps for Rashad (tag, publish check, package visibility, form,
keys). Waiting only for the workflows on the final commit.
