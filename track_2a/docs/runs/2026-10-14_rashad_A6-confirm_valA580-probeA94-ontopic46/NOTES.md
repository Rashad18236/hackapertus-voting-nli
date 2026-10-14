### A6 confirmed on the final defaults (session 14, step 1): passes six of seven conditions, fails the on-topic bar by one case; not adopted

**Arms** (interleaved, 08:36 to 09:05 UTC, two arms alternating which goes first, 1 request per second also between a
case's own calls, CPUs 0–1): `today` = session 13's final defaults (model S, hedge H, A6 off) and `today+A6`
(`--second-look-a6`: a neutral answer that cites paragraphs gets one more call, `A-v6-second-look`, with the cited
paragraphs and their neighbours; its finding same / different / nothing → 0 / 2 / 1). Cases: all 580 val task A cases,
all 94 probe task A cases and the 46 on-topic neutral cases (`--exclude-paragraphs data/ontopic_neutral/exclusions.json`),
720 in one file. Every answer and second look from one backend (blablador `vllm-0.23.1rc1`); 0 failed calls, 0 HTTP 429.
**Both arms share every first answer** (720 of 720 identical): in each case the arm sent second repeated the first arm's
request word for word and got it from the gateway's cache, so the arms differ only by A6's second looks.

`run.json` holds val's numbers (starter's scorer, `official_score.json`); probe's are in `official_score_probe.json`;
mean tokens and times in `run.json` are over all 720 cases. The rule's numbers: `a6_rule.json`
(`scripts/a6_confirmation.py`).

| Set, arm | Macro-F1 | F1 ent / neu / con | Evidence | Input + output tokens per case | Unreadable | Gold 2 answered 1 | Fixes / breaks |
|---|---|---|---|---|---|---|---|
| val, today | 0.9691 | 0.984 / 0.965 / 0.958 | 0.965 (387 / 401) | 1,224.9 + 14.7 | 0 | 12 | |
| val, today+A6 | **0.9812** | 0.984 / 0.983 / 0.976 | 0.985 (395 / 401) | 1,233.1 + 14.9 | 0 | 4 | 8 / 1 |
| probe, today | 0.9808 | 1.000 / 0.966 / 0.977 | 0.985 (64 / 65) | 1,171.8 + 16.5 | 0 | 1 | |
| probe, today+A6 | **0.9903** | 1.000 / 0.983 / 0.989 | 1.000 (65 / 65) | 1,177.4 + 16.6 | 0 | 0 | 1 / 0 |

**A6's second looks:** 14 (val 10, probe 1, on-topic 3; 1.7 per 100 val cases, 1.1 per 100 probe cases), 0 unreadable,
0 failed, each 314–592 input + 8 output tokens. 13 of 14 changed the answer ("different" → contradiction): val 8 fixes
(rows 1053, 1151, 1210, 1226, 1309, 1318, 1404, 1467) and 1 break (row 950, gold neutral), probe 1 fix (row 1453), and
all 3 on-topic second looks (rows 85, 232, 1026). One look kept neutral (row 991, gold neutral).

**A6 CONFIRMATION RULE** (decisions file, written before the run):

| Condition | Result | Holds |
|---|---|---|
| (a) val Macro-F1 at least +0.005 | 0.9691 → 0.9812 (+0.0121) | yes |
| (b) probe Macro-F1 not below today | 0.9808 → 0.9903 | yes |
| (c) fixes > breaks over val + probe, sign test p ≤ 0.10 | 9 / 1, p = 0.011 one-sided (0.021 two-sided) | yes |
| (d) input tokens per case (val + probe, 674 cases) at most +3 % | 1,217.5 → 1,225.3 (+0.64 %) | yes |
| (e) unreadable answers not more than today | 0 and 0 (first answers and second looks) | yes |
| (f) on-topic answers flipped away from neutral at most 2 | **3** (rows 85, 232, 1026; today neutral 31 of 46, A6 28) | **no** |
| (g) A6 at most once per case | one raw record per case and arm, 0 second looks in today, every case's tokens equal its recorded calls | yes |

**Verdict: not adopted** ((f) fails by one case); `second_look_a6` stays off. Rows 232 and 1026 also flipped in
session 13's dev run (`2026-10-13_rashad_prompts-A_devA300-ontopic46`); row 85 is new. Session 13's dev numbers for
A6 (that run, on session 12's defaults): today 0.983, today+A6 0.987, 1 fix, 0 breaks, 2 on-topic flips.

**Session 12's 15 val errors answered neutral** (`2026-10-13_rashad_final-s12_val1160`; another run, indicative):
today fixes 3 (rows 341, 1025, 1159), today+A6 fixes 11 (also 1053, 1151, 1210, 1226, 1309, 1318, 1404, 1467); still
wrong with A6: rows 235, 1200, 1347, 1351; one new error answered neutral in both arms (row 1175).
