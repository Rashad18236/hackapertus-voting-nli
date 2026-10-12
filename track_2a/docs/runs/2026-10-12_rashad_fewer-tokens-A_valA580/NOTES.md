### K4 against today on val: K4 fails (session 10, step 5)

**Run.** All 580 val task A cases, two arms interleaved (`scripts/paired_run.py`, one request per second), Public AI
`apertus-v1.5-8b`; all 1,160 answers from one backend (blablador). 0 failed calls, 0 HTTP 429. K4 was the only
version that passed the TOKEN RULE on dev (`2026-10-12_rashad_fewer-tokens-A_devA300`); P-short and P-short+K4
failed there.

| arm | Macro-F1 | F1 E / N / C | evidence | neutral recall | unreadable | input + output tokens | fixes / breaks |
|---|---|---|---|---|---|---|---|
| today | 0.959 | 0.976 / 0.955 / 0.946 | 0.955 | 1.000 | 0 | 1,205.8 + 14.5 | |
| K4 | 0.944 | 0.971 / 0.937 / 0.924 | 0.938 | 0.994 | 0 | 804.2 + 14.3 | 6 / 15 (p 0.08) |

**TOKEN RULE: K4 fails on val** (Macro-F1 −0.015, rule at most −0.005; evidence −0.017, rule at most −0.010;
neutral recall, unreadable answers and input tokens (−33.3 %) pass). **No task A version is adopted in step 5.**
The instruction's second dev run with K6 was for a K4 that fails on dev; K4 passed on dev and failed on val, so
there is no K6 run.

**REF SCORE** (`scripts/official_score.py`; val numbers of this run; local time from the step 5 measurements of K4,
0.215 / 0.837 s per case, and step 2's one-worker image for today, 0.015 / 0.300 s): today S_A 0.894 at 1.0 s per
request and 0.769 at 0.3 s; K4 S_A 0.804 and 0.778. K4 would also lower the mean over both delays (0.791 against
0.832): its embedding of every routed part costs local time, and its Macro-F1 and evidence fall on val.
