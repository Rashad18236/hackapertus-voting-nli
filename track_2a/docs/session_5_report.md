# Session 5 report: where the task A evidence score is lost

2026-10-08, from 22:00 UTC, branch `claude/eager-cannon-08bx1h-evidence`
(stacked on PR #8). Run by Rashad, with Claude Code. **No model calls**: every
number comes from E4's saved answers (`embed-e5-small`, the default, on
`apertus-v1.5-8b-thinking`), re-read offline and scored with the starter's
`evaluate.py`. The test split was never used. Runs:
`docs/runs/2026-10-08_rashad_evidence-loss-e4_devA201/` and
`docs/runs/2026-10-08_rashad_evidence-forms-e4_devA300/`; decisions:
`docs/decisions/2026-10-08-2200_rashad_session-5.md`.

Fixed decision for this session (from Rashad): task A evidence holds only
pages Apertus cited. No padding with other pages; the `cited-then-retrieved`
setting stays in the code, off, and was not used.

## 1. In short

- E4's evidence score is 0.373: the evidence matched the gold passage in 75
  of 201 cases.
- **The biggest loss is pages that were sent but not cited (43 cases)**:
  Apertus saw the page with the gold passage and cited other pages.
- Next comes the right page cited but its text not matching (40). Mostly
  Apertus cited only the first or last page of a passage that runs over
  several pages; such a page also holds other text, so it cannot match.
- Shorter evidence (only the parts of a page that were sent) does not help:
  0.368 and 0.358 against 0.373 for the whole page. The whole page stays.
- If Apertus always cited the right page among those it was sent, the score
  could reach 0.657 with whole pages. That is the realistic maximum with
  today's search.
- Recommendation: change the citation instruction in the prompt (proposed
  below, not run: it needs model calls).

## 2. Step 1: how the scorer matches a task A evidence item

From the starter's `evaluate.py` (commit `559b598`), short quotes with line
numbers:

- **What is compared with what.** Each evidence item's `text` is compared
  with the gold passage (`reference` in `expected-labels.jsonl`), both
  normalised first:
  > 35: `text = unicodedata.normalize("NFKC", text).replace("­", "")`
  > 36: `text = re.sub(r"(\w) ?-\s*\n\s*(\w)", r"\1\2", text)  # words hyphenated across lines`
  > 37: `return re.sub(r"\s+", " ", text).strip().lower()`
- **The threshold and the length limit.**
  > 26: `MAX_QUOTE_CHARS = 5000  # about one booklet page: 95% of pages are shorter`
  > 47: `if not quote or len(quote) > max_chars:` / 48: `return False`
  > 49: `return fuzz.partial_ratio(quote, passage) >= min_ratio`
  > 101: `parser.add_argument("--min-ratio", type=float, default=90, ...)`

  `partial_ratio` slides the shorter text along the longer one (lines
  43-44: "a short quote from the passage and a page that contains the
  passage both match"). An item therefore matches when it lies almost
  entirely inside the gold passage, or when it contains the whole passage.
  The 5,000-character limit counts the normalised text.
- **The page.** It is not checked. The code never reads `page`, and the
  starter's README says so (line 208: "Evidence pages are not checked yet.").
- **The first five items.**
  > 25: `MAX_QUOTES = 5`
  > 72: `return [item["text"] for item in evidence[:MAX_QUOTES]`

  Items after the fifth are ignored. One matching item among the first five
  is enough, and extra or wrong items cost nothing.
- **Which cases count.**
  > 145: `if task == "A" and gold["label"] != 1:`
  > 151: `elif prediction and any(quote_matches(q, passage, ...) for q in quotes_of(prediction)):`

  Only gold entailment and contradiction cases count, whatever label was
  predicted. A neutral answer gives no evidence, so it is a miss.

The organisers' guide (`docs/official_contract.md`, lines 68, 91 and 93)
says the same in words: "a verbatim quote in the source's original
language, or the text of the page it is on", at most about 5,000
characters, "Only the first five evidence items are scored", quote "from the
section of the booklet that deals with the vote in detail", and "An item can
be a sentence, a paragraph, or the whole page, copied from the PDF text."

## 3. Step 2: where the evidence is lost

Each of the 201 cases falls into exactly one class, checked in this order.
A "gold page" is a page that holds part of the gold passage (found by
matching 200-character pieces of it, see the run's notes).

| E4, embed-e5-small | All 201 | Same language (67) | Cross-language (134) |
|---|---|---|---|
| Hit: the evidence matched | 75 | 27 | 48 |
| Gold page not sent: the search missed it | 23 | 2 | 21 |
| Predicted neutral: no evidence given | 20 | 7 | 13 |
| **Gold page sent, but not cited** | **43** | 14 | 29 |
| Gold page cited, but its text did not match | 40 | 17 | 23 |

- Apertus cites 2.9 pages per answer (answers with label 0 or 2).
- 347 cited pages are not gold pages:
  - 32 lie before the vote's detailed section, on a front summary or cover
    page, in 18 answers;
  - 118 lie inside the detailed section;
  - 197 lie after it.
- Of the 40 "cited, but no match" cases:
  - in 27 Apertus cited only the first or last page of a passage spread
    over several pages;
  - in 7 another gold page that was sent would have matched;
  - in 16 no single page of the booklet matches the passage.

## 4. Step 3: other evidence text for the same cited pages

Same pages, none added, only the text of each item changed (official
scorer):

| Item text | Evidence score |
|---|---|
| (a) the whole page (today, setting `cited`) | **0.373** |
| (b) the parts of the page that were sent to Apertus | 0.368 |
| (c) those parts plus the text next to them on the same page | 0.358 |

The whole page stays best, so no new setting and no default change. The
sent parts are usually only a piece of what the page holds about the vote.
Joining parts that are not next to each other (31 of 513 items) also breaks
the "lies inside the passage" match, and such a joined item is not one
passage copied from the PDF, as the guide asks.

Outside the three forms, one combination would help: the whole page *and*
its sent parts as two items of the same page reach 0.408, with no page
added. It is not registered; the team should decide whether it fits
"cited pages only".

## 5. Step 4: the realistic maximum

- In 23 of the 201 cases, no whole page matches the gold passage at all:
  - 21: the passage runs over a page break, and every page also holds other
    text;
  - 2: the passage is longer than 5,000 characters and spans several pages.

  None was due only to differences between the PDF text and the gold text.
  A gold page was sent in 21 of these cases. The sent parts, form (b),
  could have matched in 11 of them, and form (c) in 2.
- **Realistic maximum with cited pages only, today's search, whole-page
  items: 0.657 (132 of 201).** That assumes Apertus cites a matching sent
  page whenever there is one, and answers 0 or 2. With items made of the
  sent parts it is 0.642; with both item kinds per page, 0.756. With a
  perfect search (any page of the booklet), whole pages could reach 0.886.
- The gap between today's 0.373 and 0.657 comes from citation and from
  neutral answers. The gap from 0.657 to 0.886 comes from search: in 46
  cases a matching page exists in the booklet but was not among the pages
  sent (35 of them cross-language; in 21 no gold page was sent at all).

## 6. Recommendation: change the citation instruction

"Gold page sent but not cited" is the largest loss (43 cases), so the next
step is a change to the citation instruction in the task A prompt. Proposed,
not run; it needs model calls:

- **A new prompt version** (for example `A-v4-excerpts`, leaving
  `A-v3-excerpts` unchanged). It would ask Apertus to:
  - cite every page that holds the passage supporting or refuting the
    claim;
  - when that passage continues on the next or previous page, cite those
    pages too;
  - prefer the pages of the vote's detailed section over the short summary
    at the front.

  This targets both the 43 uncited gold pages and the 27 answers that cited
  only a boundary page.
- **A paired run** on all 300 dev task A cases: `embed-e5-small` with
  `A-v3-excerpts` against the same with the new prompt, json_schema, one
  model name for the whole run. Report the evidence score, Macro-F1 (it must
  not drop by more than 0.02), and the classes of Step 2 again. It would
  cost about 2 × 300 × 1,900 input tokens.

## 7. What could not be verified

- How the official evaluation matches evidence. Only the starter's scorer
  was available; it does not check pages, and the official one might.
- That E4's answers on `apertus-v1.5-8b-thinking` cite pages the way
  `apertus-v1.5-8b` would. The two answered alike in the 20-case check, but
  citations were not compared separately.
- The gold page locations come from fuzzy matching of 200-character pieces,
  not from a page number in the dataset (the dataset has none). A page with
  little matching text could be misplaced.
