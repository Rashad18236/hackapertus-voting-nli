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

⟨Phase C, D, E, FINISH, model calls and tokens, not verified⟩
