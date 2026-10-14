# Session 14: A6 confirmed on the final defaults, two worker lanes with model S

Branch `rashad/session-14` from `main` at `3c60943` (session 13 merged in step 0), 2026-10-14 08:32 to 16:00 UTC,
unattended. Status log: `docs/session_14_status.md`; decisions, each written before the run it concerns:
`docs/decisions/2026-10-14-0832_rashad_session-14.md`. Rules as in session 13 (only the 8B on Public AI, one request
per second, one model run at a time; sealed dates never opened; every label from an answer of Apertus).

## In short

SUMMARY_PLACEHOLDER

## Step 0: session 13 merged

PR #21 (`rashad/session-13`, head `b0b88f6`) was open, a draft, `mergeable_state` clean, with all four checks green
(tests, image, publish, pull-and-run). It was marked ready for review and merged with a merge commit: `main` =
`3c60943`, branch kept; `origin/main` contains `b0b88f6`. publish-image on `main` (run 87) succeeded with the tags
`latest` and `sha-3c609435dce7`. `latest` pulls without a login (an empty Docker configuration): digest
`sha256:3572bfdebce7…`, the same image as `sha-3c609435dce7`, revision label `3c60943` = `main`. The publish workflow
also builds `rashad/session-14` (tag `session-14`).

## Step 1: A6 confirmed on the final defaults

**Why again:** in session 13, A6 (a second look after a neutral answer that cites paragraphs) ran on session 12's
defaults (e5 ranker, no hedge) and scored val 0.973 against 0.959 (val 9 fixes / 1 break, dev 1 / 0), +0.8 % input
tokens, and failed only the on-topic condition (2 flips, at most 1 allowed). The team decided to confirm it once more
on the final defaults (model S + hedge H) with the on-topic bar raised to 2, because on val's real neutrals A6 made 1
break in 11 changes and neutral F1 rose 0.957 → 0.981, while the on-topic set is 46 synthetic cases. The flag is
`--second-look-a6` (the instruction's `--second-look-a` names L2, session 9); A6's code is unchanged.

**Run** (`docs/runs/2026-10-14_rashad_A6-confirm_valA580-probeA94-ontopic46`, 08:36 to 09:05 UTC): arms `today`
(session 13's final defaults) and `today+A6`, interleaved, on all 580 val, all 94 probe and the 46 on-topic neutral task
A cases (720), 1,464 calls (1,440 first answers, 14 second looks, 10 AP-translate calls of fallback cases), one backend (blablador `vllm-0.23.1rc1`), 0 failed calls. **Both arms share every first
answer** (720 of 720): in each case the arm sent second repeated the first arm's request and got it from the gateway's
cache, so the two arms differ exactly by A6's second looks.

| Set, arm | Macro-F1 | F1 ent / neu / con | Evidence | Input + output tokens per case | Unreadable | Gold contradiction answered neutral |
|---|---|---|---|---|---|---|
| val, today | 0.9691 | 0.984 / 0.965 / 0.958 | 0.965 | 1,224.9 + 14.7 | 0 | 12 |
| val, today+A6 | **0.9812** | 0.984 / 0.983 / 0.976 | 0.985 | 1,233.1 + 14.9 | 0 | 4 |
| probe, today | 0.9808 | 1.000 / 0.966 / 0.977 | 0.985 | 1,171.8 + 16.5 | 0 | 1 |
| probe, today+A6 | **0.9903** | 1.000 / 0.983 / 0.989 | 1.000 | 1,177.4 + 16.6 | 0 | 0 |
| dev (session 13's run, session 12's defaults), today / today+A6 | 0.983 / 0.987 | | 0.985 / 0.990 | 1,240.4 / 1,242.1 + 14.7 | 0 / 0 | 1 / 0 |

**Second looks:** 14 (val 10 = 1.7 per 100 cases, probe 1 = 1.1 per 100, on-topic 3), 0 unreadable, 0 failed, 314–592
input + 8 output tokens each. 13 of 14 changed the answer to a contradiction ("different"): **val 8 fixes** (rows 1053,
1151, 1210, 1226, 1309, 1318, 1404, 1467), **val 1 break** (row 950, gold neutral), **probe 1 fix** (row 1453), and
**all 3 on-topic second looks** (rows 85, 232, 1026). One kept neutral (row 991, gold neutral).

**A6 CONFIRMATION RULE** (written before the run):

| Condition | Result | Holds |
|---|---|---|
| (a) val Macro-F1 at least +0.005 | 0.9691 → 0.9812 (+0.0121) | yes |
| (b) probe Macro-F1 not below today | 0.9808 → 0.9903 | yes |
| (c) fixes > breaks over val + probe, sign test p ≤ 0.10 | 9 / 1, p = 0.011 (one-sided; 0.021 two-sided) | yes |
| (d) mean input tokens per case at most +3 % (val + probe) | 1,217.5 → 1,225.3 (+0.64 %) | yes |
| (e) no more unreadable answers than today | 0 / 0 | yes |
| (f) at most 2 on-topic answers flip away from neutral | **3** (rows 85, 232, 1026; neutral 31 → 28 of 46) | **no** |
| (g) A6 never fires more than once per case | one record per case; tokens per case equal its recorded calls | yes |

**Verdict: A6 is not adopted** ((f) fails by one case); `second_look_a6` stays off. Rows 232 and 1026 flipped in
session 13 too; row 85 is new. What A6 does well is clear: it removes 8 of val's 12 "gold contradiction answered
neutral" errors and probe's one; what it does badly is the same move on a passage that is on topic but does not settle
the claim, where every one of its 3 on-topic looks said "different".

**Session 12's 15 val errors answered neutral** (`2026-10-13_rashad_final-s12_val1160`; another run, so indicative):
today fixes 3 (rows 341, 1025, 1159); today+A6 fixes 11 (also 1053, 1151, 1210, 1226, 1309, 1318, 1404, 1467); still
wrong with A6: rows 235, 1200, 1347, 1351; one new error answered neutral in both arms (row 1175).

## Step 2: two worker lanes with model S

STEP2_PLACEHOLDER

## FINISH

FINISH_PLACEHOLDER
