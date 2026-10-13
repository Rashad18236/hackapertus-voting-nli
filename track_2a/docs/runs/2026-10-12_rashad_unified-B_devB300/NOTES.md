### B-U: task B read like task A, against today on dev (session 10, step 9, optional)

**Version (off by default, `--context-b unified`):** task B's reference as numbered paragraphs (B-cut's text: a
reference over 8,000 characters keeps its first line and the 8 paragraphs most similar to the claim, e5), with task
A's default routed prompt (`A-v4-section-route-L1`) and paragraph schema; the cited paragraphs are not used (task B
evidence stays empty).

**Run.** All 300 dev task B cases, two arms interleaved, one request per second; all answers from one backend.

| arm | Macro-F1 | F1 E / N / C | neutral recall | unreadable | input + output tokens | fixes / breaks |
|---|---|---|---|---|---|---|
| today | 0.967 | 0.985 / 0.963 / 0.951 | 0.929 | 2 | 1,994.2 + 8.4 | |
| B-U | 0.976 | 0.985 / 0.980 / 0.964 | 1.000 | 0 | 1,403.2 + **14.0** | 7 / 4 (p 0.55) |

**Not adopted, and not run on val.** (1) B-U adds 5.6 output tokens per case (its answer names paragraphs before the
label); the session's rules allow no version to add output tokens. (2) Its cut text needs e5 like B-cut (step 2),
whose local time at 0.3 s per request was 0.47 s per case against 0.009 s: estimated REF SCORE S_B, mean over both
delays, 0.816 against today's 0.843 even with this run's Macro-F1 and tokens. The PAIRED RULE (margin 0.01 on val,
tokens ≤ +5 %) was therefore not tried on val. B-U stays in the code, off.
