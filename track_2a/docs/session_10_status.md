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

- (13:50) Step 2: cases prepared in one forked worker process (`src/pipeline.py`), one kept connection, booklet
  parsed once, ONNX threads = CPU limit, `src/` compiled in the image; G1/G2 pass; adopted (same-answer rule).
  Task B default back to the whole reference (no cut) by REF SCORE (`docs/runs/2026-10-12_rashad_pipelining_devA300-devB300`).
- (13:50) Step 3: `.github/workflows/publish-image.yml` publishes `ghcr.io/rashad18236/hackapertus-voting-nli`
  (`session-10` and the commit hash from this branch; `latest` only from `main`) and runs the pulled image with the
  organisers' command; both runs green. An anonymous pull from the sandbox works (the package is public) and the
  pulled image answered both examples. **After a merge into `main`, Rashad: check that the workflow ran on `main`
  (Actions -> publish-image) and that `latest` is pullable without logging in.**

## Running

- Step 4: probe set built (`data/probe/`, 94 task A + 94 task B cases from the test rows dated 2021-03-07 and
  2025-09-28; booklets in `output/booklets_probe/`).

## Next

- Step 4: probe without the model (parse, vote match, routing, local time), then with the model (today's defaults,
  both tasks), errors by mechanism.

## Numbers so far

- **Local time per case of `main`** (2 CPUs, warm): task A 0.803 s (fake model delay 1.0 s) / 0.742 s (0.3 s);
  task B 0.985 s / 0.939 s. Task A: PDF reading of each booklet's first case (108 s in all) and a few e5
  embeddings; task B: B-cut's e5 embedding of the 105 long references.
- **Connection set-up per call** (real endpoint, through the sandbox's proxy): a new connection per call
  486 ms mean; one kept connection 1.2 ms after the first call.
- **REF SCORE of `main`:** dev 0.770 (S_A 0.767, S_B 0.774), val 0.761; T_A 0.062, T_B 0.005.
- **After step 2** (one worker process; task B no cut): local time per case A 0.015 s (1.0 s per request) /
  0.300 s (0.3 s), B 0.008 / 0.009 s. REF SCORE dev 0.877 / 0.799, val 0.868 / 0.789.
