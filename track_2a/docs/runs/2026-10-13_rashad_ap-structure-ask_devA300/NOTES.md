### AP-structure asked after the parser, parser forced off (dev): 0.946 / 0.925 against 0.896 / 0.672 (session 12 step 6)

**What it tests.** What a case gets when the parser cannot split its booklet: session 11's test force "no parser"
(`scripts/paired_run.py`) keeps the case's vote and its contents entry but makes every part fail its checks. All 300
dev task A cases, interleaved, 1 request per second also between a case's own calls, 12:46 to 13:15 UTC; all 644
requests (600 answers and 44 contents calls) answered by one backend (blablador `vllm-0.23.1rc1`).

- **today-noparser**: today's handling: no valid part, so the fallback (embed-e5-small);
- **AP-ask-noparser** (`--ap-structure-a ask-after-parser`, new in session 12): the lane prepares the fallback as usual
  and hands the booklet's page texts to the main process, which asks Apertus to read the contents pages
  (`AP-structure-v1`, one call per booklet, 1,828 + 192 tokens, counted in the booklet's first such case); Apertus's
  entries go through the parser's own heading checks; a part that passes is routed as usual, else the case gets the
  fallback. Unlike session 11's after-parser mode, no case moves to the sequential path.

| Arm | Macro-F1 | Evidence (of 201) | Neutral recall | Input + output tokens per case | Fixes / breaks |
|---|---|---|---|---|---|
| today-noparser | 0.896 | 0.672 (135) | 0.859 | 1,868 + 15.8 | |
| **AP-ask-noparser** | **0.946** | **0.925** (186) | 0.990 | 1,564 + 42.8 | 23 / 8 (sign test p = 0.011) |

Apertus's reading placed the vote for 279 of 300 cases; paths: council 94, summary 63, committee 44, detail 36, law 35,
fallback 28. 0 failed calls, 0 unreadable answers. Session 11's version of the same idea (run 3, falling back to VW)
scored 0.970 / 0.955 on the same cases in another run; the two are not compared (different runs).

**STRUCTURE RULE, dev part** (Macro-F1 at least 0.02 above today's forced handling, evidence not lower): +0.050 and
+0.254: **passes on dev**; val sample next (`2026-10-13_rashad_ap-structure-ask_valA300`). No unforced dev or val case
reaches it (G1/G2 with it on).
