# Session 10: score what the organisers score

2026-10-12 11:42 UTC to 2026-10-13 13:00 UTC, branch `rashad/session-10` from `main` at `42b2a3c` (draft pull
request #17, never merged, no tag), run unattended by Claude Code for Rashad. Decisions:
`docs/decisions/2026-10-12-1142_rashad_session-10.md`; status log: `docs/session_10_status.md`; the organisers'
formula and our REF SCORE: `docs/official_scoring.md`.

## In short

**Finished:** steps 0 to 8, the optional step 9 on dev, and FINISH. Nothing was dropped for time. The sealed test
dates were never run, parsed or opened; `data/test/`, the splits file and the scorer are unchanged; no key was
printed, logged or committed. Every label comes from an answer of Apertus; Python wrote 6 labels in the final runs (2,128 cases): the neutral fallback for 6 task B answers that held no JSON object (3 dev, 3 val); 0 in task A, 0 on the probe, 0 failed calls.

**Local time and tokens per case, `main` → final** (local time: `scripts/local_time.py`, the image with 2 CPUs,
fake model replaying saved answers after 1.0 s / 0.3 s; tokens: input + output from real runs on dev):

| | `main` at `42b2a3c` (before) | final (published image `sha-421d8c804677`) |
|---|---|---|
| Task A local time per case, 1.0 / 0.3 s per request | 0.803 / 0.742 s | 0.017 s / 0.154 s |
| Task B local time per case, 1.0 / 0.3 s per request | 0.985 / 0.939 s | 0.010 s / 0.0068 s |
| Task A tokens per case (dev, input + output) | 1,237.8 + 14.5 | 1,237.8 + 14.5 |
| Task B tokens per case (dev, input + output) | 1,231.2 + 8.4 (B-cut) | 1,994.2 + 8.4 (whole reference) |
| Task A Macro-F1 / evidence, task B Macro-F1 (dev) | 0.980 / 0.980, 0.967 (session 9) | 0.983 / 0.980, 0.967 |
| Peak memory, task A (4 GB limit) | not measured on `main` (2.2 GiB in session 8) | 2.3 GiB |
| **REF SCORE dev**, 1.0 / 0.3 s per request | 0.770 / 0.770 | **0.870 / 0.824** |
| **REF SCORE val** (dev's local times, as for `main`), 1.0 / 0.3 s | 0.761 / 0.762 | **0.860 / 0.813** (val's own local times: 0.873 / 0.888) |

**Defaults changed, each by its rule:**

| Change | Rule | Evidence | Commit |
|---|---|---|---|
| Cases prepared in background worker processes while a request is in flight; one kept connection; each booklet parsed once; ONNX threads = the CPU limit; `src/` compiled in the image (step 2) | same answers (G1, G2) and local time per case falls for both tasks | G1/G2 pass; A 0.803 → 0.015 s, B 0.985 → 0.008 s at 1.0 s per request | `628f5b0`, `150ae44` |
| Task B sends the whole reference again (no B-cut) (step 2) | B-cut against no cut under REF SCORE with measured times and tokens | mean S_B over both delays dev 0.827 vs 0.821, val 0.821 vs 0.817 | `83e7fab` |
| A vote name the title match cannot place is placed by meaning (e5, lead ≥ 0.04) (step 8) | G1 and G2 unchanged on dev and val | G1/G2 pass; swap test 182 of 264 right, 0 wrong | `6204a67` |
| Two worker processes ("lanes"), each owning whole booklets | same answers and local time | G1/G2 pass; task A at 0.3 s per request 0.316 → 0.206 s per case | `6204a67`, `2509882` |

**Tried and not adopted:** P-short and P-short+K4 (task A, step 5; fail on dev), K4 (passes on dev, fails on
val), BP-short and BP-short+B-cut4 (task B; fail on dev), **B-cut4** (passes the TOKEN RULE on dev and val with −55 %
tokens but lowers REF SCORE through local time), CS and SL (step 6; fail the PAIRED RULE), B-U (step 9; adds output
tokens and local time). Step 7: without `response_format` 0 of 100 answers unreadable; nothing to change.

**Probe** (the test rows of 2021-03-07 and 2025-09-28, 94 + 94 cases, published image): task A **0.960**,
evidence **0.908**; task B **0.971**; REF SCORE 0.850 / 0.777, val's level.
83 of 94 task A cases routed; the parser misses the first vote of `2025_09_28_fr` (8 fallbacks, 3 of the 6 evidence
misses): reported, not fixed.

**The Python rule "neutral with a citation → contradiction"** (offline only, from today's saved answers; never in
`src/`): dev 0.9833 → 0.9834, val 0.9589 → 0.9728, on-topic neutral set 31 → 28 of 46 answered neutral (all 3 changes
wrong).

**Each version on the on-topic neutral set** (46 dev cases whose gold passage was removed; expected neutral;
indicative): today 31 of 46 answered neutral (0.674), CS 28 (0.609), SL 31 (0.674).

**Not verified:** the organisers' hardware, model server and its speed (local time depends on it: at 0.3 s per
request task A's PDF reading no longer hides behind the requests); the other teams' best values (REF SCORE uses
ours); whether their proxy counts "in flight" as our fake model does; a cold start of the freshly pulled image (the
first read of the 470 MB e5 file was slow on this sandbox's disk); the parser gap on one probe booklet
(`2025_09_28_fr`) is reported, not fixed.

## Details, step by step

Every run folder is under `docs/runs/`; every decision with its reason is in the decisions file.

**Step 0, the organisers' score.** `docs/official_scoring.md` writes down the formula (Score = 0.4 S_B + 0.6 S_A;
S_A = 0.50 Macro-F1 + 0.20 evidence + 0.15 T + 0.15 K; S_B = 0.70 Macro-F1 + 0.15 T + 0.15 K) and the rule for local
time (container wall-clock minus the time a request is in flight). `scripts/official_score.py` computes **REF
SCORE**: the same formula with reference "best" values fixed before any measurement (600 / 800 tokens, 0.05 / 0.005 s
local time per case for task A / B).

**Step 1, local time of `main`** (`2026-10-12_rashad_local-time-main_devA300-devB300`, `scripts/local_time.py`): the
image with the organisers' command, 2 CPUs, 4 GB, a fake model replaying saved real answers after 1.0 s or 0.3 s.
Task A 0.803 / 0.742 s per case (PDF reading of each booklet's first case: 108 s over the dev set), task B 0.985 /
0.939 s (B-cut's e5 embedding). A new connection per call cost 486 ms through the sandbox's proxy, a kept one 1.2 ms
(`2026-10-12_rashad_connection-time_devB20`, real endpoint, short references only).

**Step 2, pipelining** (`2026-10-12_rashad_pipelining_devA300-devB300`; `src/pipeline.py`, `src/cli.py` `prepare()` /
`complete()`, `src/llm.py` kept connection, `src/parse.py` and `src/memo.py` caches, ONNX threads = CPU limit, `src/`
compiled in the image). Threads were tried first and dropped: PDF reading and the ONNX session start hold Python's
lock (up to 2.45 s), so the request thread waited. One forked worker process: G1 and G2 pass, task A 0.015 / 0.300 s,
task B 0.008 / 0.009 s per case. Failure tests: a case that raises in the worker, a worker that dies, a timeout, a
killed run (each answered or written once). B-cut against the whole reference under REF SCORE with measured times:
the mean over both delays favours the whole reference (dev 0.827 vs 0.821, val 0.821 vs 0.817), so task B's default
went back to it. Later the same day: **two lanes** (`2026-10-12_rashad_lanes_devA300-devB300`), each owning whole
booklets: task A at 0.3 s per request 0.316 → 0.206 s; G1/G2 pass.

**Step 3, the published image.** `.github/workflows/publish-image.yml` builds `linux/amd64` from `track_2a/`, pushes
`ghcr.io/rashad18236/hackapertus-voting-nli` (tags: the commit, `session-10` from this branch, `latest` from `main`),
then pulls it on a fresh runner and runs the organisers' command against the fake model without internet. The
package is public; an anonymous pull works.

**Step 4, probe** (`2026-10-12_rashad_probe-defaults_probe188`; `data/probe/`, `scripts/make_probe.py`): the test
rows of two of the five test dates, chosen as text before any parsing; the other three dates stay sealed.

**Step 5, fewer tokens** (`2026-10-12_rashad_fewer-tokens-{A_devA300,A_valA580,B_devB300,B_valB580}`). Task A: P-short
0.670 and P-short+K4 0.619 fail on dev; K4 passes on dev (0.990, −35 % input tokens) and fails on val (0.944 vs
0.959). Task B: BP-short 0.667 (29 unreadable) and BP-short+B-cut4 0.718 fail on dev; B-cut4 passes the TOKEN RULE on
dev (0.987 vs 0.967) and val (0.961 vs 0.957) with −55 % input tokens but costs e5 local time (0.066 / 0.730 s per
case against 0.0075 / 0.0067 s): REF SCORE, mean over both delays, dev 0.832 vs 0.843, val 0.812 vs 0.837. Not
adopted (rule recorded before the task B runs). Break-even: if the best team's task B local time were above about
0.027 s per case, B-cut4 would win.

**Step 6, reading** (`2026-10-12_rashad_reading-A_{devA300-ontopic46,valA580}`): the endpoint enforces `anyOf`;
the on-topic neutral set (`data/ontopic_neutral/`, 46 dev cases whose gold passage was removed); CS fails (on-topic
neutral share 0.609 vs 0.674); SL fails the PAIRED RULE (val +0.0034, sign test p = 0.25). Python rule offline only.

**Step 7, no `response_format`** (`2026-10-12_rashad_response-format-off_devA100`): 0 of 100 answers unreadable;
nothing changes.

**Step 8, vote names by meaning** (`src/contexts/section_route.py`, `tests/test_vote_meaning.py`,
`scripts/vote_language_check.py`): with other languages' names swapped in, 182 of 264 placed right, 0 wrong (lead ≥
0.04); G1/G2 unchanged on dev and val. Risk: names of votes not in the booklet are placed in 12 % of cases (never
asked by the dataset).

**Step 9 (optional), B-U** (`2026-10-12_rashad_unified-B_devB300`): 0.976 vs 0.967 on dev but +5.6 output tokens
and e5 local time; not adopted, val skipped.

**FINISH.** The final defaults through the published image `sha-421d8c804677` (task A and task B in separate
containers, one request per second, every answer from one backend): `2026-10-12_rashad_final-defaults_dev600`,
`…_val1160`, `…_probe188`; local time of the same image in each folder (`local_time_*.json`, `ref_score.json`). New
replay reference `2026-10-12_rashad_prompt-snapshot-final-s10_devAB-valA` (1,180 requests; the replay reproduces the
final runs exactly). Checks: 222 tests pass (1 skipped), `scripts/build_docs.py --check` passes, `technical_report.pdf` has 6 pages; the clean-machine workflow result for the final push is in the status file.

**For Rashad.** After a merge into `main`: check that `publish-image` ran on `main` and that
`ghcr.io/rashad18236/hackapertus-voting-nli:latest` pulls without logging in; that is the tag to submit. Before the
deadline: team name, members, project name in `technical_report.md` and the README, and the licence (the report
says CC-BY-4.0, `LICENSE` is Apache-2.0).
