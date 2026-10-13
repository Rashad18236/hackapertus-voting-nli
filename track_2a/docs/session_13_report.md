# Session 13: Apertus's reading errors, the evidence page, how Apertus is used

2026-10-13 19:56 UTC to 2026-10-14 (experiments stop 08:00 UTC, everything pushed by 09:00 UTC), branch
`rashad/session-13` from `main` at `c85a119` (PR #20 merged in step 0; draft pull request #21, never merged, no tag),
run unattended by Claude Code for Rashad. Decisions: `docs/decisions/2026-10-13-1956_rashad_session-13.md`; status
log: `docs/session_13_status.md`. The instruction was complete (it ends with "END OF SESSION 13 INSTRUCTION").

## In short

SUMMARY

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

STEP2

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

STEP4

## Step 5: questions for the organisers

`docs/organiser_questions.md`: the evidence page (quote's page, any gold page or first gold page), evidence on a
neutral answer, items beyond five; evaluation hardware; server and model variant; output tokens in K; rate limit and
retries; the task B minimum (0.70 or 0.75).

STEP6

FINISH
