# Session 12: every remaining idea with a real chance

2026-10-13 10:35 UTC to 2026-10-14 (experiments stop 02:00 UTC), branch `rashad/session-12` from `main` at `37904b3`
(draft pull request #20, never merged, no tag), run unattended by Claude Code for Rashad. Decisions:
`docs/decisions/2026-10-13-1035_rashad_session-12.md`; status log: `docs/session_12_status.md`.

The instruction arrived cut off in step 3 ("… H: session 11's selector …; B"); steps 4 to 8 and FINISH were read from
the instruction's own references, and the reading was written down before any of them ran (decisions file).

## In short

FINAL_SUMMARY

**Each step, before → after:**

| Step | What | Result | Rule, outcome |
|---|---|---|---|
| 0 | Kaan's `kaan/robustness-experiments` | merged whole, everything off; dataset README unchanged (no label definitions) | G1/G2 and 292 tests pass |
| 1 | model S (`static-similarity-mrl-multilingual-v1`, tokenizers + numpy) and rankers without the endpoint | S equals the reference library (3e-8); first cited paragraph among the 8 best, cross-language: e5 0.980, **S 0.993**, S+BM25 0.985, BM25 0.945; S's local time at 0.3 s per request 0.018 s per case against e5's 0.144, peak memory 200 against 2,286 MiB | **R = S** (256 dimensions) |
| 2 | memory guard (no embedding model below its need or without its files) | both tasks answer every case at 4g, 2g, 1.5g, 1g, 768m, 512m, with 2 CPUs and 1 (before: 1 GiB lost 24 task A and 190 task B responses) | **default**; nothing changes at 1.5 GiB and above |
| 3 | task B selectors B-R, H, B-BM25 (dev, against T) | T 0.987; B-R 0.973; H 0.993 but +13 % tokens; B-BM25 0.967 | TASK B RULE 2: **none passes**; T stays |
| 4 | model S in place of e5 in task A (dev) | 0.973 / 0.970 against 0.980 / 0.980 (2 breaks, 0 fixes, both long "detail" parts) | S RULE (a): **fails by one case**; off |
| 5 | fallback bm25-ap: BM25 on the claim, translated by Apertus across languages (forced) | dev 0.956 / 0.736 vs 0.900 / 0.672; val 0.957 / 0.755 vs 0.875 / 0.588 | FALLBACK RULE: **default** |
| 6 | AP-structure asked after the parser (parser forced off) | dev 0.946 / 0.925 vs 0.896 / 0.672; val 0.939 / 0.917 vs 0.872 / 0.593 | STRUCTURE RULE: **default** |
| 7 | final defaults' memory and local time | in FINISH below | — |
| 8 | an image without e5 | not done: no default uses S | — |

FINAL_TABLE

## Details, step by step

Every run folder is under `docs/runs/`; every decision with its reason is in the decisions file. Model runs: Public
AI's `swiss-ai/apertus-v1.5-8b` (from `.env`), at most one request per second, one run at a time, every comparison
one interleaved run with an arm "today", the backend of every call recorded; every answer and every parsing or
translation call of the session came from one backend (blablador, `vllm-0.23.1rc1`). Model runs used CPUs 0–1 and
timing measurements CPUs 2–3 (pinned).

**Step 0, Kaan's branch.** `kaan/robustness-experiments` (BM25, bm25-mt, hybrid retrievers; the strategies; a local
translation module) already contained `main`; merged whole with no conflict. Everything in it is off by default; its
translation packages are in `requirements-experiments.txt`, which the image does not read, so ctranslate2 and
sentencepiece stay out of the image and `requirements.txt`. G1, G2 and all 292 tests passed. The dataset README
(repository commit `fc2b276`, last changed 2026-10-08) still has a field table and no label definitions beyond the
names; the prompts keep the official guide's wording.

**Step 1, model S and the rankers** (`2026-10-13_rashad_rankers-S_offline`, `2026-10-13_rashad_S-cost_devAB600`; no
model). `src/static_embed.py`: S is a table of token vectors (105,879 × 1,024); a text's vector is the mean of its
tokens' vectors, normalised; computed with tokenizers and numpy only, the safetensors file read by its documented
layout; the table cut to its first 256 dimensions (108 MB) when the image is built, in a build stage of its own, from
the repository at a pinned commit. On 50 dev claims its vectors equal sentence-transformers' at 256 and 1,024
dimensions (largest difference 3e-8; checked in a separate environment on the development machine only).
`src/rankers.py` switches the ranker of long parts, the fallback's chunks and (for B-R) long task B references.

| Ranker (session 11 final runs' answers, dev + val + probe) | first cited paragraph among the 8 best: all / same language / cross-language | among the 4 best (all) | cut parts: gold passage still among the 8 (of 44) |
|---|---|---|---|
| e5 (today) | 0.987 / 1.000 / 0.980 | 0.937 | 44 |
| **S** | **0.993 / 0.995 / 0.993** | 0.935 | 44 |
| S, 1,024 dimensions | 0.995 / 0.995 / 0.995 | 0.937 | 44 |
| BM25 (claim as it is) | 0.962 / 0.995 / 0.945 | 0.836 | 42 |
| S+BM25 | 0.988 / 0.995 / 0.985 | 0.913 | 44 |
| e5+BM25 | 0.983 / 1.000 / 0.975 | 0.927 | 44 |

R = S (its cross-language share at 8 is above e5's; the rule allowed 3 points below). Through the image, with S
everywhere, task A's local time per case at 1.0 / 0.3 / 0.1 s per request is 0.016 / 0.018 / 0.043 s against e5's
0.017 / 0.144 / 0.365 s (two rounds at 0.3 s), and peak memory falls from 2,286 to 200 MiB (task B 1,164 → 82 MiB). A
vote name in another language is placed by meaning with S only with a lead of 0.50 (S's largest wrong lead in session
10's test is 0.499; 71 of 264 names placed, none wrong; e5 places 182).

**Step 2, memory guard** (`2026-10-13_rashad_memory-guard_grid48`; no model). Before the worker processes start, each
embedding model whose need (e5 1.5 GiB, S 0.5 GiB) is above the container's memory limit, or whose files are missing,
is marked unusable for the run; an exception while loading or running a model (MemoryError included) marks it the
same way. Without the model a long part sends its first 8 paragraphs, the fallback ranks chunks by BM25 alone, and a
long task B reference is sent whole; each such case is marked in its raw answer and counted in the log. Through the
image, with today's defaults: every response written at 4g, 2g, 1.5g, 1g, 768m and 512m, with 2 CPUs and with 1, for
both tasks (peak 90 MiB for task A and 51 MiB for task B under the guard). Session 11's image lost 24 task A and 190
task B responses at 1 GiB to the out-of-memory kill. With S no guard is needed at any of these limits.

**Step 3, task B selectors** (`2026-10-13_rashad_taskb-selectors-s12_devB300`). All four keep T's rule (a reference
over 3,000 characters becomes its first line plus 4 paragraphs).

| Arm (dev, 300) | Macro-F1 | Input + output tokens | Long references: neutral called contradiction | Fixes / breaks vs T |
|---|---|---|---|---|
| T (today) | 0.987 | 815 + 8.6 | 1 | |
| B-R (S on the whole paragraph) | 0.973 | 923 + 8.7 | 6 (5 cross-language) | 3 / 7 |
| H (session 11) | **0.993** | 923 + 8.6 | 0 | 2 / 0 |
| B-BM25 (Apertus translates across languages) | 0.967 | 1,039 + 26.2 | 6 (all cross-language) | 2 / 8 |

TASK B RULE 2 (Macro-F1 ≥ T + 0.005, tokens ≤ T + 10 %): B-R and B-BM25 fail on Macro-F1; H passes on Macro-F1
(+0.0067) but needs 13 % more tokens. By REF SCORE that costs more than it gains (+0.005 for Macro-F1, −0.017 for tokens
in S_B), so T stays; no val run was spent. On val (session 11) T makes 9 of its 19 errors as neutral long references
called contradiction; none of these versions is shown to fix that on dev without a cost.

**Step 4, model S in task A** (`2026-10-13_rashad_S-and-fallbacks_devA300`). Only 24 of the 300 requests differ (23
long parts, 1 fallback); S answers 21 of them right, e5 23 (rows 31 and 1052, long "detail" parts). S RULE (a)
(Macro-F1 and evidence at most 0.005 below today's) fails: −0.0067 and −0.010. (b) passes (forced fallback +0.013) and
(c) passes clearly. **Trade-off for the team:** at 0.3 s per request, S's local time would raise T for task A from
0.35 to 1.0 of its reference (REF SCORE S_A about +0.10) for a Macro-F1 cost of one case in 300 on dev; at 1.0 s per
request the two are equal. The rule set before the run decided; `--ranker S` stays available.

**Step 5, bm25-ap fallback** (dev in the same run as step 4; val `2026-10-13_rashad_bm25ap-fallback_valA300`). A case
section-route cannot route gets the booklet's 8 chunks with the best BM25 score for the claim; for a claim in
another language than the booklet, Apertus first translates it (`AP-translate-v1`, about 128 + 42 tokens, counted in
the case) and BM25 ranks with the translation; the reading call gets the claim as it is. Forced to the fallback:

| | dev (300) | val sample (300) |
|---|---|---|
| today's fallback (e5) | 0.900 / 0.672 / 1,868 + 15.8 | 0.875 / 0.588 / 1,827 + 15.6 |
| model S's fallback | 0.913 / 0.677 / 2,385 + 16.1 | — |
| **bm25-ap** | **0.956 / 0.736** / 2,591 + 44.3 (23 fixes, 6 breaks) | **0.957 / 0.755** / 2,609 + 45.4 (29 / 5) |

(Macro-F1 / evidence / input + output tokens per case.) FALLBACK RULE (+0.02 and evidence not lower, dev and val):
passes; default. Kaan's bm25-mt with a local translation model (not allowed in the image) scored 0.963 / 0.771 on dev.

**Step 6, AP-structure asked after the parser** (`2026-10-13_rashad_ap-structure-ask_{devA300,valA300}`). When the
rules name a part but the parser gives no valid part for the vote, the worker process hands the booklet's pages to
the main process, which asks Apertus to read the contents (one call per booklet, about 1,825 + 192 tokens, counted in
its first case); Apertus's entries go through the parser's heading checks, and a part that passes is routed.
Session 11's version moved every case to the sequential path; this one keeps the worker processes. Parser forced off:
dev 0.946 / 0.925 against 0.896 / 0.672 (23 / 8), val 0.939 / 0.917 against 0.872 / 0.593 (25 / 5): STRUCTURE RULE
passes; default. With it on, G1/G2 change only the 4 cases bm25-ap changes; no dev or val case asks for the contents.
Two faults found and fixed before the default changed: the mode switched AP-part off (fixed, tested), and an error in
the bm25-ap fallback would have cost a case its call (it now goes on to embed-e5-small).

FINAL_DETAILS

## What did not work or was not done

- Model S as task A's ranker: one case short of its rule (above); B-R for task B: worse across languages.
- H for task B: better Macro-F1 by 2 cases, 13 % more tokens.
- An image without e5 (step 8): nothing in the defaults uses S.
- No separate probe run for steps 5 and 6: the final runs include the probe with the final defaults.
- The queue error at 13:15 (two val runs waited on a pattern their own command line contained) cost two minutes;
  the runs were restarted before any request.
