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

- (14:00) Step 4: probe set `data/probe/` (94 task A + 94 task B cases, test rows dated 2021-03-07 and 2025-09-28);
  offline (5 of 6 booklets parse, 83 of 94 routed), local time, and today's defaults through the image
  (`docs/runs/2026-10-12_rashad_probe-defaults_probe188`).

- (14:25) Step 5, task A on dev (`docs/runs/2026-10-12_rashad_fewer-tokens-A_devA300`, all 300 answers from one
  backend): today 0.980 / evidence 0.980 / 1,238 input tokens; P-short 0.670 (cites a paragraph, then answers
  neutral) and P-short+K4 0.619 fail; K4 0.990 / 0.975 / 808 passes the TOKEN RULE on dev. Local time: K4 0.215 s
  per case at 1.0 s per request (today 0.015), 0.837 s at 0.3 s (today 0.300); B-cut4 0.107 / 0.744 s (today 0.008 /
  0.009).

- (15:00) Step 5, task A on val: K4 fails (0.944 vs 0.959, evidence 0.938 vs 0.955); nothing adopted for task A.
- (15:05) Step 7: 100 dev task A cases without response_format: 0 unreadable; nothing changes.
- (14:45) Step 8: vote names by meaning (e5, lead ≥ 0.04) when the title match fails; G1/G2 unchanged; adopted.
- (15:50) Step 6: anyOf enforced; CS fails (on-topic neutral share), SL fails on val (+0.0034, p 0.25); nothing
  adopted. Python rule offline: dev +0.0001, val +0.014, on-topic 3 of 3 changes wrong.
- Lanes (two worker processes owning whole booklets): G1/G2 pass; task A at 0.3 s per request 0.316 → 0.206 s per
  case; at 1.0 s 0.015 → 0.018 (the busy lanes slow the request loop); peak memory 2.3 GB.

- (16:00) Lanes default: two (one on a single CPU); lower priority did not help and was taken out.
- (17:05) Step 5, task B: BP-short fails on dev; B-cut4 passes the TOKEN RULE on dev (0.987 vs 0.967) and val (0.961
  vs 0.957) with −55 % tokens, but lowers REF SCORE (local time 0.066 / 0.730 s per case vs 0.0075 / 0.0067 s):
  not adopted. Step 5 changes no default.

## Running

- Step 9 (optional): B-U against today on dev (`docs/runs/2026-10-12_rashad_unified-B_devB300`).

## Next

- FINISH: publish, final runs through the published image (dev 600, val 1,160, probe 188), local time of the final
  image, new replay reference, report, PDF, CLAUDE.md, session report.

## Numbers so far

- **Local time per case of `main`** (2 CPUs, warm): task A 0.803 s (fake model delay 1.0 s) / 0.742 s (0.3 s);
  task B 0.985 s / 0.939 s. Task A: PDF reading of each booklet's first case (108 s in all) and a few e5
  embeddings; task B: B-cut's e5 embedding of the 105 long references.
- **Connection set-up per call** (real endpoint, through the sandbox's proxy): a new connection per call
  486 ms mean; one kept connection 1.2 ms after the first call.
- **REF SCORE of `main`:** dev 0.770 (S_A 0.767, S_B 0.774), val 0.761; T_A 0.062, T_B 0.005.
- **After step 2** (one worker process; task B no cut): local time per case A 0.015 s (1.0 s per request) /
  0.300 s (0.3 s), B 0.008 / 0.009 s. REF SCORE dev 0.877 / 0.799, val 0.868 / 0.789.
- **Probe** (today's defaults): task A Macro-F1 0.960, evidence 0.908, 1,232 + 14 tokens; task B 0.961, 1,831 + 9
  tokens; 0 fallback labels; REF SCORE 0.846 (1.0 s) / 0.775 (0.3 s). Errors: A 4 (spread over mechanisms), B 4 (all
  neutral called contradiction).
