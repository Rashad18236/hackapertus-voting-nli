# Session 9: open items, offline analyses, task B long passages, task A label errors

2026-10-09 17:07 UTC to 2026-10-10 13:00 UTC, branch `rashad/until-1600` (draft pull request #16, never
merged, no tag), run unattended by Claude Code for Rashad. Decisions:
`docs/decisions/2026-10-09-1707_rashad_session-9.md`; status log: `docs/session_9_status.md`.

⟨FIRST PAGE: finished, experiments, defaults changed, stability, dropped⟩

## Phase A: open items

**A0. PR #14 merged into the branch** (`bd9d030`). Only the generated `docs/decisions.md` conflicted; it was
rebuilt by `scripts/build_docs.py`. The gates equal `gates/merge.json` (0 request or path differences,
0 label differences, evidence different only in session 8's 19 repeated-text cases); 161 tests passed
(`gates/s9_A0.json`).

**A1. `src/llm.py` fallbacks** (`7edbae4`):

- (a) HTTP 400 or 422 to a request with `response_format`: the request is sent once more without it, and
  `response_format` is left out for the rest of the run.
- (b) HTTP 404, or HTTP 400 after (a): `BASE_URL/models` is read once and the id naming Apertus v1.5 8B is
  taken (case ignored; "apertus", "v1.5" and "8b" as a size; the shortest if several, so `…-8b` wins over
  `…-8b-thinking`), for the rest of the run.
- (c) At most three extra requests per run; the tokens of every request and the time of all of them count in
  the call's metrics.
- (d) Tests against the fake model over HTTP (`tests/test_llm_fallbacks.py`): each fallback alone, 400 and
  422, both together (using all three extra requests), the limit, no fallback on a normal endpoint, tokens
  and time. G1 and G2 equal `gates/merge.json`; 169 tests passed (`gates/s9_A1.json`).
- Also new, off unless set: `LLM_MIN_INTERVAL` (seconds between two requests), so runs through `make run`
  keep this session's rule of at most one request per second.

**A2. Evidence halves** (`453e5b4`, **default changed**). After the cited paragraphs, the two halves of each
cited paragraph (cut after the `.`, `!` or `?` nearest the middle) are added in turn until there are five
items; a text already present is skipped. Measured by replaying E5's (dev) and E6's (val sample) saved answers
through the code with the halves on:

| | G1 requests | Labels | Evidence score (starter) |
|---|---|---|---|
| dev, 300 task A cases (E5's answers) | unchanged | unchanged | 0.9055 → **0.9254** (182 → 186 of 201) |
| val sample, 300 cases (E6's answers) | unchanged | unchanged | 0.9461 → **0.9559** (193 → 195 of 204) |

Rashad's rule (G1 and every label unchanged, the evidence score not lower on dev and val) holds, so the halves
are on by default (`evidence_halves_a=True`; `--no-evidence-halves-a` switches them off).

**A3. Documentation** (`1f51b56`).

- Dataset README (checked 17:20 UTC, repository commit `fc2b276`): it now has a field table, but no label
  definitions beyond names: `entailment_label` — "The entailment class of the `claim` relative to the
  `reference_string` and voting booklet as a whole. May be `Entailment` (`0`), `Unrelated / Neutral` (`1`)
  or `Contradiction` (`2`)." No prompt was changed.
- The booklets' terms: admin.ch's "Terms and conditions" say "Copyright, Swiss federal authorities …
  Downloading or copying of texts, illustrations, photos or any other data does not entail any transfer of
  rights on the content … Any reproduction requires the prior written consent of the copyright holder." The
  repository commits one booklet (`examples/booklets/2020_09_27_fr.pdf`); the dev booklets are downloaded by
  script. Swiss copyright law exempts official reports of authorities (Art. 5 URG); whether that covers the
  booklet is left for the team (not legal advice).
- `README.md`: requirements, running with one's own cases and booklets (`make run CASES=… BOOKLETS=…
  OUTPUT_DIR=…`), and the statement that answers are not political advice and are traceable to the booklet.

**A4. Stability point 1** (`2026-10-09_rashad_stability-1_dev600`): ⟨stability section⟩

## Phase B: offline analyses (no model calls)

Full write-up: `docs/analysis_offline.md`; run folder `2026-10-09_rashad_analysis-offline_devA-valA-devB`.

- **B1.** Task A Macro-F1, dev and val pooled (600 cases): 0.955, 95 % bootstrap interval 0.938–0.970;
  task B dev 0.967 (0.945–0.986). No language pair stands out.
- **B2.** Of the dev cases whose evidence matches the gold passage (182), the item's page is the page of its
  quote in all 182, a page of the gold passage in 179, its first page in 107 (val: 193 / 189 / 114 of 193).
- **B3.** Accuracy with and without numbers, dates, negation and qualifying words differs by a few cases
  only; numbers are not where task A errs (0.965 with, 0.950 without).
- **B4.** Always neutral: Macro-F1 0.165. Task B: references over 8,000 characters are neutral in 99 of 105
  dev cases, shorter ones in 0 of 195 (a dataset artefact; never used).
- **B5.** All 12 routed val errors of E6 had the gold passage among the paragraphs sent (10 cited a paragraph
  inside it): reading errors. The 13th fell back to embed-e5-small. 9 of 13 are "called neutral".
- **B6.** E5's 110 neutral answers: wrong ones have higher claim-paragraph similarity (0.836–0.914) than right
  ones (0.768–0.862). No clean separation; threshold **0.845** flags 10 of 11 wrong and 11 of 99 right
  neutral answers (largest difference of the two shares), estimated +3.5 % input tokens: L2 is run with it.

## Phase C: task B long passages

**Versions** (`src/taskb_context.py`, `--context-b`; the code went in off by default):

- **B-cut:** a reference over 8,000 characters becomes its first line (the ballot's title) plus the 8
  paragraphs most similar to the claim (e5, the paragraph splitting of section-route), in their order; prompt
  unchanged. Shorter references are sent unchanged.
- **B-para:** the same text as numbered paragraphs with task A's prompt (`A-v4-section-route`) and paragraph
  answer schema; evidence stays `[]`.

**Offline first** (`scripts/taskb_context_tokens.py`, 300 dev task B cases, Apertus v1 tokenizer plus the
endpoint's 19 tokens): full 1,994 input tokens per case (equal to the measured mean), B-cut 1,231 (−38 %),
B-para 1,375 (−31 %).

**Dev, one interleaved run** (`2026-10-09_rashad_taskb-context_devB300`, 17:53–18:20 UTC, three arms
rotating, all 900 answers from one backend, so "all cases" and "same backend" are the same 300):

| | current | B-cut | B-para |
|---|---|---|---|
| Macro-F1 | 0.967 | 0.967 | 0.963 |
| Mean input tokens | 1,994 | 1,231 (−38.3 %) | 1,375 (−31.0 %) |
| Mean / p95 time | 1.25 / 2.22 s | 1.86 / 6.33 s | 2.12 / 5.44 s |

B-cut's labels equal current's on all 195 short references (same requests) and on the long ones it is 97 of
105 right, like current; B-para gets the long ones right more often (104) but calls 8 short-reference
contradictions neutral. Times include two CPU-heavy gate runs that overlapped the first 20 minutes.

**Val, one interleaved run** (`2026-10-09_rashad_taskb-cut-confirm_valB580`, the task B cases of all 580 val
rows, 18:26–18:59 UTC, one backend): current 0.957, **B-cut 0.961**; input tokens 1,957 → **1,230
(−37.1 %)**; time 1.48 → 1.80 s per case (the e5 embedding of long references). The run was stopped by a
background-job time limit after 516 cases and finished with `--resume`.

**Rule:** B-cut at most 0.01 below current (all and same-backend cases) and at least 25 % fewer input tokens,
on dev and on val; B-para only if 0.02 above B-cut. **B-cut passes on both; B-para does not replace it. The
task B default is now `cut`** (`13da75a`). Gate: G1 differs in exactly the 105 dev task B requests over 8,000
characters; labels and evidence unchanged; 188 tests.

## Phase D: task A label errors

**Versions** (off by default): **L1** (`--label-rule-a`): the routed prompt plus "A claim that gives a
different number, share, date, actor or direction than the reference text gives for the same thing is a
contradiction." (`A-v4-section-route-L1`). **L2** (`--second-look-a`): after a neutral answer whose highest
claim-paragraph similarity is at least 0.845 (B6), one more call with the three most similar paragraphs and a
prompt that asks for 0, then 2, then 1 (`A-v4-second-look`); a 0 or 2 replaces the neutral; tokens of both
calls summed.

**Dev, one interleaved run** (`2026-10-09_rashad_label-errors_devA300`, 18:56–19:27 UTC, three arms
rotating, one backend):

| | current | L1 | L2 |
|---|---|---|---|
| Macro-F1 | 0.966 | **0.980** (+0.0137) | 0.976 (+0.0102) |
| Neutral recall | 1.000 | 1.000 | 1.000 |
| Gold contradictions answered neutral | 7 | 2 | 4 |
| Evidence (starter) | 0.955 | 0.980 | 0.970 |
| Mean input tokens | 1,210 | 1,238 (+2.3 %) | 1,244 (+2.8 %) |
| Model calls | 300 | 300 | 317 |

L1: 5 wrong → right, 1 right → wrong. L2: 17 second calls (11 on gold neutrals, all stayed neutral; 3 of 6
wrong neutrals fixed), 3 wrong → right, none right → wrong.

**Val, one interleaved run** (`2026-10-09_rashad_label-errors-confirm_valA580`, all 580 val task A cases,
19:28–20:16 UTC, three arms rotating, one backend; L2 for information only):

| | current | L1 | L2 |
|---|---|---|---|
| Macro-F1 | 0.950 | **0.961** (+0.0104) | 0.954 (+0.0034) |
| Neutral recall | 1.000 | 1.000 | 1.000 |
| Gold contradictions answered neutral | 21 | 14 | 19 |
| Evidence (starter) | 0.943 | 0.958 | 0.948 |
| Mean input tokens | 1,178 | 1,206 (+2.4 %) | 1,217 (+3.3 %) |
| Model calls | 580 | 580 | 619 |

L1: 7 wrong → right, 1 right → wrong. L2: 39 second calls, 2 labels changed (both right).

**Rules:** L1 needs +0.01 on dev, +0.005 on val and neutral recall ≥ 0.98 on both: **passes (dev +0.0137,
val +0.0104, recall 1.000 and 1.000); the task A default is now `label_rule_a=True`**. L2 needs +0.015 on both
and at most +5 % input tokens: **fails on dev** (+0.0102); on val +0.0034 for +3.3 % tokens. It stays off; as
an option it buys a few corrected neutral answers for about 3 % more input tokens and 6–7 % more calls.

## Phase E: information only (no default changed)

**E1, context curve** (`2026-10-09_rashad_context-curve_devA100`, 100 balanced dev task A cases, seed 42, one
interleaved run of six arms in a balanced Latin square, 20:17–20:50 UTC, one backend; routed arms with L1):

| What Apertus reads | Macro-F1 | Evidence | Input tokens | Mean / p95 time |
|---|---|---|---|---|
| whole booklet | 0.858 | 0.422 | 37,586 | 7.3 / 17.6 s |
| embed-e5-small (8 chunks) | 0.898 | 0.656 | 1,885 | 4.9 / 15.3 s |
| section-route | **0.989** | **1.000** | 1,248 | 1.9 / 3.0 s |
| section-route, 4 most similar paragraphs | 0.979 | 0.984 | 804 | 2.0 / 3.2 s |
| section-route, 2 | 0.940 | 0.922 | 614 | 1.8 / 2.6 s |
| section-route, 1 | 0.769 | 0.641 | 510 | 1.9 / 2.9 s |

More text is not better; the right part matters more than similarity; 4 paragraphs keep most of the result at
64 % of the tokens (a possible later trade, not tested on val).

**E2, closed book** (`2026-10-09_rashad_closed-book_devA300`, 300 dev task A, two arms, 20:50–21:09 UTC):
claim and vote name only 0.435 (neutral in 236 of 300 answers), section-route 0.980 in the same run. The
booklet supplies almost all of the result.

**E3, Apertus as router** (`2026-10-09_rashad_llm-router_dev300-stress300`, 600 calls, 21:09–21:22 UTC):
agreement with the rules on 278 of 300 dev claims (16 of the 22 disagreements: law claims naming the Federal
Assembly's recommendation, which Apertus calls council). On the 300 stress openings: right 283 (rules 285),
wrong part 17 (rules 0), fallback 0 (rules 15). About 220 input and 8 output tokens and 1.3 s per call. The
rules stay the router.

⟨FINISH, model calls and tokens, not verified⟩
