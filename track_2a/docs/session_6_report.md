# Session 6 report: evidence pieces, and sending the part of the vote the claim names

2026-10-08, from 23:11 UTC (the paired run ended on 2026-10-09), branch
`claude/eager-cannon-08bx1h` (from `main` after PR #9). Run by Rashad, with
Claude Code, autonomously on Rashad's instructions. Every number comes from an
actual run on the dev split, scored with the starter's `evaluate.py` (commit
`559b598`); the test split was never used. Runs: `docs/runs/2026-10-08_rashad_*`
(listed per part below); decisions:
`docs/decisions/2026-10-08-2311_rashad_session-6.md`.

Fixed decision (Rashad): task A evidence contains only what Apertus cited.

## 1. In short

- **Evidence pieces (Part 0).** Splitting each page Apertus cited into
  1,000-character pieces, one evidence item each, raises E4's evidence score
  from 0.373 to 0.542 with the same answers. It is the default now.
- **Routing (Parts 1 and 2).** A claim's opening names the part of the vote
  its gold passage comes from ("according to the summary", "the Federal
  Council holds", "the committee holds", "according to the text put to the
  vote", "if the vote is accepted"). A new parser finds these parts in all
  44 dev booklets, and the router reads the opening of all 300 dev claims.
  The part sent to Apertus holds the gold passage in all 200 routed cases
  that have one (the embedding search: 0.741), with fewer characters.
- **Paired run (Part 3).** On all 300 dev task A cases, `section-route`
  against today's default `embed-e5-small`, same model
  (`swiss-ai/apertus-v1.5-8b`), case by case:

| | `section-route` | `embed-e5-small` |
|---|---|---|
| **Macro-F1** | **0.953** | 0.834 |
| **Evidence** | **0.905** | 0.662 |
| Input tokens per case | **1,210** | 1,868 |
| Median / p95 time | 1.6 s / **3.9 s** | 1.9 s / 11.7 s |

- **Recommendation: make `section-route` the task A default** (not changed
  here, as asked). See section 6 for the reasons and the risks.

## 2. Part 0: evidence as pieces of the cited pages

**What changed.** A new evidence setting, `cited-pieces`
(`src/evidence.py`): for the pages Apertus cited, and no others, each page is
split into the pipeline's pieces of at most 1,000 characters (the same split
as the embedding chunks). Each piece is its own evidence item with its page.
Pieces are taken in turn across the cited pages (the first piece of each
page, then the second of each, and so on), at most five items.

**Why it helps.** The scorer compares an item with the gold passage by
"partial ratio": it matches when the shorter text lies almost entirely inside
the longer one. A whole page matches only if it holds the whole passage or
lies inside it; a page that also holds other text, or a passage that runs over
a page break, fails. A 1,000-character piece inside the passage matches.

**Result** (E4's saved `embed-e5-small` answers re-scored, no model calls;
`docs/runs/2026-10-08_rashad_evidence-cited-pieces-e4_devA300/`):

| Claim type | Gold cases | Whole cited pages (`cited`) | Pieces (`cited-pieces`) |
|---|---|---|---|
| summary ("according to the summary") | 55 | 5 (0.091) | 5 (0.091) |
| council ("the Federal Council holds") | 68 | 30 (0.441) | 48 (0.706) |
| committee ("the committee holds") | 27 | 12 (0.444) | 20 (0.741) |
| law ("according to the text put to the vote") | 25 | 13 (0.520) | 16 (0.640) |
| detail ("if the vote is accepted") | 26 | 15 (0.577) | 20 (0.769) |
| **all** | **201** | **75 (0.373)** | **109 (0.542)** |

- The starter's scorer confirms Rashad's re-score: **0.542 against 0.373**.
  No label changes, no case found with whole pages is lost.
- The gain comes entirely from session 5's class "cited, but the text did not
  match": 34 of its 40 cases now match.
- Summary claims gain nothing: their gold page is not cited at all.
- **`cited-pieces` is now the default** (commit `ade5227`, on its own).
- Session 5's proposed prompt A-v4 (cite more pages, prefer the detailed
  section over the summary) was **not run**. Its "prefer the detailed section"
  is wrong for summary claims: 34 of the 43 "sent but not cited" cases of
  session 5 are summary claims whose gold passage is the summary page (checked
  on session 5's per-case file). Notes pointing here were added to sections 4
  and 6 of `docs/session_5_report.md`.

## 3. Part 1: what was built

The idea (Rashad's analysis, checked here): every vote in a booklet has the
same parts, and a claim's opening names the part its gold passage comes
from. The dataset's gold passages are exactly these parts: a council claim's
gold passage is the Federal Council's arguments, a summary claim's is one
summary page, a detail claim's is the whole detailed section.

- **`src/booklet.py`, the parser.** It reads the table of contents ("In Kürze
  4 – 5 / Im Detail 8 / Argumente 14 / Abstimmungstext 18", and the French and
  Italian equivalents) into one entry per vote, and checks every start page
  against the heading printed on it. The arguments are split into the
  committee's, the parliamentary debate (where there is one) and the Federal
  Council's, from the list on each vote's detail page and from page headings
  (both must agree). The summary pages' recommendation boxes are split per
  voice: committee (its own website), Federal Council and Parliament
  (admin.ch), a parliamentary minority (parlament.ch), and Parliament's vote
  counts. Paragraphs keep the page text's lines verbatim; running headers,
  page numbers and fragments under 40 characters are removed. When the
  contents are not found, or a vote fails a check, the parser says so (None,
  or a vote without parts) and never guesses.
- **`src/claim_router.py`, the router.** Patterns on the claim's opening, in
  German, French and Italian, for the five parts: summary, council,
  committee, law (the text put to the vote) and detail ("if the vote is
  accepted"). None when no pattern matches.
- **Context variant `section-route`** (`src/contexts/section_route.py`). The
  routed part is sent as numbered paragraphs, each keeping its page; the
  committee's and the council's parts include their recommendation boxes. If
  the part has more than 8,000 characters, the 8 paragraphs most similar to
  the claim are kept (the e5 model of `embed-e5-small`). If the router, the
  parser or the vote match gives nothing, the case runs exactly as
  `embed-e5-small` (same selection, prompt and evidence).
- **Prompt `A-v4-section-route`** (`src/nli.py`): task B's decision rule
  (`v3-topic-first`) word for word, one line naming the part and its voice,
  and the answer by json_schema as `{"paragraphs": [at most 3 numbers],
  "label": 0|1|2}`. The evidence is the cited paragraphs, verbatim, with
  their pages.
- **Tests:** parser (miniature booklet), router (each part in three
  languages, no match), variant (routing, top 8, fallback, evidence) and the
  CLI path (routed and fallback case). 89 tests pass.

Rashad's prototype `booklet_sections_prototype.py` was not in the repository
or on any branch when this session ran, so its notes on known gaps could not
be read; the parser was written without it.

## 4. Part 2: measured offline

`docs/runs/2026-10-08_rashad_route-check_devA300/` (no model calls).

- **Booklets: all 44 dev booklets parse completely** (131 of 131 votes), every
  language and year from 2020 to 2026. Problems found and fixed on the way:
  stray spaces inside words in some Italian booklets (" a rgomenti"), an
  overview page shared by two initiatives (2021-06-13), summaries longer than
  the contents say (initiative with counter-proposal, 2026-03-08), a
  parliamentary debate inside the arguments (AHV 21, cash initiative), boxes
  that do not name their voice.
- **Claims: the router assigns a part to all 300 dev claims** (summary 67,
  council 102, committee 49, law 39, detail 43). On the 586 deduplicated rows
  outside dev and test, 580 were routed before four patterns were added for
  the six misses. 299 of the 300 cases are routed; one falls back (a committee
  claim on the OECD minimum tax, a vote with no committee).
- **What the routed part holds** (200 routed cases with a gold passage):

| | Cases | A sent paragraph lies inside the gold passage | Characters sent |
|---|---|---|---|
| summary | 55 | 1.000 | 2,246 |
| council | 68 | 1.000 | 3,141 |
| committee | 26 | 1.000 | 3,102 |
| law | 25 | 1.000 | 3,482 |
| detail | 26 | 1.000 | 5,452 |
| same-language / cross-language | 67 / 133 | 1.000 / 1.000 | 3,350 / 3,173 |
| **all routed** | **200** | **1.000** | **3,233** |
| `embed-e5-small` (session 4) | 201 | 0.741 | 5,386 |

- Share of sent paragraphs that lie inside the gold passage: 0.782 (council
  0.964, law 1.000, summary 0.458: the summary spread's second page holds the
  boxes, while the gold passage is usually the first page).
- Coverage of the gold text: on average 0.879 of the gold passage is in the
  sent text. Lowest for law (0.610): the four longest law texts (the Covid-19
  law, about 20,000 characters) are cut to the 8 most similar paragraphs,
  which are short legal clauses.
- **Gate passed:** 100 % of dev booklets parse (needed 90 %), and the routed
  part holds the gold passage in 200 of 200 routed evidence cases (needed
  0.90).

## 5. Part 3: the paired run (E5)

`docs/runs/2026-10-08_rashad_section-route-vs-embed_devA300/` (both arms,
`NOTES.md`, `paired_analysis.json`).

**Setup.** All 300 dev task A cases. For each case both settings ran one
after the other, the order alternating from case to case, so the endpoint's
drift affects both equally. Model `swiss-ai/apertus-v1.5-8b` on Public AI for
all 600 calls (it was up, so the thinking model was not needed); 0 failed
calls, 0 unparseable answers. 23:41 to 00:07 UTC.

- `section-route`: prompt `A-v4-section-route`, the routed part as numbered
  paragraphs, the answer `{"paragraphs": [...], "label": ...}` by
  json_schema, evidence = the cited paragraphs. 299 cases routed; 1 fell back
  to `embed-e5-small` (a committee claim on a vote without a committee).
- `embed-e5-small` (control, today's default): prompt `A-v3-excerpts`, the 8
  chunks most similar to the claim, evidence `cited-pieces`.

**Labels.**

| | `section-route` | `embed-e5-small` |
|---|---|---|
| Macro-F1 | **0.953** | 0.834 |
| F1 entailment | 0.965 | 0.832 |
| F1 neutral | 0.947 | 0.850 |
| F1 contradiction | 0.947 | 0.819 |

Confusion matrices (rows: gold; columns: predicted entailment, neutral,
contradiction):

| gold | `section-route` | `embed-e5-small` |
|---|---|---|
| entailment (102) | 97 / 4 / 1 | 77 / 8 / 17 |
| neutral (99) | 0 / 99 / 0 | 3 / 85 / 11 |
| contradiction (99) | 2 / 7 / 90 | 3 / 8 / 88 |

The embedding's most frequent error, a true statement called a
contradiction (17 times), almost disappears (1). `section-route` never calls
an unrelated claim entailed or contradicted. Its remaining errors are mostly
the other way: 11 of its 14 wrong answers call a supported or refuted claim
neutral.

**Evidence, tokens, time.**

| | `section-route` | `embed-e5-small` |
|---|---|---|
| Evidence score | **0.905** (182/201) | 0.662 (133/201) |
| Mean input tokens | **1,210** | 1,868 |
| Median time | 1.6 s | 1.9 s |
| p95 time | **3.9 s** | 11.7 s |

The embedding's long times come from embedding each whole booklet on its
first case. `section-route` embeds only the paragraphs of long parts.

**By claim type** (Macro-F1; evidence found / gold cases):

| Claim type | Cases | `section-route` | `embed-e5-small` | Evidence `section-route` | Evidence `embed-e5-small` |
|---|---|---|---|---|---|
| summary | 67 | 0.929 | 0.789 | 49/55 | 25/55 |
| council | 102 | **1.000** | 0.852 | 65/68 | 50/68 |
| committee | 49 | 0.960 | 0.863 | 24/27 | 20/27 |
| law | 39 | 0.944 | 0.668 | 24/25 | 17/25 |
| detail | 43 | 0.817 | 0.818 | 20/26 | 21/26 |

**By language:** same-language 0.930 against 0.910, cross-language 0.965
against 0.796. By booklet and claim language, `section-route` is better in 7
of the 9 pairs; German booklet with German claim is lower (0.824 against
0.852), Italian with Italian the same (0.970).

**Where one was right and the other wrong** (all 300 cases answered by both):
both right 241, **only `section-route` right 45**, only `embed-e5-small`
right 9, both wrong 5. The difference is far beyond chance (sign test on the
54 cases where they differ: p < 0.000001). By claim type, `section-route` is
alone right in 12 summary, 15 council, 5 committee, 10 law and 3 detail
cases; `embed-e5-small` in 4 summary, 1 committee, 1 law and 3 detail cases.

**What is left.** Detail is the one part where routing does not help (0.817,
the same as the embedding): a detailed section has 4 to 8 pages, and 8 of
the 26 detail evidence cases are cut to the 8 paragraphs most similar to the
claim. Of the 19 evidence misses, 11 are neutral answers (no evidence) and 8
cite a paragraph outside the gold passage, once the committee's disclaimer
line ("Der Text auf dieser Doppelseite stammt vom Initiativkomitee").

**A caution on comparing with earlier runs.** The control arm scores 0.834
here and 0.711 in E4: E4 ran on `apertus-v1.5-8b-thinking` with whole-page
evidence. Different model, time and evidence setting; as always, only the two
arms of one paired run compare.

## 6. Recommendation

> **Done in session 7** (commit `d69d820`), after a paired run on 300
> validation cases nobody had looked at: `section-route` 0.956 against
> `embed-e5-small` 0.865. See `docs/session_7_report.md`.

**Make `section-route` the task A default** (`Settings.context_a` in
`src/cli.py`, a commit of its own after the team agrees). Reasons:

- It wins the paired run on every measure the organisers score: Macro-F1
  0.953 against 0.834, evidence 0.905 against 0.662, 35 % fewer input tokens,
  a third of the p95 time.
- It sends Apertus the passage the claim is about, and its evidence is the
  paragraph Apertus cited, copied from the booklet with its page: traceable
  to the source, as the challenge asks.
- It needs no new dependency: the parser and router are plain Python, and
  the e5 model is already in the Docker image.
- When it cannot route, a case runs exactly as today's default.

Risks to weigh before switching:

- **It depends on the claims' openings.** The router's patterns come from
  the dev claims. On the 586 deduplicated dataset rows outside dev and test,
  580 were routed before four patterns were added; the private test set is
  presumably built the same way, but if its claims are phrased differently,
  more cases fall back to the embedding (still correct, not better).
- **It depends on the booklet layout of 2020 to 2026.** All 44 dev booklets
  parse; a booklet laid out differently makes the parser return no parts, and
  the case falls back.
- **Tuned and measured on the same 300 dev cases.** The router, the parser's
  checks and the vote-match threshold were written with the dev data in
  view; only the held-out set will show how well they carry over.

Follow-ups, one change per comparison: a larger character budget for detail
and law parts instead of the 8 most similar paragraphs; dropping the
committee's disclaimer line from the paragraphs; routing committee claims on
votes without a committee to the parliamentary minority (one dev case);
work on the remaining "called neutral" errors.

## 7. What stays unverified

- **Docker on a clean machine.** The image was rebuilt here (through the
  sandbox wrapper that adds this session's proxy certificate) and `make run`
  answered the two example requests in the official format (format check
  clean), once with the defaults (`embed-e5-small`, evidence
  `cited-pieces`) and once with `EXTRA_ARGS="--context-a section-route"`.
  The first task A case took 70 s with the default (the whole booklet is
  embedded first, inside the container) and 4.2 s with `section-route`. A
  plain `make build && make run` on a clean machine was not tried.
- **The evaluation model and server.** E5 ran on Public AI's
  `apertus-v1.5-8b` at night; which Apertus model and server the organisers
  use is unknown.
- **The official scorer.** Only the starter's `evaluate.py` was available.
  It does not check pages; the official one might. `section-route`'s
  evidence pages are the pages the paragraphs come from (a recommendation box
  carries its summary page).
- **The prototype parser's notes** (`booklet_sections_prototype.py`) could
  not be read; gaps it knows about may not be covered.
- **Booklets outside dev.** Only the 44 dev booklets were parsed; the test
  booklets were not opened.
- **The dataset README** was not checked again for label definitions.
