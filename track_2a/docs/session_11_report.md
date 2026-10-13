# Session 11: unseen booklets, Apertus as parser, a fast server, memory, task B tokens

2026-10-12 20:10 UTC to 2026-10-13 10:30 UTC, branch `rashad/session-11` from `main` at `014f691` (draft pull
request #18, never merged, no tag), run unattended by Claude Code for Rashad. Decisions:
`docs/decisions/2026-10-12-2010_rashad_session-11.md`; status log: `docs/session_11_status.md`.

## In short

PENDING-SUMMARY

## Details, step by step

Every run folder is under `docs/runs/`; every decision with its reason is in the decisions file. Model runs: Public
AI's `swiss-ai/apertus-v1.5-8b` (from `.env`), at most one request per second, one run at a time, every comparison
one interleaved run with an arm "today"; every answer of the session came from one backend (blablador,
`vllm-0.23.1rc1`). From 21:35 UTC model runs used CPUs 0–1 and timing measurements CPUs 2–3 (pinned), so both could
go on at once.

**Step 1, parser coverage** (`2026-10-12_rashad_parser-coverage_booklets93`; no model). Every federal booklet from
2016 to 2026 in de, fr and it (93 PDFs, the sealed dates removed before any download), kept outside the repository.
`scripts/parser_coverage.py` checks each booklet and, per date, the three languages against each other (same votes,
same parts, start pages within one page). Causes fixed, most frequent first, each with a unit test on a synthetic
page or PDF: the older contents layout used until mid-2018 (20 booklets), PDFs pypdf could not read because a font
descriptor names two font programs (7), an arguments heading lost in the text layer, and per-part validity (a part
that passes its own checks is used even when another part of its vote fails). Booklets complete 64 → 88 of 93; votes
passing every check 178 → 244 of 249, all 249 with a usable part; cross-language disagreements 2 → 0; probe cases
routed 83 → 90 of 94 (`2025_09_28_fr`'s first vote now found). Remaining: the joint 2017-09-24 pension vote has no
detail heading in any language (3 booklets), one heading of `2018_09_23_it` is lost in its text layer, and
`2025_09_28_fr` has no arguments entry (its parts are valid). G1/G2 pass; adopted.

**Step 2, better fallbacks** (`2026-10-12_rashad_fallbacks_{devA300,valA300}`). VW (vote-wide: the 8 paragraphs of
the vote's valid parts most similar to the claim, each with its part's name) and BW (booklet-wide: the 8 most similar
paragraphs of the booklet), both with the routed prompt and L1's sentence under new version names, and a forced test
in `scripts/paired_run.py` ("no part": the router returns nothing; "no vote": the vote match fails):

| Forced, Macro-F1 / evidence / input + output tokens | dev (300) | val (balanced 300) |
|---|---|---|
| today, routed (not forced) | 0.977 / 0.980 / 1,238 + 14.5 | — |
| today's fallback (embed-e5-small), "no part" | 0.900 / 0.672 / 1,868 + 15.8 | 0.875 / 0.593 / 1,827 + 15.8 |
| VW, "no part" | 0.927 / 0.766 / 1,078 + 14.4 | 0.873 / 0.716 / 1,079 + 14.4 |
| BW, "no vote" | 0.857 / 0.647 / 939 + 14.3 | 0.856 / 0.627 / 951 + 14.5 |

FALLBACK RULE (val: Macro-F1 ≥ +0.02 and evidence ≥ +0.05 over today's fallback; not lower on dev): **VW fails**
(−0.002 on val), **BW fails** (lower on dev and val). Both stay off; no routed case could change; the probe run
"today against the new defaults" was not needed. Local work per fallback case (`fallback_local_time.json`): routed
0.29 s, today's fallback 1.74 s, VW 1.31 s, BW 1.61 s.

**Step 3, Apertus in the parsing roles.**

Apertus was tried in the two roles Python plays before the answer: naming the part a claim's opening refers to
(AP-claim, one call per claim, `src/ap_parse.py`) and reading a booklet's contents (AP-structure, one call per
booklet, cached; its entries go through the parser's own heading checks before any part is used). Every parsing call
counts in the case's tokens (a booklet's contents call in its first case).

| Role, run | Accuracy | Macro-F1 / evidence (vs the arm it replaces) | Tokens per case, input + output (of which parsing) | In the final system? |
|---|---|---|---|---|
| AP-structure, 93 booklets (3a) | 78.7 % of passing current-layout votes with all four pages equal to the parser's (per field 0.79–0.84); older layout law page 30 % | — | 1,796 + 176 per booklet | no: needs ≥ 95 % (HYBRID RULE) |
| AP-structure, parser off, dev 300 (run 3) | vote placed and checked for 277 of 300 | 0.970 / 0.955 (VW 0.886 / 0.687) | 1,478 + 43.1 (268 + 28.5) | no: part a fails |
| AP-claim (AP-part), reworded openings, dev 150 (run 2) | 78.7 % of parts equal to the original opening's | 0.967 / 0.880 (VW 0.894 / 0.670) | 1,383 + 63.4 (236 + 49.0) | PENDING-APPART |
| AP-all, dev 300 (run 1) | part = rules' part for 89.0 %; vote placed for 93.0 % | 0.960 / 0.891 (today 0.977 / 0.980) | 1,655 + 90.9 (502 + 76.5) | never (the step's rule) |
| AP-all, probe 94 (run 1) | part = rules' 89.4 %; vote placed 91.5 % | 0.951 / 0.877 (today 0.971 / 0.954) | 1,383 + 71.6 (346 + 57.4) | never |

AP-all's local time (replay of run 1's answers through the image, 0.3 s per request): 0.822 s per case against 0.101 s for today, since its calls during preparation force the sequential path. Step 3b (no model): with Apertus's restated statement (the claim without its
opening, in the booklet's language) as the search text of cut parts, the 9 gold cases among the 18 cut
cross-language dev and probe cases keep their gold paragraph among the 8 (net gain 0, needs ≥ 5), so run 4 was not
run. Step 3d: the endpoint accepts an image part, but Apertus's answer does not name the page's printed heading.

**Step 4, a fast server** (`2026-10-12_rashad_local-time-step4_devA300`; no model). Profile at 0.3 s per request:
the two lanes need 145–155 s each for 90 s of requests; PDF reading 107 s and e5 embedding of long parts 177 s over
both lanes. Found in the profile: two lanes each started onnxruntime with every CPU, so 4 spinning threads shared 2
CPUs. Changes, each a switch, measured in alternating rounds (the model run beside it shifted single values by about
±0.015 s): light-first (cases that need no e5 first; e5 loaded only when needed), lazy pages (a page read when first
asked for; cache key = the PDF's SHA-256; one open reader per process) and SHARE_CPUS (each lane its share of the CPUs
for onnxruntime). Local time per case at 0.3 s: today 0.202, light-first 0.177, lazy 0.184, SHARE_CPUS 0.124, all three
**0.101**. G1/G2 pass with all three: **adopted** (SAME-ANSWER RULE). Not built: shared reading of the first booklet
(the time to the first request is 3.1 s, 0.010 s per case). The target of 0.05 s at 0.3 s is not reached: what is
left is PDF reading (about 1.3 s per booklet in pure-Python pypdf) and e5 embedding of long parts (about 3 s per
part). Quantised e5 for task A was checked first: it changes the 8 paragraphs of 50 of 75 cut cases, so it cannot
pass G1.

**Step 5, memory.**

PENDING-STEP5

**Step 6, task B tokens.**

PENDING-STEP6

**FINISH.**

PENDING-FINISH

**Dropped for time:** PENDING-DROPPED

**Not verified:** PENDING-NOTVERIFIED
