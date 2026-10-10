# Offline analyses (session 9, phase B)

No model calls: every number below comes from answers already recorded. Script:
`scripts/analysis_offline.py` (run from `track_2a/` with `EMBED_MODEL_DIR=models/multilingual-e5-small`);
its output is in `docs/runs/2026-10-09_rashad_analysis-offline_devA-valA-devB/`.

Answers used (each the default settings of its time):

| Set | Task | Cases | Answers |
|---|---|---|---|
| dev (E5) | A | all 300 dev task A cases | `2026-10-08_rashad_section-route-vs-embed_devA300/section-route` |
| val (E6) | A | the balanced 300-case val sample | `2026-10-09_rashad_section-route-vs-embed_valA300/section-route` |
| dev (stability 1) | B | all 300 dev task B cases | `2026-10-09_rashad_stability-1_dev600/task-B` |

Val task B answers did not exist when this was written; phase C's val run adds them to the report
(`docs/session_9_report.md`).

## B1. Error margin and languages

95 % bootstrap interval of the Macro-F1: 2,000 resamples of the cases with replacement, seed 42; the interval is
the 2.5th and 97.5th percentile.

| Task | Set | Cases | Macro-F1 | 95 % interval |
|---|---|---|---|---|
| A | dev (E5) | 300 | 0.953 | 0.927 – 0.975 |
| A | val (E6) | 300 | 0.956 | 0.930 – 0.979 |
| A | **dev and val pooled** | 600 | **0.955** | **0.938 – 0.970** |
| B | dev (stability 1) | 300 | 0.967 | 0.945 – 0.986 |

What it means: with 300 cases, a difference of 0.02 to 0.03 between two separate runs is within the noise of
the case sample alone (before any drift of the endpoint). This is why every comparison in this project is
paired or interleaved on the same cases, and why phase C and D's adoption rules require the gain on dev and
on val.

Accuracy by claim language (rows) and source language (columns), task A, dev and val pooled
(about 67 cases per cell):

| Claim \ booklet | de | fr | it |
|---|---|---|---|
| de | 0.897 (61/68) | 0.941 (64/68) | 0.969 (63/65) |
| fr | 0.940 (63/67) | 0.970 (65/67) | 0.970 (65/67) |
| it | 0.955 (63/66) | 0.970 (64/66) | 0.985 (65/66) |

Task B, dev (about 33 cases per cell):

| Claim \ reference | de | fr | it |
|---|---|---|---|
| de | 1.000 (34/34) | 0.941 (32/34) | 0.941 (32/34) |
| fr | 0.939 (31/33) | 1.000 (33/33) | 0.970 (32/33) |
| it | 0.939 (31/33) | 0.970 (32/33) | 1.000 (33/33) |

No language pair is far below the others. The lowest task A cell (German claim, German booklet, 0.897) is
7 errors in 68 cases; with cells this small, one or two errors move a cell by 0.015 to 0.03, so the table shows
no pattern we would act on. Task B is right on all 100 same-language dev cases; all 10 of its errors are
cross-language (10 of 200).

## B2. Evidence pages under three rules

The starter's scorer checks the quoted text only ("pages are not checked yet"). Of the gold
entailment/contradiction cases whose evidence matches the gold passage under the starter's text rule, how many
also have a page that would pass a page rule? Gold pages are found as in session 5 (200-character windows of
the gold passage located in the booklet, `scripts/evidence_loss.py`); "the passage's first page" is the
lowest of them.

| Set | Gold cases | Text matches | (1) any page of the gold passage | (2) its first page | (3) the page holding the quoted text |
|---|---|---|---|---|---|
| dev (E5) | 201 | 182 | 179 | 107 | 182 |
| val (E6) | 204 | 193 | 189 | 114 | 193 |

- Rule 3 holds for every matching item: the page we give is always the page the quote comes from (each
  paragraph keeps its own PDF page; session 6).
- Rule 1 fails for 3 (dev) and 4 (val) cases: the matching item lies on a page outside the gold passage's
  pages, typically a summary box or a title repeated elsewhere whose text also lies inside the gold passage.
- Rule 2 would cost a lot (182 → 107): gold passages often span two or three pages and the cited paragraph is
  on a later one. If the official run checks pages, rule 1 or 3 is what our evidence is built for; rule 2 would
  need every passage's first page as an extra item. This stays an open question for the organisers.

## B3. Claim features and accuracy

Claims tagged with word lists in German, French and Italian (`TAGS` in the script): a digit (number); a year
or month name (date); a negation word (nicht, kein, ne/pas, aucun, non, nessun, senza, ...); a qualifying word
(nur, alle, mindestens, seulement, tous, au moins, solo, tutti, almeno, ...). Accuracy with and without each
tag:

| Tag | Task A (600, dev+val) with / without | Task B (300, dev) with / without |
|---|---|---|
| number | 0.965 (200) / 0.950 (400) | 0.939 (99) / 0.980 (201) |
| date | 0.988 (83) / 0.950 (517) | 0.953 (43) / 0.969 (257) |
| negation | 0.935 (77) / 0.958 (523) | 1.000 (40) / 0.962 (260) |
| qualifier | 0.974 (78) / 0.952 (522) | 0.917 (36) / 0.973 (264) |

The differences are a few cases each (task B's "number" gap is 6 errors in 99 against 4 in 201). Numbers are
not the main source of task A errors (0.965 with a number against 0.950 without), which is a first hint that
L1 (a sentence on different numbers, dates and actors) has little to fix; task A's negated claims are slightly
worse (5 of 77 wrong).

## B4. Rules without a model (never used in the pipeline)

| Rule | Task A dev | Task A val | Task B dev |
|---|---|---|---|
| always neutral | 0.165 | 0.162 | 0.165 |
| task B: reference over 8,000 characters → neutral, else entailment | – | – | 0.541 |
| task B: over 8,000 characters → neutral, else the model's answer | – | – | 0.973 (model alone 0.967) |

The length rule exposes a property of the dataset: of the 105 dev task B references over 8,000 characters,
**99 are neutral**; of the 195 shorter ones, **none** is. Neutral rows pair the claim with an unrelated passage,
and those passages are whole sections; gold passages of entailment and contradiction rows are shorter. A
pipeline could exploit this, but the rule says nothing about the claim and would fail on any other data, so it
is reported only and never used. It matters for phase C: the passages B-cut and B-para shorten are almost all
neutral cases, so their test is mainly whether the model still sees that the passage does not deal with the
claim.

## B5. The 13 val errors of E6: was the gold passage sent?

| Case | Gold → answer | Route | Paragraphs sent | Gold passage among them |
|---|---|---|---|---|
| row-186 | E → C | detail | 8 | yes (4 of 8; cited one) |
| row-341 | E → N | detail | 8 | yes (6 of 8) |
| row-1025 | C → N | law | 8 | yes (8 of 8) |
| row-1036 | C → N | none: fell back to embed-e5-small | – | – |
| row-1053 | C → N | council | 9 | yes (9 of 9; cited one) |
| row-1151 | C → N | summary | 4 | yes (2 of 4; cited one) |
| row-1215 | C → N | committee | 9 | yes (8 of 9; cited one) |
| row-1226 | C → N | summary | 5 | yes (2 of 5; cited one) |
| row-1259 | C → E | committee | 5 | yes (4 of 5; cited one) |
| row-1312 | C → E | summary | 4 | yes (2 of 4; cited one) |
| row-1325 | C → N | council | 8 | yes (8 of 8; cited one) |
| row-1360 | C → N | detail | 14 | yes (12 of 14; cited one) |
| row-1457 | C → E | summary | 5 | yes (3 of 5; cited one) |

(E entailment, N neutral, C contradiction; "cited one": the answer cited a paragraph inside the gold passage.)

All 12 routed errors had the gold passage in front of the model, and in 10 of them the model even cited a
paragraph inside it: **these are reading errors, not search errors.** 9 of 13 are "called neutral"
(8 contradictions and 1 entailment answered neutral), 4 are entailment and contradiction swapped. Several of
the claims turn on one detail (a share, "most farms", "new taxes", "until 2030"). The one fallback case (row-1036) had no route, so its passage came from embed-e5-small.

## B6. Similarity of neutral answers: a threshold for L2?

For each of E5's 110 neutral answers (dev, all routed): the cosine similarity (multilingual-e5-small, the
model section-route already uses) between the claim and the most similar paragraph sent.

| | Answers | Lowest | Median | Highest |
|---|---|---|---|---|
| right (gold neutral) | 99 | 0.768 | 0.822 | 0.862 |
| wrong (gold entailment or contradiction) | 11 | 0.836 | 0.875 | 0.914 |

No threshold separates them completely (the ranges overlap between 0.836 and 0.862), but the wrong neutral
answers sit clearly higher. At or above a threshold t:

| t | Wrong neutral flagged (of 11) | Right neutral flagged (of 99) | Second calls per 300 cases |
|---|---|---|---|
| 0.8358 | 11 | 24 | 35 |
| **0.845** | **10** | **11** | **21** |
| 0.8467 | 9 | 9 | 18 |
| 0.8703 | 7 | 0 | 7 |

**Threshold for L2: 0.845**, the threshold with the largest difference between the share of wrong and the
share of right neutral answers flagged (0.909 − 0.111 = 0.798; 0.758 at 0.8358, 0.727 at 0.8467, 0.636 at
0.8703). Estimated cost on dev: 21 second calls of
about 612 input tokens each (Apertus v1 tokenizer plus the endpoint's 19), +43 input tokens per case on
average, +3.5 % against E5's 1,210, inside L2's 5 % limit. The threshold is chosen on E5's dev answers, so
the dev run of phase D is not an independent test of it; the val confirmation is.
