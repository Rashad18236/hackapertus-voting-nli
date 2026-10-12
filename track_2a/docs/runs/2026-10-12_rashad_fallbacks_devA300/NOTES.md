### Fallback levels on dev, forced (session 11 step 2): VW passes dev, BW is lower than today's fallback

**What it tests.** On dev almost every task A case is routed (the claim's opening names a part, the parser finds the
vote and that part), so a fallback is rarely reached and cannot be judged on the cases where it happens. The forced
test (`scripts/paired_run.py`, arm field `force`, test only) puts every case into one fallback situation:

- **"no part"**: the router returns nothing, as for a claim whose opening names no part;
- **"no vote"**: the vote match fails, as for a vote name the parser cannot place.

Arms (interleaved, every case to all four back to back in rotating order, 1 request per second, 20:31 to 21:22 UTC;
all 1,200 answers from one backend, blablador `vllm-0.23.1rc1`):

- **today-routed**: today's defaults, not forced (the reference);
- **today-fallback-nopart**: forced "no part", today's fallback `embed-e5-small` (8 chunks of at most 1,000
  characters from the whole booklet, prompt `A-v3-excerpts`);
- **VW-nopart**: forced "no part", **VW (vote-wide)**: the paragraphs of every valid part of the found vote, each
  marked with its part's name, the 8 most similar to the claim by e5, numbered (`A-v4-vote-wide-L1`: the routed
  prompt with the L1 sentence; routed evidence);
- **BW-novote**: forced "no vote", **BW (booklet-wide)**: the paragraphs of the whole booklet's valid parts, the 8
  most similar (`A-v4-booklet-wide-L1`).

| Arm | Macro-F1 | Evidence (of 201) | F1 ent / neu / con | Input + output tokens per case | p95 time | Fixes / breaks vs today's fallback |
|---|---|---|---|---|---|---|
| today-routed | 0.977 | 0.980 (197) | 0.976 / 0.990 / 0.964 | 1,238 + 14.5 | 2.2 s | 27 / 4 |
| today-fallback-nopart | 0.900 | 0.672 (135) | 0.941 / 0.873 / 0.884 | 1,868 + 15.8 | 12.0 s | |
| VW-nopart | **0.927** | **0.766** (154) | 0.959 / 0.904 / 0.919 | 1,078 + 14.4 | 7.0 s | 21 / 13 |
| BW-novote | 0.857 | 0.647 (130) | 0.921 / 0.833 / 0.818 | 939 + 14.3 | 11.7 s | 17 / 30 |

(Times include the model and the 1 s pacing; the local time per fallback case is measured apart,
`scripts/fallback_local_time.py`.) 0 failed calls, 0 unreadable answers, 0 HTTP 429 in all arms.

**FALLBACK RULE, dev part ("neither is lower on dev").** VW is higher than today's fallback on dev (+0.028 Macro-F1,
+0.094 evidence, −42 % input tokens; neutral recall 1.000 against 0.869); it goes on to the val confirmation. BW is
lower (−0.042 Macro-F1, −0.025 evidence), so **BW fails the rule** and stays in the code, switched off. In its
situation ("no vote") today's fallback stays.

Note: the dev case file is ordered by label (entailments first), so partial scores during a run mean nothing; only
the finished run is scored. today-routed agrees with the session 10 final dev run on the cases checked during the
run (the same request bodies, G1).

Files: one folder per arm (`predictions.jsonl`, `raw_answers.jsonl` with the backend of every call,
`official_score.*`, `settings.json`, `run.json`), `rule_check.json` (`scripts/rule_check.py` with
today-fallback-nopart as the reference: per-arm numbers on all cases and on same-backend cases, fixes and breaks),
`paired_run.log`.
