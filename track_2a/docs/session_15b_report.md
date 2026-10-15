# Session 15b: Apertus v1.5 70B as a reference point (report only): listed, but not reachable

Branch `rashad/session-15b` from `main` at `61ce0eb` (session 15 merged in step 0), 2026-10-15 from 10:30 UTC,
unattended. Status log: `docs/session_15b_status.md`; decisions, each written before the step it concerns:
`docs/decisions/2026-10-15-1030_rashad_session-15b.md`. The session started after the instruction's push time
(10:00 UTC); the work went on and was pushed as soon as it was done.

## In short

**NOTHING IS ADOPTED.** No code path, default or prompt of `src/` changed; the submission stays the 8B.

**The 70B was not reachable.** Public AI lists `swiss-ai/apertus-v1.5-70b`, but it refused every call: the smoke test's
6 calls (3 dev task A, 3 dev task B; 3 attempts each) and 3 single-request probes 15 minutes apart, 9 of 9 calls over
41 minutes, 21 HTTP requests, every one HTTP 429 after 26–27 s ("Available Model Group Fallbacks=None"). The 8B,
asked alongside in the smoke test, answered all 6 cases in 1.3–1.7 s per call. So step 2 (the interleaved 70B-vs-8B
run on all 600 dev cases and the 46 on-topic cases) did not run, by the rule written before the probes.

**Technical report:** one sentence under the ablation table that no larger model was reachable, and a Limitations
bullet on why the submission is the 8B (the organisers' endpoint and model are unknown, the pipeline was built and
measured on the 8B, the 70B did not answer). PDF 6 pages. README unchanged (it names only the default model).

## Step 0: session 15 merged

PR #23 (`rashad/session-15`, head `18fcd06`) was open, a draft, `mergeable_state` clean, with all four checks green
(tests, image, publish, pull-and-run). It was marked ready for review and merged with a merge commit: `main` =
`61ce0eb`, branch kept; `origin/main` contains `18fcd06`. publish-image on `main` (run 106) succeeded with the tags
`latest` and `sha-61ce0ebb9f2c`. `latest` pulls without a login (an empty Docker configuration): digest
`sha256:5cb605460fe5…`, the same image as `sha-61ce0ebb9f2c`, revision label `61ce0eb` = `main`. dockerd had to be
started again (a stale containerd pid file from the previous container).

## Step 1: is a larger Apertus v1.5 reachable?

`BASE_URL/models` (Public AI, the key from `.env`, never printed) lists 9 ids. Those naming Apertus:

| Id | v1.5 | Size | Variant |
|---|---|---|---|
| `swiss-ai/apertus-v1.5-8b` | yes | 8B | the submission's model |
| `swiss-ai/apertus-v1.5-8b-thinking` | yes | 8B | thinking |
| **`swiss-ai/apertus-v1.5-70b`** | yes | 70B | **MODEL_70B** |
| `swiss-ai/apertus-v1.5-70b-thinking` | yes | 70B | thinking (excluded) |
| `swiss-ai/apertus-8b-instruct` | no | 8B | — |
| `swiss-ai/apertus-70b-instruct` | no | 70B | — |

**Smoke test** (`docs/runs/2026-10-15_rashad_70B-smoke_devA3-devB3`, 10:36 to 10:46 UTC): the last 3 dev task A and
the last 3 dev task B cases through `scripts/paired_run.py` (the CLI's code in-process), arms `70B` (`MODEL` set to
MODEL_70B, nothing else changed) and `8B` (a check that the arm switch sends the right model), `--call-log`, 1 request
per second. Every 70B call failed after its 3 attempts (the CLI's retries for HTTP 429), each attempt answered after
about 26 s with HTTP 429 ("litellm.RateLimitError … 429 Too Many Requests … Received Model
Group=swiss-ai/apertus-v1.5-70b, Available Model Group Fallbacks=None"). The 8B arm answered all 6 (1.3–1.7 s per call;
every response body names `swiss-ai/apertus-v1.5-8b`).

**Probes** (decisions file, written after the smoke test): one minimal request to MODEL_70B (8 tokens, one attempt) at
10:47, 11:02 and 11:17 UTC: HTTP 429 after 27.0, 27.2 and 26.0 s. Public AI's status page (read 10:46) lists the 70B at
about 54–56 % uptime over 30 days, one entry "Down". **Verdict: not reachable; step 2 not run.**

## Step 2: not run

The interleaved run (arms `8B` and `70B`, all 300 dev task A, 300 dev task B and 46 on-topic cases, 1 request per
second) was prepared and written into the decisions file before step 1's result, but not started: the 70B answered no
call. Nothing is adopted.

What is ready for it if the 70B becomes reachable: `scripts/paired_run.py`'s new arm field `model` (sets `MODEL` for
that arm's cases only: the answer, A6's second looks, AP-translate; `src/llm.py`'s run-wide fallbacks kept per arm, so
that one arm's fallback cannot change the other's requests) and `--call-log` (one line per model call: latency,
tokens, the model the response names, cache hit). The command, from `track_2a/`:

    LLM_MIN_INTERVAL=1 python3 scripts/paired_run.py --cases <dev 600 + on-topic 46> --data-dir output/data_s14 \
        --out-dir docs/runs/<date>_rashad_70B-vs-8B_dev600 --min-interval 1.0 --call-log \
        --exclude-paragraphs data/ontopic_neutral/exclusions.json \
        --arm '{"name": "8B"}' --arm '{"name": "70B", "model": "swiss-ai/apertus-v1.5-70b"}'

## Step 3: report

- `technical_report.md`: under the ablation table, "A larger Apertus could not be measured as a reference: Public AI
  lists `swiss-ai/apertus-v1.5-70b`, but on 15 October it refused all 9 calls we sent it over 41 minutes (21 HTTP
  requests, every one HTTP 429) [S15b]."; in Limitations, "**The 8B.** The submission calls Apertus v1.5 8B: the
  organisers' endpoint and model are unknown to us, every rule, prompt and threshold was built and measured on the 8B,
  and the one larger v1.5 model listed (70B) did not answer." PDF 6 pages.
- README unchanged.

## Not done

Step 2 (the 70B-vs-8B run) and the 70B's row in the ablation table: the 70B was not reachable. The final session was
not started (the instruction: Rashad decides when it runs).
