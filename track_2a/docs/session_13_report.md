# Session 13: Apertus's reading errors, the evidence page, how Apertus is used

2026-10-13 19:56 UTC to 2026-10-14 (experiments stop 08:00 UTC, everything pushed by 09:00 UTC), branch
`rashad/session-13` from `main` at `c85a119` (PR #20 merged in step 0; draft pull request #21, never merged, no tag),
run unattended by Claude Code for Rashad. Decisions: `docs/decisions/2026-10-13-1956_rashad_session-13.md`; status
log: `docs/session_13_status.md`. The instruction was complete (it ends with "END OF SESSION 13 INSTRUCTION").

## In short

**Finished:** step 0 and steps 1 to 6, the combination and FINISH; nothing was dropped for time (the last model call
at 01:01 UTC, the last measurement at 02:05; the stop was 08:00). At 01:16 the session's worker restarted (dockerd and a
local-time measurement were lost and restarted) and the instruction was delivered again, word for word the same; no
step was repeated. The sealed test dates were never run, parsed, downloaded or opened;
`data/test/`, the splits and the scorer are unchanged; no key was printed, logged or committed; no booklet PDF or text
is committed; no new local model; no translation model. Every label comes from an answer of Apertus; Python wrote 1
label in the final runs (2,128 cases): the neutral fallback for one val task B answer it could not read (a bare `1`).

**Defaults changed, each by its rule:** the evidence page hedge **H** (step 3: under the strictest page rule, the
first page of the gold passage, +18 hits over dev, val and probe; nothing worse; labels and requests unchanged) and
**model S as the ranker** for task A (step 6: val 0.961 → 0.969, REF SCORE higher at 0.3 and 1.0 s per request; task
A's peak memory 2,287 → 206 MiB). **Not adopted:** the five task A prompts (all fail on dev), the second look A6 (best
val arm, 0.973 against 0.959, but it turned 2 of 46 on-topic neutrals into contradictions; its rule allows 1), task B's
B2 (val 0.974 against 0.968 and no unrelated passage answered contradiction, but 9 fixes against 6 breaks and one more
unreadable answer than today), B1 (void: unreadable), B3 and B4. Everything stays in the code, switched off.

**Each step:**

| Step | What | Result | Rule, outcome |
|---|---|---|---|
| 0 | merge session 12 | PR #20 merged (`c85a119`; it was a draft, marked ready first); PR #19 closed; `latest` published | — |
| 1 | task A prompts A1–A5, second look A6 (dev 300 + 46 on-topic, val 580) | dev: no prompt better than today; val (report only): A5 0.971, A3 0.970, A6 0.973 vs 0.959 | PAIRED / SECOND-LOOK RULE: **none passes** (A6 fails the on-topic condition by one case) |
| 2 | task B prompts B1, B2, B4, selector B3 (dev 300, val 580) | B1 void; B2 val 0.974 vs 0.968, the targeted error 8 → 0 | PAIRED RULE: **none passes** (B2 fails (c) and (e)) |
| 3 | evidence page hedge H (offline) | rule 3 hits +18 (dev 116 → 119, val 223 → 236, probe 44 → 46) | H RULE: **default** |
| 4 | report section "How Apertus is used" | roles, ablation, errors (10 routing + 13 reading on val A), negative results | — |
| 5 | questions for the organisers | `docs/organiser_questions.md` (8 questions) | — |
| 6 | model S on val | val A 0.961 → 0.969; REF SCORE 0.9243 / 0.9166 → 0.9269 / 0.9192 | S RULE: **default** |
| — | combination H+S (val A) | 0.969 vs 0.959, equal to S alone | kept |

**Session 12's targeted val errors in the final runs** (another run, so indicative): of the 15 task A errors
answered neutral, 3 are fixed (rows 341, 1025, 1159: routing errors S now finds) and 1 new (row 1175); of the 9 task B
errors answered contradiction, none is fixed and 1 new (row 396). Val errors: task A 23 → 18, task B 18 → 19.


## Step 0: session 12 merged

PR #20 (`rashad/session-12`, tip `668114f`, all four checks green, `mergeable_state` clean) was a draft; GitHub
refuses to merge a draft, so it was marked ready for review and merged with a merge commit: `main` = `c85a119`, branch
kept. `kaan/robustness-experiments` is an ancestor of `main`, so PR #19 was closed with the instruction's comment. The
publish workflow on `main` (run 74) succeeded: `latest` and `sha-c85a119b409a`. `origin/main` contains `668114f`.

## Step 1: task A, contradictions answered neutral

Session 12's 23 val task A errors: 15 answered neutral (13 gold contradiction, 2 gold entailment; the instruction's
"15 of 23"), of which 9 are reading errors and 6 routing errors (the gold passage was not in the part as sent).

**Dev** (`docs/runs/2026-10-13_rashad_prompts-A_devA300-ontopic46`; 300 dev cases and the 46 on-topic neutral cases,
7 arms, one backend):

| Arm | Macro-F1 | F1 ent / neu / con | Evidence | Tokens in + out | Unreadable | Gold 2 answered 1 | Fixes / breaks | On-topic neutral (of 46) | Fails |
|---|---|---|---|---|---|---|---|---|---|
| today | 0.983 | 0.980 / 0.995 / 0.975 | 0.985 | 1,240.4 + 14.7 | 0 | 1 | | 32 | |
| A1 `A-v6-says` | 0.902 | 0.975 / 0.843 / 0.888 | 0.970 | 1,291.2 + 75.6 | 6 | 0 | 5 / 29 | 13 | b, d, e, g |
| A2 `A-v6-residual` | 0.973 | 0.971 / 0.990 / 0.959 | 0.980 | 1,258.4 + 14.7 | 0 | 2 | 1 / 4 | 27 | b, g |
| A3 `A-v6-mismatch` | 0.980 | 0.975 / 0.995 / 0.970 | 0.990 | 1,337.1 + 26.1 | 0 | 0 | 1 / 2 | 19 | d, g |
| A4 `A-v6-opposite` | 0.964 | 0.975 / 0.969 / 0.946 | 0.985 | 1,334.1 + 53.3 | 2 | 0 | 2 / 8 | 28 | b, d, e, g |
| A5 `A-v6-words` | 0.983 | 0.980 / 0.995 / 0.975 | 0.990 | 1,251.4 + 16.4 | 0 | 0 | 1 / 1 | 25 | g |
| today+A6 | 0.987 | 0.980 / 1.000 / 0.980 | 0.990 | 1,242.1 + 14.7 | 0 | 0 | 1 / 0 | 30 (2 flips) | g |

**Val** (`docs/runs/2026-10-13_rashad_prompts-A_valA580`; the instruction's arms, for the report only):

| Arm | Macro-F1 | F1 ent / neu / con | Evidence | Tokens in + out | Unreadable | Gold 2 answered 1 | Fixes / breaks | Of the 15: fixed / new |
|---|---|---|---|---|---|---|---|---|
| today | 0.959 | 0.974 / 0.957 / 0.946 | 0.960 | 1,210.7 + 14.7 | 0 | 14 | | 0 / 1 |
| A5 | 0.971 | 0.971 / 0.983 / 0.959 | 0.978 | 1,221.6 + 16.4 | 0 | 5 | 10 / 3 | 7 / 0 |
| A3 | 0.970 | 0.974 / 0.977 / 0.958 | 0.988 | 1,307.2 + 25.9 | 0 | 2 | 13 / 7 | 9 / 0 |
| today+A6 | **0.973** | 0.974 / 0.981 / 0.964 | 0.983 | 1,219.9 + 14.9 | 0 | 5 | 9 / 1 | 8 / 0 |

A6: second looks per 100 cases 0.3 (dev) and 2.1 (val); answers changed 1 (dev), 11 (val: 9 fixes, 1 break, 1 wrong
to wrong); on-topic neutrals flipped 2 (rows 232, 1026). **Verdicts:** A1–A5 fail the PAIRED RULE on dev; A6 passes
(a)–(e) on dev and val (val +0.014; fixes / breaks 10 / 1 over both, p = 0.006; tokens +0.8 %) and fails (g) by one
on-topic case. **Nothing is adopted in step 1.** For the team: A6 is the best val arm and costs 0.8 % tokens; the rule
the instruction set keeps it off, because the on-topic set (indicative only, 46 cases) shows it can turn a missing
passage into a contradiction.

## Step 2: task B, unrelated passages answered contradiction

Session 12's 18 val task B errors: 9 answered contradiction (8 gold neutral, 1 gold entailment; the instruction's "9 of
18"). **B3 offline** (`docs/runs/2026-10-13_rashad_b3-picks_offline`): selector T with the reference's first line
changes the picks of 383 of 539 long references (71 %; bar 10 %): an arm. **Format check**
(`docs/runs/2026-10-13_rashad_format-check-B_devB5`): **B1 void** (one of 5 answers stops `passage_ballot` at the
schema's 80 characters and then produces whitespace until its budget ends: unreadable), so B1+B3 is not run; B1's
claim_ballot was in the reference's language in 3 of its 4 readable answers.

**Dev** (`docs/runs/2026-10-13_rashad_prompts-B_devB300`) and **val** (`docs/runs/2026-10-13_rashad_prompts-B_valB580`):

| Arm | Set | Macro-F1 | F1 ent / neu / con | Tokens in + out | Unreadable | Gold 1 answered 2 (same / cross language) | Fixes / breaks | Of the 9: fixed / new |
|---|---|---|---|---|---|---|---|---|
| today | dev | 0.987 | 0.985 / 0.995 / 0.980 | 815.3 + 8.7 | 0 | 1 (1 / 0) | | |
| B2 `v7-unrelated` | dev | 0.983 | 0.985 / 0.990 / 0.974 | 841.3 + 7.6 | 0 | 0 | 1 / 2 | |
| B3 `cut4-tf` | dev | 0.980 | 0.975 / 0.985 / 0.980 | 839.6 + 8.8 | 0 | 1 (1 / 0) | 0 / 2 | |
| B4 `v7-claim-first` | dev | 0.980 | 0.980 / 0.985 / 0.974 | 851.3 + 39.3 | 5 | 0 | 1 / 3 | |
| today | val | 0.968 | 0.982 / 0.963 / 0.958 | 819.5 + 9.5 | 1 | 8 (4 / 4) | | 0 / 1 |
| B2 | val | **0.974** | 0.982 / 0.973 / 0.968 | 845.5 + 8.0 | 2 | **0** | 8 / 4 | **8** / 0 |
| B3 | val | 0.966 | 0.976 / 0.966 / 0.955 | 840.0 + 9.5 | 1 | 7 (4 / 3) | 4 / 5 | 4 / 6 |

**Verdicts:** B4 fails on dev ((b), (d), (e)); B3 fails (a) and (b). **B2** passes (a) (val +0.0068), (b), (d)
(+3.2 %) but fails **(c)** (9 fixes, 6 breaks over dev and val, p = 0.30) and **(e)** (2 unreadable answers, a bare
`1` without JSON, against today's 1). **Nothing is adopted in step 2.** For the team: B2 removes every val case of
the targeted error (8 → 0), at the cost of 4 val cases where a supported or contradicted claim becomes neutral.


## Step 3: evidence page hedge H

`docs/runs/2026-10-13_rashad_evidence-pages_offline` (no model calls). Counts of gold 0/2 cases:

| Set | Items | Text hit | Rule 1 (quote's page) | Rule 2 (any gold page) | Rule 3 (first gold page) |
|---|---|---|---|---|---|
| dev (201) | today / **H** | 197 / **198** | 197 / **198** | 192 / **193** | 116 / **119** |
| val (401) | today / **H** | 385 / 385 | 385 / 385 | 379 / 379 | 223 / **236** |
| probe (65) | today / **H** | 63 / 63 | 63 / 63 | 63 / 63 | 44 / **46** |

Rule 3 would cost about 40 % of today's evidence score: the gold passage often starts on the page before the
paragraph Apertus cites. H (today's items first; the paragraph before the first cited one when that one opens its
page and the part continues from an earlier page; then the whole cited page; at most five; never a page the text is
not on) is at least as good under every rule on every set and +18 under rule 3; labels identical; G1 identical; G2
differs only in evidence (414 dev and val cases). **H passes its rule.**

## Step 4: "How Apertus is used" (technical report, section 4)

Written into `technical_report.md` (section 4, about one page; the PDF stays at 6 pages): the organisers' two
sentences, the thesis, a role table (calls per 100 cases and tokens on the final dev run), the ablation (closed book
0.435; the embedding baseline 0.834 / 0.662; whole booklet 0.858; Apertus does all parsing 0.960 / 0.891 with +34 %
tokens and 8× local time; routed today), the error analysis and a table of what was tried and not adopted, this
session's arms included. The instruction's "embed-only early baseline 0.435 evidence" joins two runs: 0.435 is the
closed-book Macro-F1, the embedding baseline is E5's arm; both rows are given with their own numbers.

**Error analysis** (`docs/runs/2026-10-13_rashad_error-types_valAB`, `scripts/error_types.py`, offline): of session
12's 23 val task A errors, 10 are routing errors (gold passage not in what Apertus read: law 5, detail 3, committee 1,
fallback 1) and 13 reading errors; all 18 task B errors are reading errors. Apertus, asked once per reading error
(31 calls, gold label given), names: task A direction or negation 6, scope 5, number or date 2; task B other ballot or
topic 6, number or date 6, scope 4, direction 1, other 1. The session's adopted ranker S fixes 3 of the 10 routing
errors on val (the long part's passage among its 8 paragraphs).


## Step 5: questions for the organisers

`docs/organiser_questions.md`: the evidence page (quote's page, any gold page or first gold page), evidence on a
neutral answer, items beyond five; evaluation hardware; server and model variant; output tokens in K; rate limit and
retries; the task B minimum (0.70 or 0.75).

## Step 6: model S on val

Run because step 2's val run ended at 23:37 (before 04:00). `docs/runs/2026-10-13_rashad_S-val_valA580` (val task A;
task B's requests do not depend on the ranker, checked by G1, so its part of REF SCORE is today's val task B):

| | Macro-F1 | Evidence | Tokens in + out | Local time per case, 1.0 / 0.3 s (val, median of 3) | REF SCORE 1.0 / 0.3 s |
|---|---|---|---|---|---|
| today | 0.961 | 0.963 | 1,210.7 + 14.7 | 0.0091 / 0.0088 s | 0.9243 / 0.9166 |
| **S** | **0.969** | **0.968** | 1,224.9 + 14.7 | 0.0073 / 0.0071 s | **0.9269 / 0.9192** |

S fixes 6 cases, breaks 1 (all six fixes are long law or detail parts whose passage e5 left out). **S RULE passes;
S is the default ranker.** e5 stays in the image (task B's selector T). On dev, S's local time at 0.3 s per request is
0.016 s against e5's 0.127 s (three rounds each). Memory grid and image size: in FINISH.


## FINISH

**Final defaults through the published image** `ghcr.io/rashad18236/hackapertus-voting-nli:sha-54032b4a7970` (built
from `54032b4`; tag `session-13` at the time; task A and B in separate containers; every answer from one backend; 0
failed calls), session 12's final image → session 13's (different runs):

| | dev | val | probe |
|---|---|---|---|
| Task A Macro-F1 / evidence | 0.977 / 0.980 → **0.973 / 0.985** | 0.961 / 0.960 → **0.969 / 0.965** | 0.971 / 0.969 → **0.981 / 0.985** |
| Task B Macro-F1 | 0.987 → **0.987** | 0.969 → **0.968** | 0.977 → **0.977** |
| Task A tokens per case (input + output) | 1,240 + 14.7 → 1,251 + 14.8 | 1,211 + 14.7 → 1,225 + 14.7 | 1,169 + 16.5 → 1,172 + 16.6 |
| Task B tokens per case | 815 + 8.7 → 815 + 8.8 | 820 + 9.4 → 820 + 9.4 | 789 + 8.6 → 789 + 8.9 |
| Task A local time per case, 1.0 / 0.3 s per request | 0.017 / 0.160 s → **0.016 / 0.017 s** (repeat 0.015; at 0.1 s 0.364 → 0.025 s) | 0.009 / 0.010 → 0.008 / 0.007 s | 0.040 / 0.028 → 0.035 / 0.027 s |
| Task B local time per case, 1.0 / 0.3 s | 0.012 / 0.010 → 0.008 / 0.009 s | 0.007 / 0.007 → 0.006 / 0.007 s | 0.015 / 0.016 → 0.014 / 0.015 s |
| **REF SCORE**, 1.0 / 0.3 s | 0.903 / 0.845 → **0.915 / 0.911** | 0.913 / 0.907 → **0.917 / 0.912** | 0.897 / 0.896 → **0.903 / 0.901** |

Task A paths (dev / val / probe): routed 299 / 577 / 90, fallback bm25-ap 1 / 3 / 4 (with 1 / 2 / 3 translation calls);
no case needed AP-part or AP-structure. Python wrote 1 of 2,128 labels (val task B, a bare `1`). Local time measured
01:17 to 02:05 UTC through the same image (`scripts/local_time.py`, 2 CPUs pinned to CPUs 2–3, 4 GB).

**Memory** (`docs/runs/2026-10-14_rashad_memory-grid-final-s13_grid24`): both tasks write every response at 4g, 2g,
1.5g, 1g, 768m and 512m, with 2 CPUs and with 1. Task A peak 2,287 → 206 MiB (two worker processes; 130 MiB with one);
task B 1,164 MiB (e5 for selector T; 51 MiB below 1.5 GiB). Image size 2,216 MB before and after (e5 stays for task B).
For the team: below 2.5 GiB task A still runs one worker process (a limit set for e5); with S the second one would fit
and keep local time low at fast models (0.016 against 0.126 s per case at 0.1 s per request).

**Replay reference:** `docs/runs/2026-10-14_rashad_prompt-snapshot-final-s13_devAB-valA` reproduces the final dev and
val runs exactly (0 of 1,180 labels or evidence differ); it is G1/G2's anchor and `scripts/local_time.py`'s default.

**Checks:** 347 tests (pytest: 346 passed, 1 skipped; unittest the same after one test pinned its ranker); self-checks;
`scripts/build_docs.py --check`; `scripts/check_format.py` on the six final prediction files (2,128 responses): no
errors; pypdf 6.17.0; `.env.example` unchanged (no new variable). `latest` pulls without a login: digest
`sha256:a6213d70ea55…`, the same image as `sha-c85a119b409a`, i.e. `main` at `c85a119`.

**Not done:** nothing from the instruction. Left for the team: A6 (val +0.014, misses its rule by one on-topic case),
B2 (val +0.007, removes the targeted error, fails on breaks and one unreadable answer), and the one-lane memory limit
with model S.
