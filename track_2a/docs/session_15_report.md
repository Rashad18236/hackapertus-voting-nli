# Session 15: A6 as a default, three ideas that did not pass, and the stability of the final defaults

Branch `rashad/session-15` from `main` at `4f19500` (session 14 merged in step 0), 2026-10-14 13:13 UTC to 2026-10-15
03:00 UTC, unattended. Status log: `docs/session_15_status.md`; decisions, each written before the run it concerns:
`docs/decisions/2026-10-14-1313_rashad_session-15.md`. Rules as in session 14 (only the 8B on Public AI, one request per
second, one model run at a time; sealed dates never opened; every label from an answer of Apertus; Python decides only
when to ask again).

## In short

STEP-5-AND-FINISH-SUMMARY

**Defaults changed:** **A6 is on** (step 1, a team decision): after a task A answer "neutral" that cites paragraphs,
Apertus looks once more at the cited paragraphs and their neighbours and answers same / different / nothing (→ 0 / 2 /
1). Its known weakness (on-topic passages that do not settle the claim can be answered "different") is in the
technical report's Limitations.

**Not adopted, each by a rule written before its run:**

| Step | Idea | Result against today | Rule |
|---|---|---|---|
| 2 | **A6b**: A6's second look told that "related but not settled" is "nothing" | the same finding as A6 in all 19 second looks: dev 0.977, val 0.981, probe 0.990 in both arms; on-topic flips 3 and 3 (rows 85, 232, 1026) | fails: no fewer on-topic flips |
| 3 | **B1 with the format fixed** (both ballot fields at most 6 words, 40 characters, 64 tokens) | dev 0.892 vs 0.987; 19 unreadable vs 0; +13.1 % input tokens; 2 fixes / 30 breaks | fails (b), (d), (e) on dev; no val run |
| 4 | **B6**: after a task B answer 2, one question "is the claim about the ballot named in the title?" | dev 0.970 vs 0.987; +7.0 % input tokens; 1 fix / 6 breaks | fails (b), (d) on dev; no val run |

No default changed beyond step 1, so there was no combination run.

## Step 0: session 14 merged

PR #22 (`rashad/session-14`, head `ec7a6c1`) was open, a draft, `mergeable_state` clean, with all four checks green. It
was marked ready for review (the first attempt hit a connection reset, so GitHub first refused to merge a draft; the
second attempt succeeded) and merged with a merge commit: `main` = `4f19500`, branch kept; `origin/main` contains
`ec7a6c1`. publish-image on `main` (run 92) succeeded with the tags `latest` and `sha-4f1950002ca0`; `latest` pulls
without a login (an empty Docker configuration): digest `sha256:e3e61af166c0…`, the same image as `sha-4f1950002ca0`,
revision label `4f19500`. The publish workflow also builds `rashad/session-15` (tag `session-15`). dockerd had to be
started again (the container had been restarted).

## Step 1: A6 becomes a default

The team's decision, in its words: "A6 failed its on-topic condition twice by one case (2 of 46 in session 13, 3 of 46
in session 14) and passed every other condition in both runs (val +0.014 and +0.012, probe +0.010, 19 fixes against 2
breaks on 1,254 real cases). The team adopts it on the strength of val and probe and records the on-topic result as its
known weakness: a passage on the claim's subject that does not settle the claim can be answered 'different'." Counted
from the run files, the 19 fixes against 2 breaks include session 13's dev run (1,554 cases); on the 1,254 val and
probe cases they are 18 against 2. Both counts are written next to the sentence in the decisions file and in the
technical report.

`second_look_a6 = True` in `src/cli.py`; `--no-second-look-a6` switches it off. Five tests that assumed A6 off now say
so. pytest: 348 passed, 1 skipped. **G1** against session 14's reference (fake model): every first request and path
identical in all 1,180 cases; A6's second-look requests are added in exactly the 15 cases whose replayed first answer is
neutral with a citation (dev rows 629, 844, 1016, 1052, 1161; val rows 950, 991, 1053, 1151, 1210, 1226, 1309, 1318,
1404, 1467). **G2:** 0 labels and 0 evidence differ, because the fake model answers a second look it has no saved
answer for with an unreadable text, so A6 keeps the first answer; A6's real effect is in the model runs (session 14:
val 0.969 → 0.981, probe 0.981 → 0.990). Technical report: A6 has a row in the role table (1.6 calls per 100 task A
cases, 479 + 8 tokens per call), its negative-results row is gone, and its weakness is in Limitations.

## Step 2: A6b, A6's second look with "related but not settled"

**Arms** (`docs/runs/2026-10-14_rashad_A6b_devA300-valA580-probeA94-ontopic46`, 13:30 to 14:10 UTC, interleaved, 1,020
cases: all 300 dev, 580 val and 94 probe task A cases and the 46 on-topic neutral cases): `today` (A6) and `A6b`
(`--second-look-a6-prompt A-v6-second-look-b`: only the second look's system prompt differs, adding "including when it
deals with the same subject but does not state the claim's value or its opposite" and "A text that does not state the
claim's value is "nothing", never "different"."). One backend; 0 failed calls; 0 unreadable. Both arms share every
first answer (the gateway's cache answers the arm sent second), so they differ exactly by the second look's prompt.

| Set | Macro-F1 A6 / A6b | Evidence | Input + output tokens per case (A6 / A6b) | Second looks | Changed | Fixes / breaks |
|---|---|---|---|---|---|---|
| dev (300) | 0.9767 / 0.9767 | 0.990 / 0.990 | 1,258.7 / 1,259.4 + 14.9 | 5 / 5 | 2 / 2 | 2 / 0 and 2 / 0 |
| val (580) | 0.9812 / 0.9812 | 0.985 / 0.985 | 1,233.1 / 1,233.8 + 14.9 | 10 / 10 | 9 / 9 | 8 / 1 and 8 / 1 |
| probe (94) | 0.9903 / 0.9903 | 1.000 / 1.000 | 1,177.4 / 1,177.8 + 16.6 | 1 / 1 | 1 / 1 | 1 / 0 and 1 / 0 |
| on-topic (46) | neutral 27 / 27 | — | — | 3 / 3 | 3 / 3 | — |

**Every one of the 19 second looks got the same finding from both prompts**: "different" in dev rows 1016 and 1161,
val rows 1053, 1151, 1210, 1226, 1309, 1318, 1404, 1467 (fixes) and 950 (break), probe row 1453 (fix) and the on-topic
rows 85, 232 and 1026 (flips); "nothing" in dev rows 629, 844, 1052 and val row 991. **A6b RULE:** (1) val + probe
fixes 9 ≥ 9 − 1 and breaks 1 ≤ 1: holds; (2) on-topic flips 3, not fewer than A6's 3: **fails**; (3) input tokens
+0.05 %: holds. **Not adopted.** Session 14's four still-wrong val cases (rows 235, 1200, 1347, 1351) stay neutral in
both arms: none of them gets a second look, because their first answer cites no paragraph.

## Step 3: B1 retried with the format fixed

Session 13's B1 (task B names both ballots, says whether they are the same, then labels) was void: an answer stopped at
a field's 80-character limit and ran on in whitespace until the budget ended. The retry `v7-same-ballot-f` changes only
the format: both ballot fields "at most 6 words" and `maxLength` 40, budget 64 tokens.

**Format check** (10 dev cases, `2026-10-14_rashad_format-check-B1f_devB10`): all 10 answers readable, so the arm was not
void (six ballot names cut at 40 characters but closed properly). **Dev run** (`2026-10-14_rashad_B1f_devB300`, 14:11
to 14:36 UTC, 300 task B cases, interleaved, one backend):

| Arm | Macro-F1 | F1 ent / neu / con | Input + output tokens per case | Unreadable | Gold 1 answered 2 (same / cross language) | Fixes / breaks |
|---|---|---|---|---|---|---|
| today | **0.987** | 0.985 / 0.995 / 0.980 | 815.3 + 8.7 | 0 | 1 (1 / 0) | |
| B1f | 0.892 | 0.980 / 0.836 / 0.861 | 922.3 (+13.1 %) + 53.5 | **19** | 20 (6 / 14) | 2 / 30 |

Over 300 cases the endpoint again ended 19 answers inside a string with whitespace, tab or NUL characters (10 of the 30
breaks are their neutral fallbacks). The other 20 breaks are unrelated passages called contradictions: in 17 of them
Apertus wrote `same_ballot: true` with `claim_ballot` a copy of `passage_ballot`. **Language of `claim_ballot`** (30
answers drawn at random, seed 15, judged by hand): 3 unreadable; of 27 readable, 21 are in the reference's language
(19 of them copy `passage_ballot` word for word) and 6 in the claim's language (all cross-language cases; 2 of them are
not ballot names at all). **Fails (b) −0.094, (d) +13.1 %, (e) 19 unreadable on dev: no val run, not adopted.**

## Step 4: B6, a second look on the ballot

After a task B answer 2, one request: a single user message "TITLE: <the reference's first line> / VOTE: <the vote
field> / CLAIM: <the claim>" and the question "Is the claim about the ballot named in the title? Answer in JSON:
{"same_ballot": true|false}." (schema, 16 tokens); false makes the label 1. **Dev run** (`2026-10-14_rashad_B6_devB300`,
14:38 to 14:53 UTC, 300 task B cases, interleaved, one backend; both arms share every first answer):

| Arm | Macro-F1 | F1 ent / neu / con | Input + output tokens per case | Unreadable | Gold 1 answered 2 (same / cross language) | Fixes / breaks |
|---|---|---|---|---|---|---|
| today | **0.987** | 0.985 / 0.995 / 0.980 | 815.3 + 8.6 | 0 | 1 (1 / 0) | |
| today+B6 | 0.970 | 0.985 / 0.971 / 0.953 | 872.7 (+7.0 %) + 12.0 | 0 | 0 | 1 / 6 |

99 second looks (33 per 100 cases, 174 + 10 tokens each), 7 changed answers (2 same-language, 5 cross-language): the
one fix is dev's only targeted error (row 688, a claim about profit tax against the drinking water initiative); the 6
breaks (rows 1063, 1074, 1144, 1223, 1263, 1472) are gold contradictions whose claim is about the reference's own ballot
but states its opposite, and Apertus answers "not about the ballot named in the title". In every dev case the vote field
repeats the title. **Fails (b) −0.017 and (d) +7.0 % on dev: no val run, not adopted.**

STEP-5-SECTION

FINISH-SECTION
