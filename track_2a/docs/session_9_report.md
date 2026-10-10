# Session 9: open items, offline analyses, task B long passages, task A label errors

2026-10-09 17:07 UTC to 2026-10-10 13:00 UTC, branch `rashad/until-1600` (draft pull request #16, never
merged, no tag), run unattended by Claude Code for Rashad. Decisions:
`docs/decisions/2026-10-09-1707_rashad_session-9.md`; status log: `docs/session_9_status.md`.

## In short

**Finished:** every phase, A to E, and FINISH. Nothing was dropped for time. Phases C and D each changed a
default under their fixed rules, and phase A changed one; phases B and E changed nothing. The test split, the
splits and the scorer were not touched; no key was printed, logged or committed.

**Defaults changed, each by its rule:**

| Default | Rule | Dev | Val | Commit |
|---|---|---|---|---|
| Task A evidence: halves of the cited paragraphs up to five items (A2) | G1 and every label unchanged, evidence not lower on dev and val | evidence 0.906 → 0.925 (replay of E5) | 0.946 → 0.956 (replay of E6) | `453e5b4` |
| Task B: references over 8,000 characters cut to the first line plus the 8 most similar paragraphs (B-cut) | ≤ 0.01 below current (all and same-backend cases), ≥ 25 % fewer input tokens, on dev and val | 0.967 = 0.967, −38 % tokens | 0.961 vs 0.957, −37 % | `13da75a` |
| Task A prompt: one sentence on what makes a contradiction (L1) | +0.01 on dev, +0.005 on val, neutral recall ≥ 0.98 on both | 0.980 vs 0.966, recall 1.000 | 0.961 vs 0.950, recall 1.000 | `50cb320` |

**Final defaults, all 600 dev cases through the Docker image:** task A **0.980** (evidence **0.980**, 1,238
input tokens), task B **0.967** (1,231 input tokens, was 1,994). On all 580 val rows: task A 0.961 (evidence
0.958), task B 0.961.

**What each experiment showed:**

- **A1** `llm.py` now survives an endpoint that refuses `response_format` or the model name (tests against the
  fake model; at most three extra requests).
- **B (offline):** task A's 95 % interval on dev and val is 0.938–0.970; all of E6's routed val errors had the
  gold passage in front of the model (reading errors); task B references over 8,000 characters are 99 of 105
  times neutral (a dataset artefact, never used); a similarity threshold (0.845) flags 10 of 11 wrong neutral
  answers.
- **C:** cutting long task B references keeps Macro-F1 and saves 37–38 % of input tokens; numbering them with
  task A's prompt (B-para) was 0.004 worse.
- **D:** one sentence (L1) fixed most "called neutral" contradictions (7 → 2 on dev, 21 → 14 on val) without
  losing a neutral case; a second look (L2) fixed fewer (+0.010 dev, +0.003 val) and stays off.
- **E1:** whole booklet 0.858 (37.6k tokens) < 8 similar chunks 0.898 < the routed part **0.989** (1.2k);
  4 paragraphs keep 0.979, 1 paragraph drops to 0.769. **E2:** without the booklet Apertus scores 0.435.
  **E3:** Apertus as router agrees with the rules on 278 of 300 dev claims but routes 17 stress openings to a
  wrong part (rules 0).

**Stability points** (the image built at `7edbae4`, 17:26 UTC, before session 9's default changes; the same settings each time; all 600 dev cases):

| Point (start, UTC) | Task A Macro-F1 | Evidence | Task B Macro-F1 | Unreadable (B) | Labels equal to point 1 (A; B) | Backend |
|---|---|---|---|---|---|---|
| 1 (2026-10-09 17:28) | 0.966 | 0.930 | 0.967 | 3 | – | blablador, all 600 |
| 2 (2026-10-10 01:56) | 0.966 | 0.935 | 0.967 | 4 | 299/300; 300/300 | blablador, all 600 |
| 3 (2026-10-10 09:56) | 0.966 | 0.930 | 0.963 | 1 | 300/300; 299/300 | blablador, all 600 |

**Dropped for time:** nothing. **Not done:** the 4-paragraph cut on val, an Apertus fallback router, L2 as a
default (all reported as options).


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

**A4. Stability points.** All 600 dev cases with default settings through the Docker image, `make run` and
the real endpoint, at three times with exactly the same image and settings (`hackapertus-voting-nli:stability`,
built at `7edbae4` at 17:26 UTC, before A2 and the later default changes; `LLM_MIN_INTERVAL=1`). Scores per
task and per backend by `scripts/stability_report.py` (task B's numbers in each point's `task-B/run.json`):

| Point (start, UTC) | Task A Macro-F1 | Evidence | Task B Macro-F1 | Unreadable (B) | Labels equal to point 1 (A; B) | Backend |
|---|---|---|---|---|---|---|
| 1 (2026-10-09 17:28) | 0.966 | 0.930 | 0.967 | 3 | – | blablador, all 600 |
| 2 (2026-10-10 01:56) | 0.966 | 0.935 | 0.967 | 4 | 299/300; 300/300 | blablador, all 600 |
| 3 (2026-10-10 09:56) | 0.966 | 0.930 | 0.963 | 1 | 300/300; 299/300 | blablador, all 600 |

- Point 1 (`2026-10-09_rashad_stability-1_dev600`, 17:28–17:48 UTC), point 2
  (`2026-10-10_rashad_stability-2_dev600`, 01:56–02:18 UTC), point 3 (`2026-10-10_rashad_stability-3_dev600`,
  09:56–10:16 UTC).
- Over 16.5 hours two of the 600 cases ever changed label: row 1138 (task A, a gold contradiction: neutral,
  entailment, neutral) and row 640 (task B, a gold neutral: neutral, neutral, contradiction); the endpoint, on
  this one backend, answered the same requests almost identically.
- The sandbox restarted before points 2 and 3; the Docker daemon was started again each time and the image was
  unchanged. Points 2 and 3 had no gateway cache hits (their requests were last sent eight hours before), so
  their answers are fresh.

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

## FINISH

- **Final defaults on all 600 dev cases through the Docker image** (`2026-10-09_rashad_final-defaults_dev600`,
  image `hackapertus-voting-nli:final` built at `50cb320`, 21:22–21:44 UTC, one backend):

  | Task | Macro-F1 | Evidence | Mean input / output tokens | Mean / p95 time |
  |---|---|---|---|---|
  | A (300) | **0.980** | **0.980** | 1,238 / 14.5 | 2.2 / 4.5 s |
  | B (300) | **0.967** | – | 1,231 / 8.4 | 2.0 / 3.8 s |

- **New replay reference** `2026-10-09_rashad_prompt-snapshot-final_devAB-valA`: the final code's 1,180
  requests (600 dev, 580 val), each answered from a saved real answer (the final dev run; the val L1 arm). The
  replay reproduces them exactly (0 label, 0 evidence differences): dev A 0.980 / 0.980, B 0.967, val A
  0.961 / 0.958. It replaces the session 8 reference for G1/G2.
- Tests: 189 pass, 1 skipped (`pytest`, after every code change). Clean-machine workflow (`image` and `tests` jobs on GitHub): green on every pushed commit checked, last on `8447cf3` (stability point 3 and the final reports); this record's own commit is checked the same way.
- `technical_report.md` rewritten to six A4 pages at 10 pt (`technical_report.pdf`, built by
  `scripts/build_report_pdf.sh`: pandoc and headless Chromium); template sections kept; token usage and
  inference time in section 5. Remaining TODOs: team name and members only.
- `CLAUDE.md` has a session 9 section; `docs/session_9_status.md` logs every phase.

## Model calls and tokens

Every call went to Public AI's `swiss-ai/apertus-v1.5-8b` (the model named in `.env`), at most one request
per second, one run at a time. No call failed and none was retried (0 HTTP 429, 0 5xx). Tokens are the
endpoint's `usage` as recorded per case (gateway cache hits included: the endpoint reports their tokens too).

| Run | Model calls | HTTP requests | Input tokens | Output tokens |
|---|---|---|---|---|
| A4 stability point 1 | 600 | 600 | 961,224 | 6,959 |
| C dev (3 arms) | 900 | 900 | 1,380,182 | 9,272 |
| C val (2 arms) | 1,160 | 1,160 | 1,848,717 | 10,358 |
| D dev (3 arms) | 917 | 917 | 1,107,589 | 13,282 |
| D val (3 arms) | 1,779 | 1,779 | 2,088,309 | 25,776 |
| E1 context curve (6 arms) | 600 | 600 | 4,264,620 | 9,387 |
| E2 closed book (2 arms) | 600 | 600 | 438,123 | 7,690 |
| FINISH final defaults | 600 | 600 | 740,677 | 6,871 |
| stability point 2 | 600 | 600 | 961,224 | 6,934 |
| stability point 3 | 600 | 600 | 961,224 | 6,887 |
| E3 Apertus as router | 600 | 600 | 126,204 | 4,580 |
| **Total** | **8,956** | **8,956** | **14,878,093** | **107,996** |

The gates, the replay reference and every test used the fake model (`scripts/stub_llm.py`), not the endpoint.

## What was not verified

- **Other backends and servers.** Every one of session 9's answers came from one Public AI backend
  (blablador, fingerprint `...dd237840`); the featherless backend that served 39 % of the answers of a run at 02:11 UTC
  answered none. All adoption rules were therefore checked on one backend only ("same backend" equals "all
  cases" everywhere); how B-cut and L1 behave on another backend or on the evaluation's server is unknown.
- **Time.** Times include gateway cache hits (identical requests within about 10 minutes; up to two thirds of
  an arm in phase D) and, in the phase C dev run, two CPU-heavy gate runs on the same machine. Time was not
  part of any rule; B-cut's extra CPU time (about 0.3 s per case for embedding long references) was measured
  only on this machine.
- **The L2 threshold** was chosen on E5's dev answers (B6) and tested on the same dev cases; only its val run
  is independent (+0.003).
- **E1 used 100 cases**; its differences of 0.01 are one case. Cutting to 4 paragraphs was not run on val.
- **Unseen booklets** were checked offline only (session 8); the test split and the private set were not run.
- **The booklets' reuse terms** were read, not resolved: one booklet is committed as an example.
- **Pages** in evidence are the PDF pages of the quoted text; whether the official scorer checks pages, and
  with which rule, is unknown (B2 shows what three rules would give).
