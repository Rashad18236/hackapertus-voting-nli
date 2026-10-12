# Session 10 status

Updated after every step. If the session is restarted with "continue", work goes on from "Next".

- **Branch:** `rashad/session-10` from `main` at `42b2a3c` (draft pull request, never merged, no tag).
- **Clock:** experiments stop on Tuesday 13 October at 11:30 UTC; everything pushed by 13:00 UTC.

## Done

- (11:45 UTC, Mon) Branch created; status and decisions files; draft PR #17.
- (12:05) Step 0: `docs/official_scoring.md`, CLAUDE.md corrected (formula, minimums, published image,
  separate containers, session 10 stage), `scripts/official_score.py` with `tests/test_official_score.py`.

- (12:45) Step 1: `scripts/local_time.py` (local time = wall-clock of `docker run` minus the union of request
  intervals, fake model in replay mode with a delay), `scripts/connection_time.py`; baseline of `main`
  (`docs/runs/2026-10-12_rashad_local-time-main_devA300-devB300`) and connection set-up on the real endpoint
  (`docs/runs/2026-10-12_rashad_connection-time_devB20`).

## Running

- Step 2 (pipelining): code written (`src/pipeline.py`, `src/memo.py`, `cli.prepare/complete`, keep-alive in
  `src/llm.py`, lazy pypdf, booklet parse cached, ONNX threads = CPU limit, compiled `src/` in the image);
  contract tests and G1/G2 running.

## Next

- Step 2: G1/G2 for `--workers 2` and `--workers 0`, image build, local time again (1.0 s and 0.3 s), REF SCORE,
  B-cut against no cut under REF SCORE.

## Numbers so far

- **Local time per case of `main`** (2 CPUs, warm): task A 0.803 s (fake model delay 1.0 s) / 0.742 s (0.3 s);
  task B 0.985 s / 0.939 s. Task A: PDF reading of each booklet's first case (108 s in all) and a few e5
  embeddings; task B: B-cut's e5 embedding of the 105 long references.
- **Connection set-up per call** (real endpoint, through the sandbox's proxy): a new connection per call
  486 ms mean; one kept connection 1.2 ms after the first call.
- **REF SCORE of `main`:** dev 0.770 (S_A 0.767, S_B 0.774), val 0.761; T_A 0.062, T_B 0.005.
