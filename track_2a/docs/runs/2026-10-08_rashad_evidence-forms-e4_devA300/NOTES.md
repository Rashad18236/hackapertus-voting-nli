### 2026-10-08, session 5, Step 3: evidence text for the same cited pages, E4's control answers re-scored (no model calls)

- Question: with exactly the pages Apertus cited in E4's `embed-e5-small` arm (`2026-10-08_rashad_section-k12-vs-embed-thinking_devA300/embed-e5-small`), no page changed and none added, does another text per evidence item match the gold passage more often?
- Forms: **(a)** the whole cited page, split at 5,000 characters (the pipeline today, evidence setting `cited`); **(b)** the chunks of that page that were sent to Apertus, joined in page order, cut at 5,000 characters; **(c)** form (b) plus the neighbouring chunk on each side on the same page. One item per cited page for (b) and (c); at most five items.
- Command (from `track_2a/`): `EMBED_MODEL_DIR=models/multilingual-e5-small python3 scripts/evidence_forms.py --run docs/runs/2026-10-08_rashad_section-k12-vs-embed-thinking_devA300/embed-e5-small --cases output/devA --out <folder> --form a|b|c`, about 22:21 UTC (commit `6f592e0`); scored with the starter's `evaluate.py`; format check clean for all three. The rebuilt chunks equal the pages E4 recorded for every case; form (a) reproduces E4's evidence exactly (0 items changed).

| Form | Evidence score (official) |
|---|---|
| (a) whole page | **0.373 (75/201)** |
| (b) sent chunks of the page, joined | 0.368 (74/201) |
| (c) sent chunks plus neighbours | 0.358 (72/201) |

- **The whole page (a) stays best.** It is the existing setting `cited` and the default, so no new setting is registered and the default does not change.
- Why the chunks do not help: an item matches when its text lies almost entirely inside the gold passage, or contains it. A sent chunk is usually only part of what lies on the page, and joining several chunks (31 of 513 form-(b) items join chunks that are not next to each other) breaks the "inside the passage" alignment.
- Allowed by the guide? It says "An item can be a sentence, a paragraph, or the whole page, copied from the PDF text." Forms (b) and (c) are copied text, but an item joined from non-adjacent chunks is not one copied passage, so (b) is not clearly allowed as it stands.
- Outside the three forms (from `scripts/evidence_loss.py`, not stored as predictions): the whole page *and* its sent chunks as two items of the same page (at most five items) would reach 0.408 (82/201). Not registered; proposed in the session 5 report.
