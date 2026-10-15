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

## Running

- Health checks of the endpoint (every 10 minutes from 11:53), then the one rerun of the sealed run.
