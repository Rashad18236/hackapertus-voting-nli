### 2026-10-08, session 6, Part 0: evidence setting cited-pieces, E4's control answers re-scored (no model calls)

- Question: with only the pages Apertus cited in E4's `embed-e5-small` arm (`2026-10-08_rashad_section-k12-vs-embed-thinking_devA300/embed-e5-small`), does splitting each cited page into the pipeline's 1,000-character pieces, one item per piece, match the gold passage more often than whole pages?
- Setting `cited-pieces` (`src/evidence.py`): the cited pages that were shown, in the model's order, repeated pages once; each page split at whitespace into pieces of at most 1,000 characters (`parse._split`, as the embedding chunks); pieces taken in turn across the pages (first piece of each page, then the second of each, ...), at most five items. No page the model did not cite.
- Command (from `track_2a/`): `python3 scripts/rescore_evidence.py --run docs/runs/2026-10-08_rashad_section-k12-vs-embed-thinking_devA300/embed-e5-small --cases output/devA --evidence-a cited-pieces --out <folder>`, 23:17 UTC, commit `3081d38`; scored with the starter's `evaluate.py` (commit `559b598`); format check clean. With `--evidence-a cited` the same script reproduces E4's `predictions.jsonl` byte for byte.
- Labels, tokens and times are E4's, unchanged (Macro-F1 0.711). 205 answers carry evidence, 4.4 items each on average, 857 characters per item (at most 1,000).

| Claim type (`src/claim_router.py`) | Gold cases | `cited` (whole pages) | `cited-pieces` |
|---|---|---|---|
| summary ("according to the summary") | 55 | 5 (0.091) | 5 (0.091) |
| council ("the Federal Council holds") | 68 | 30 (0.441) | 48 (0.706) |
| committee ("the committee holds") | 27 | 12 (0.444) | 20 (0.741) |
| law ("according to the text put to the vote") | 25 | 13 (0.520) | 16 (0.640) |
| detail ("if the vote is accepted") | 26 | 15 (0.577) | 20 (0.769) |
| **all** | **201** | **75 (0.373)** | **109 (0.542)** |
| same-language / cross-language | 67 / 134 | 27 / 48 | 41 / 68 |

- **The starter's scorer confirms Rashad's re-score: 109 of 201 (0.542) against 75 (0.373).** No case found with whole pages is lost with pieces. The gain is entirely in session 5's class "cited, but its text did not match": 34 of its 40 cases now match (re-implemented rule of `scripts/evidence_loss.py`, which gives the official 75 and 109).
- Summary claims gain nothing (5 of 55 either way): their loss is that the gold page is not cited at all (34 of session 5's 43 "sent but not cited" cases are summary claims) or not sent (10).
- Consequence: `cited-pieces` becomes the default (own commit). Session 5's A-v4 citation prompt is not run: its "prefer the detailed section over the summary" would steer summary claims away from their gold page.
