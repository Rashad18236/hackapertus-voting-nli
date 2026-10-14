### A6b: the second look with "related but not settled" (session 15, step 2): the same finding as A6 in all 19 second looks; not adopted

**Arms** (interleaved, 13:30 to 14:10 UTC, two arms alternating which goes first, 1 request per second also between a
case's own calls, CPUs 0–1): `today` = session 15's defaults after step 1 (model S, hedge H, two lanes, **A6 on**) and
`A6b` (`--second-look-a6-prompt A-v6-second-look-b`: only the second look's system prompt differs, adding "including
when it deals with the same subject but does not state the claim's value or its opposite" and "A text that does not
state the claim's value is "nothing", never "different"."). Cases: all 300 dev, 580 val and 94 probe task A cases and
the 46 on-topic neutral cases (`--exclude-paragraphs`), 1,020 in one file. Every answer from one backend (blablador
`vllm-0.23.1rc1`); 0 failed calls, 0 HTTP 429, 0 unreadable answers. **Both arms share every first answer** (1,020 of
1,020, the gateway's cache for the arm sent second); the second looks were never cache hits (A6b's carry 40 more
input tokens each).

`run.json` holds val's numbers (`official_score.json`); dev's and probe's are in `official_score_dev.json` and
`official_score_probe.json`; the rule's numbers in `a6b_rule.json` (`scripts/a6b_rule.py`).

| Set | Macro-F1 A6 / A6b | Evidence | Input + output tokens per case (A6 / A6b) | Second looks | Changed | Fixes / breaks | Gold 2 answered 1 |
|---|---|---|---|---|---|---|---|
| dev (300) | 0.9767 / 0.9767 | 0.990 / 0.990 | 1,258.7 / 1,259.4 + 14.9 | 5 / 5 | 2 / 2 | 2 / 0 and 2 / 0 | 1 / 1 |
| val (580) | 0.9812 / 0.9812 | 0.985 / 0.985 | 1,233.1 / 1,233.8 + 14.9 | 10 / 10 | 9 / 9 | 8 / 1 and 8 / 1 | 4 / 4 |
| probe (94) | 0.9903 / 0.9903 | 1.000 / 1.000 | 1,177.4 / 1,177.8 + 16.6 | 1 / 1 | 1 / 1 | 1 / 0 and 1 / 0 | 0 / 0 |
| on-topic (46) | neutral 27 / 27 | — | — | 3 / 3 | 3 / 3 | — | — |

**Every one of the 19 second looks got the same finding from both prompts**: "different" in dev rows 1016 and 1161
(fixes), val rows 1053, 1151, 1210, 1226, 1309, 1318, 1404, 1467 (fixes) and 950 (break, gold neutral), probe row 1453
(fix) and the on-topic rows 85, 232, 1026 (flips); "nothing" in dev rows 629, 844, 1052 and val row 991. The added
sentences did not move Apertus on any passage it had already called "different".

**A6b RULE** (decisions file, written before the run):

| Condition | A6 | A6b | Holds |
|---|---|---|---|
| (1) val + probe: fixes ≥ A6's − 1 and breaks ≤ A6's | 9 / 1 | 9 / 1 | yes |
| (2) on-topic flips fewer than A6's | 3 (rows 85, 232, 1026) | 3 (the same) | **no** |
| (3) input tokens per case (dev + val + probe) within +0.5 % | 1,235.6 | 1,236.3 (+0.05 %) | yes |

**Verdict: not adopted** ((2) fails); A6's prompt stays.

**Session 14's four still-wrong val cases** (rows 235, 1200, 1347, 1351): still answered neutral in both arms; none of
them got a second look, because their first answer cites no paragraph (A6 asks only after a neutral answer that cites
paragraphs).
