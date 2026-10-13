# Session 11: unseen booklets, Apertus as parser, a fast server, memory, task B tokens

2026-10-12 20:10 UTC to 2026-10-13 10:30 UTC, branch `rashad/session-11` from `main` at `014f691` (draft pull
request #18, never merged, no tag), run unattended by Claude Code for Rashad. Decisions:
`docs/decisions/2026-10-12-2010_rashad_session-11.md`; status log: `docs/session_11_status.md`.

## In short

**Finished:** steps 1 to 6 and FINISH. Nothing in the step list was dropped for time; run 4 (step 3) and val runs
for AP-structure were not needed by their rules. The sealed test dates were never run, parsed, downloaded or opened;
`data/test/`, the splits file and the scorer are unchanged; no key was printed, logged or committed; no booklet PDF or
booklet text is committed by the new scripts. Every label comes from an answer of Apertus; Python wrote 1 label in the
final runs (2,128 cases): the neutral fallback for 1 val task B answer it could not read; 0 failed calls.

**Each step, before → after:**

| Step | Before | After | Rule, outcome |
|---|---|---|---|
| 1 parser coverage (93 booklets 2016–2026) | 64 booklets complete, 178 votes pass, 2 cross-language disagreements; probe routed 83/94 | **88** complete, **244 of 249** votes pass, 0 disagreements; probe routed **90/94** | same answers (G1/G2): **adopted** |
| 2 fallbacks (forced) | embedding fallback dev 0.900 / 0.672, val 0.875 / 0.593 | VW dev 0.927 / 0.766, val 0.873 / 0.716; BW lower | FALLBACK RULE: both **fail** (VW val −0.002, needs +0.02) |
| 3 Apertus as parser | rules + Python parser | AP-part after the rules (unknown openings: dev 0.967 vs 0.894, val 0.926 vs 0.876) | HYBRID RULE: **AP-part adopted**; AP-structure fails (78.7 % < 95 %); AP-all reported only |
| 4 local time, task A at 0.3 s per request | 0.202 s per case | **0.101 s** (light-first, lazy pages, shared onnxruntime threads) | SAME-ANSWER RULE: **adopted**; target 0.05 s not reached |
| 5 memory, task A, 2 CPUs | needs 3 GiB (2 GiB: OOM) | **1.5 GiB** (one lane under 2.5 GiB) | SAME-ANSWER RULE: **adopted**; target 2 GiB reached |
| 6 task B tokens | 1,994 input tokens per case (dev), 0.967 | **815**, 0.987 (selector T) | TASK B RULE on dev and val: **adopted** |

**Final defaults through the published image** (`sha-bb2d08fea0f1`, the `session-11` tag; task A and B in separate
containers; every answer from one backend), session 10's final image → session 11's (different runs):

| | dev | val | probe |
|---|---|---|---|
| Task A Macro-F1 / evidence | 0.983 / 0.980 → **0.980 / 0.985** | 0.959 / 0.955 → **0.959 / 0.955** | 0.960 / 0.908 → **0.971 / 0.954** |
| Task B Macro-F1 | 0.967 → **0.987** | 0.961 → **0.968** | 0.971 → **0.977** |
| Task A tokens per case (input + output) | 1,238 + 14.5 → 1,238 + 14.5 | 1,206 + 14.5 → 1,206 + 14.5 | 1,232 + 14.4 → 1,136 + 14.5 |
| Task B tokens per case | 1,994 + 8.4 → **815 + 8.7** | 1,957 + 9.0 → **820 + 9.3** | 1,831 + 8.3 → **789 + 8.9** |
| Task A local time per case, 1.0 / 0.3 s per request | 0.017 / 0.154 → 0.018 / 0.155 (repeat 0.108) | 0.012 / 0.034 → 0.008 / 0.010 | 0.038 / 0.248 → 0.026 / 0.237 |
| Task B local time per case, 1.0 / 0.3 s | 0.010 / 0.0068 → 0.010 / 0.009 | 0.0069 / 0.0052 → 0.007 / 0.007 | 0.014 / 0.014 → 0.015 / 0.015 |
| **REF SCORE**, 1.0 / 0.3 s | 0.870 / 0.824 → **0.909 / 0.851** | 0.873 / 0.888 → **0.908 / 0.906** | 0.850 / 0.777 → **0.897 / 0.825** |

Task A at 0.3 s per request varies by up to ±0.03 s between single measurements; measured on the same CPUs under the
same conditions, session 10's image needs 0.223 s and session 11's 0.129 s (dev). Local time at 0.1 s per request
(dev): task A 0.316 s, task B 0.130 s per case. Memory (final image): task A answers every case at 1.5 GiB with 2 or 1
CPUs (session 10's code needed 3 GiB with 2 CPUs); task B now needs 1.5 GiB (selector T loads e5); 1 GiB fails for
both. New replay reference: `2026-10-13_rashad_prompt-snapshot-final-s11_devAB-valA`.

**Defaults changed, each by its rule:** parser fixes and per-part validity (step 1, G1/G2); AP-part after the rules
(step 3, HYBRID RULE); light-first lanes, lazy page reading, onnxruntime threads shared between lanes (step 4,
SAME-ANSWER RULE); one lane under a 2.5 GiB memory limit (step 5, SAME-ANSWER RULE); task B selector T (step 6, TASK B
RULE). **The probe before and after:** task A 0.960 / 0.908 → 0.971 / 0.954 (routed 83 → 90 of 94), task B 0.971 →
0.977.

**Apertus as parser** (details in step 3 below):

| Role | Accuracy | Macro-F1 / evidence effect | Tokens per case | In the final system? |
|---|---|---|---|---|
| AP-part (name the claim's part) | 79–85 % of reworded openings | unknown openings: +0.073 / +0.051 Macro-F1 over VW (dev / val) | +236 + 49 when asked | yes, only when the rules find no part (no dataset claim needs it) |
| AP-structure (read the contents) | 78.7 % of passing votes all pages equal | parser off: 0.970 / 0.955 vs VW 0.886 / 0.687 | ≈ +268 + 29 | no (needs 95 %) |
| AP-all (both, every case) | part 89 %, vote 93 % | dev 0.960 / 0.891 vs 0.977 / 0.980 | +502 + 77 | no; local time 0.822 vs 0.101 s at 0.3 s |
| Page image | heading not read | — | 1,077 + 26 | no |

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
| AP-claim (AP-part), reworded openings, dev 150 (run 2) | 78.7 % of parts equal to the original opening's | 0.967 / 0.880 (VW 0.894 / 0.670) | 1,383 + 63.4 (236 + 49.0) | **yes, after the rules**: val 0.926 / 0.840 against VW 0.876 / 0.650 (+0.051) |
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

(`2026-10-13_rashad_memory-step5_devA300`; no model). The main process holds 48 MiB; each
lane peaks at about 1.19 GiB, almost all of it from loading e5 (1.16 GiB at its peak, 0.80 GiB once loaded;
onnxruntime's arena adds 0.34 GiB after long batches); task B peaks at 49 MiB. The image under `--memory` ×
`--cpus` (fake model, a limit passes if every response is written with the labels of the 4g run): **before**, task A
needs **3 GiB with 2 CPUs** (2 GiB: OOM, 24 responses missing) and 1.5 GiB with 1 CPU; task B runs in 1 GiB. Fixes
at 2 CPUs: the arena off fits 2 GiB with two lanes (peak 2,005 MiB, 43 MiB of margin) but costs 0.06 s per case at
every limit; token-bounded batches add nothing; **one lane under a 2.5 GiB limit** answers every case with the same
labels at 2 GiB and 1.5 GiB (peak 1.17 GiB; local time at 0.1 s per request 0.42 s against 0.29 s with two lanes).
**Adopted** (SAME-ANSWER RULE: identical answers, G1/G2 pass, peak memory under limits improves): one lane under
2.5 GiB; lowest working limit **1.5 GiB** with 2 or 1 CPUs; 1 GiB stays out of reach (e5's load peak). Not built:
one e5 copy shared by the lanes, dropping page texts (about 6 MB per booklet).

**Step 6, task B tokens.**

(`2026-10-13_rashad_taskb-selectors_{devB300,valB580}`). Cheaper selectors of B-cut4's 4 paragraphs
for references over 3,000 characters (`src/taskb_context.py`): Q (e5's own 8-bit export), T (e5 on each paragraph's
first 300 characters), L (character 4-grams and numbers, no model), H (L in the reference's language, else T).
Agreement with E's paragraphs (mean shared of E's 3.81): Q 3.36, T 3.06, H 2.78, L 2.03. Local time per case of the
image at 1.0 / 0.3 s (step 4 defaults): whole reference 0.0067 / 0.0066, E 0.011 / 0.661, Q 0.0099 / 0.440, T 0.0077 /
0.0089, H 0.0072 / 0.0082, L 0.0065 / 0.0066; so T and H (the best two within +0.005 s) went to the dev run with E:

| Task B, Macro-F1 / unreadable / input + output tokens | dev (300) | val (580) |
|---|---|---|
| today, whole reference | 0.967 / 2 / 1,994 + 8.3 | 0.954 / 3 / 1,957 + 9.0 |
| E (B-cut4) | 0.987 / 0 / 883 + 8.7 | — |
| **T** | **0.987 / 0 / 815 + 8.5** | **0.968 / 1 / 820 + 9.4** |
| H | 0.993 / 0 / 923 + 8.5 | — |

TASK B RULE (dev and val: Macro-F1 at most 0.005 lower, no more unreadable answers, input tokens ≥ 30 % lower, local
time ≤ +0.005 s at 1.0 and 0.3 s): E fails on local time; T and H pass on dev; T (the higher REF SCORE on dev)
passes on val: **T is task B's default** (`context_b = "cut4-t"`). Q for task A was not used: it changes 50 of 75 cut
selections, so G1 cannot hold.

**FINISH.**

The final defaults (`bb2d08f`) through the published image `sha-bb2d08fea0f1` (pulled from ghcr.io, `make run`, task A
and task B in separate containers, one request per second; `2026-10-13_rashad_final-s11_{dev600,val1160,probe188}`):
dev task A 0.980 / 0.985, task B 0.987; val 0.959 / 0.955, 0.968; probe 0.971 / 0.954, 0.977; 0 failed calls, 1
unreadable answer (val task B). Local time of the same image (`local_time_*.json`; 2 CPUs pinned, 4 GB, fake model
replaying the final answers): dev task A 0.018 / 0.155 / 0.316 s per case at 1.0 / 0.3 / 0.1 s (a repeat at 0.3 s:
0.108 s), task B 0.010 / 0.009 / 0.130 s; val and probe at 1.0 / 0.3 s in their folders. REF SCORE (`ref_score.json`):
dev 0.909 / 0.851, val 0.908 / 0.906, probe 0.897 / 0.825. Memory grid of the final image (`memory_final.txt`): task A
1.5 GiB with 2 or 1 CPUs, task B 1.5 GiB; 1 GiB fails. New replay reference
`2026-10-13_rashad_prompt-snapshot-final-s11_devAB-valA` (1,180 requests; the replay reproduces the final runs
exactly; also `scripts/local_time.py`'s default table). Checks: 273 tests pass (1 skipped), `build_docs.py --check`
passes, `technical_report.pdf` has 6 pages; publish-image and clean-machine green on the final defaults' commit.

**For Rashad.** After a merge into `main`: check that `publish-image` ran on `main` and that
`ghcr.io/rashad18236/hackapertus-voting-nli:latest` pulls without logging in; that is the tag to submit. Before the
deadline: team name, members and project name in `technical_report.md` and the README. If the organisers' container
may get less than 1.5 GiB of memory, task B's selector T would need a model-free fallback (selector L passes the
local-time bound; not run on val).

**Dropped for time:** nothing from the step list. Not built (each named in its step): shared reading of the first
booklet (step 4), one e5 copy shared by the lanes and dropping page texts (step 5); not measured: E's, Q's and T's local
time at 0.1 s (step 6).

**Not verified:** the organisers' hardware, memory limit and model server (local time depends on the server's speed;
the measured CPUs have AVX-512 VNNI); the other teams' best values (REF SCORE uses ours); whether the organisers'
proxy counts "in flight" as our fake model does; how AP-part does on claim openings written by others (tested on our
own rewordings only); the peak memory includes the page cache, so it can exceed a limit a run still passes; task B
with selector T now loads e5 and needs 1.5 GiB (1 GiB failed on the final image), while task A's 1.5 GiB was the
target; the publish workflow and the clean-machine workflow results for the last push are in the status file.
