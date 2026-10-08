# Session 6 report: evidence pieces, and sending the part of the vote the claim names

2026-10-08, from 23:11 UTC (the paired run ended on 2026-10-09), branch
`claude/eager-cannon-08bx1h` (from `main` after PR #9). Run by Rashad, with
Claude Code, autonomously on Rashad's instructions. Every number comes from an
actual run on the dev split, scored with the starter's `evaluate.py` (commit
`559b598`); the test split was never used. Runs: `docs/runs/2026-10-08_rashad_*`
(listed per part below); decisions:
`docs/decisions/2026-10-08-2311_rashad_session-6.md`.

Fixed decision (Rashad): task A evidence contains only what Apertus cited.

**In progress:** the paired run of Part 3 is running; its results, the summary and the recommendation follow when it ends.

<!-- PART3-SUMMARY -->

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

<!-- PART3 -->
