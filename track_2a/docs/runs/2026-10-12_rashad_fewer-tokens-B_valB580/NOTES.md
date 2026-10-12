### B-cut4 against today on val, and B-cut4's REF SCORE (session 10, step 5)

**Run.** All 580 val task B cases, two arms interleaved, one request per second, Public AI `apertus-v1.5-8b`; all
1,160 answers from one backend (blablador); 0 failed calls. B-cut4 was the only task B version that passed the
TOKEN RULE on dev (`2026-10-12_rashad_fewer-tokens-B_devB300`).

| arm | Macro-F1 | F1 E / N / C | neutral recall | unreadable | input + output tokens | fixes / breaks |
|---|---|---|---|---|---|---|
| today | 0.957 | 0.984 / 0.945 / 0.942 | 0.911 | 3 | 1,957.2 + 8.9 | |
| B-cut4 | 0.961 | 0.976 / 0.955 / 0.951 | 0.950 | 1 | 891.5 + 9.4 | 9 / 7 |

**TOKEN RULE: B-cut4 passes on val too** (Macro-F1 +0.004; fewer unreadable answers; input tokens −54.4 %). It is
the only qualifying version of step 5.

**Local time** (`local_time_*.json`: `scripts/local_time.py`, the current image with two lanes, 2 CPUs, all 300 dev
task B cases, measured back to back with nothing else running): B-cut4 **0.066 s** per case at 1.0 s per request
and **0.730 s** at 0.3 s (it embeds every paragraph of the 218 references over 3,000 characters with e5); today
0.0075 s and 0.0067 s. Peak memory with B-cut4 1.8 GB (today: no model in memory).

**REF SCORE S_B** (`ref_score.json`; Macro-F1 and tokens of each set's run, local time from dev):

| | K | T at 1.0 s | S_B at 1.0 s | T at 0.3 s | S_B at 0.3 s | **mean** |
|---|---|---|---|---|---|---|
| dev, today | 0.400 | 0.667 | 0.837 | 0.746 | 0.849 | **0.843** |
| dev, B-cut4 | 0.897 | 0.076 | 0.837 | 0.007 | 0.826 | 0.832 |
| val, today | 0.407 | 0.667 | 0.831 | 0.746 | 0.843 | **0.837** |
| val, B-cut4 | 0.888 | 0.076 | 0.817 | 0.007 | 0.807 | 0.812 |

**Decision: B-cut4 is not adopted.** It qualifies under the TOKEN RULE, but it lowers REF SCORE (mean over both
delays) on dev and val: what it gains in tokens (K +0.49) and Macro-F1 it loses in local time (T −0.59 at 1.0 s).
The rule recorded before these runs: a qualifying version is adopted only if REF SCORE, mean over the two measured
delays, does not fall. The outcome depends on the other teams: REF SCORE takes 0.005 s as the best task B local time
per case; if the best is above about 0.027 s, B-cut4 would win at 1.0 s per request. B-cut4 stays in the code
(`--context-b cut4`).
