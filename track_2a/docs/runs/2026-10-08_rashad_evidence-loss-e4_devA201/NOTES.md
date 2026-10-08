### 2026-10-08, session 5, Steps 2 and 4: where E4's evidence is lost, and the realistic maximum (no model calls)

- Data: E4's `embed-e5-small` answers (`2026-10-08_rashad_section-k12-vs-embed-thinking_devA300/embed-e5-small`, model `apertus-v1.5-8b-thinking`), the 201 dev task A cases with gold label 0 or 2.
- Command (from `track_2a/`): `EMBED_MODEL_DIR=models/multilingual-e5-small python3 scripts/evidence_loss.py --run docs/runs/2026-10-08_rashad_section-k12-vs-embed-thinking_devA300/embed-e5-small --cases output/devA --out <folder>`, 22:27 to 22:39 UTC (script as committed in `7490a90`). Output: `summary.json`, `per_case.jsonl`.
- Checks: the starter's evidence rule, re-implemented, gives exactly the official 75/201 for these answers; the rebuilt chunks equal the pages E4 recorded in all 201 cases.
- Gold pages: the gold passage is cut into windows of 200 characters; a page holds a window when it matches at 90. The gold pages are the page holding most windows and the window-holding pages reachable from it with at most two pages in between. A sentence repeated far away (on a front summary page) does not make that page a gold page.
- Classes, checked in this order: **hit** (the answer's evidence matched); **gold page not sent** (no gold page among the 8 chunks' pages); **predicted neutral** (label 1, so no evidence); **gold page sent but not cited**; **cited but text did not match**.

| Where the evidence is lost | All 201 | Same-language (67) | Cross-language (134) |
|---|---|---|---|
| hit | 75 | 27 | 48 |
| gold page not sent | 23 | 2 | 21 |
| predicted neutral | 20 | 7 | 13 |
| **gold page sent but not cited** | **43** | 14 | 29 |
| cited but text did not match | 40 | 17 | 23 |

- Pages cited per answer with label 0 or 2 (176 answers): 2.91 on average (3.07 in the raw answers, before pages the model was not shown are dropped).
- Wrongly cited pages (cited, not gold pages): 347. Placed against the vote's detailed section (the selector's run of pages around the main gold page, without gap filling, in steps of at most two; anchored on the nearest kept page up to 10 pages before the gold page when needed): **32 before it (a front summary or cover page), in 18 answers**; 118 inside it; 197 after it.
- "Cited but text did not match" (40): in 27 the model cited only the first or last page of a passage that runs over several pages (that page also holds text outside the passage, so a whole-page item cannot match); in 7 another gold page that was sent would have matched as a whole page; in 16 no whole page of the booklet matches at all.
- **Step 4, cases where no whole page matches the gold passage: 23 of 201.** Reasons: page break, the passage runs over several pages and every page also holds other text (21); passage over 5,000 characters and over several pages (2); none was put down to PDF text differences alone. A gold page was sent in 21 of them; if the model had cited the right sent page, form (b) (its sent chunks) could have matched in 11, form (c) (chunks plus neighbours) in 2.
- **Realistic maximum with cited pages only** (Apertus cites a matching sent page whenever there is one, and answers 0 or 2): **0.657 (132/201) with whole-page items**, 0.642 with form (b), 0.642 with form (c); 0.756 if each cited page could give both a whole-page item and a sent-chunks item. With a perfect search (any page of the booklet, whole-page items): 0.886.
