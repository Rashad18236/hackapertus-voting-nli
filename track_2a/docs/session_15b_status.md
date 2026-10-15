# Session 15b status

One line per event, UTC. If the session is restarted with "continue", work goes on from "Next".

- **Branch:** `rashad/session-15b` from `main` at `61ce0eb` (draft pull request, never merged, no tag).
- **What it is:** one measurement for the technical report (the 70B as a reference point); no code path, default or
  prompt of `src/` changes; nothing is adopted.
- **Clock:** the instruction says "push by Thursday 15 October 10:00 UTC"; the session started at 10:30 UTC, after
  that time. Work goes on and is pushed as soon as it is done (decisions file).
- **Decisions:** `docs/decisions/2026-10-15-1030_rashad_session-15b.md`.

## Done

- (10:30 Thu) The instruction ends with "END OF SESSION 15B INSTRUCTION": complete. Started after its push deadline
  (10:00 UTC).
- (10:32) Step 0: PR #23 checked (open, draft, `mergeable_state` clean, head `18fcd06`, four checks green), marked
  ready, merged with a merge commit: `main` = `61ce0eb`; `origin/main` contains `18fcd06`.
- (10:33) dockerd started again (stale containerd pid file from the previous container removed).
- (10:35) Step 1: `BASE_URL/models` (Public AI) lists 9 ids. Apertus v1.5: `swiss-ai/apertus-v1.5-8b`,
  `swiss-ai/apertus-v1.5-8b-thinking`, `swiss-ai/apertus-v1.5-70b`, `swiss-ai/apertus-v1.5-70b-thinking`; other
  Apertus ids: `swiss-ai/apertus-8b-instruct`, `swiss-ai/apertus-70b-instruct`. **MODEL_70B =
  `swiss-ai/apertus-v1.5-70b`.**
- (10:36) Branch `rashad/session-15b` from `origin/main`. `scripts/paired_run.py`: an arm field `model` (sets `MODEL`
  for the arm's cases; `src/llm.py`'s fallbacks kept per arm) and `--call-log` (one line per model call: latency,
  tokens, answering model, cache hit). Decisions for steps 1 and 2 written.
- (10:46) Step 1 smoke test (`docs/runs/2026-10-15_rashad_70B-smoke_devA3-devB3`): all 6 70B calls refused with
  HTTP 429 (3 attempts each, about 26 s per attempt); the 8B arm answered all 6. Public AI's status page lists the
  70B at about 54–56 % uptime over 30 days, one entry "Down".
- (10:47) Probe 1 (one minimal 70B request): HTTP 429 after 27 s. Probes 2 and 3 at 11:02 and 11:17 (decisions file).
- (10:50) Step 0: publish-image on `main` (run 106) succeeded: `latest` and `sha-61ce0ebb9f2c`; `latest` pulls
  without a login: digest `sha256:5cb605460fe5…`, the same image as `sha-61ce0ebb9f2c`, revision label `61ce0eb`.

- (11:02) Probe 2: HTTP 429 after 27.2 s.
- (11:17) Probe 3: HTTP 429 after 26.0 s. **The 70B is not reachable (9 of 9 calls refused over 41 minutes); step 2
  not run; nothing adopted.**
- (11:18) Step 3: technical report (one sentence under the ablation table, a Limitations bullet on the 8B; PDF 6
  pages); README unchanged; `docs/session_15b_report.md`.

## Closed

The 70B could not be measured; the submission stays the 8B. The final session was not started.
