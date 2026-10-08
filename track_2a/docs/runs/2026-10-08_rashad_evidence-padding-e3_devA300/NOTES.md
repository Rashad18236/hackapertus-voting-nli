### 2026-10-08, Part 3: evidence padding, E3's answers re-scored (no model calls)

- **What the starter's scorer does with evidence** (`evaluate.py`, commit `559b598`, read in full): for every gold entailment or contradiction case it takes the first five evidence items (`MAX_QUOTES = 5`); a case is found when any of them matches the gold passage (normalised `partial_ratio` >= 90). An item longer than 5,000 characters after normalising never matches. **Extra items are not penalised**: wrong items, items after the fifth, page numbers and the predicted label play no role. Gold-neutral cases are not scored for evidence. Pages are not checked.
- Method: E3's answers are kept as they are (labels, tokens, times copied), only the evidence is rebuilt with `src/evidence.py` setting `cited-then-retrieved`: the items of the pages the model cited, then the other pages the model was shown (from `context_pages` in E3's raw answers), most similar to the claim first (e5-small, a page's best chunk), split at 5,000 characters, until five items. Answers with label 1 get no evidence, as in the pipeline. The `_all-labels` folders pad label-1 answers too (cited pages from the raw answer, then retrieved pages); that is for information only, the pipeline never does it. Failed calls keep no evidence.
- Commands (from `track_2a/`): `EMBED_MODEL_DIR=models/multilingual-e5-small python3 scripts/pad_evidence.py --run docs/runs/2026-10-08_rashad_embed-vs-section_devA300/<arm> --cases output/devA --out <folder> [--all-labels]`, 19:30 to 19:31 UTC; scored with the starter's `evaluate.py`; format check clean for all four.

| E3 arm | Evidence before (E3) | Padded, labels 0 and 2 | Padded, all labels (information only) |
|---|---|---|---|
| embed-e5-small | 0.383 (77/201) | **0.522 (105/201)** | 0.567 (114/201) |
| vote-section | 0.095 (19/201) | **0.264 (53/201)** | 0.358 (72/201) |

- Macro-F1 does not change (0.721 and 0.561): labels are untouched.
- Evidence changed in 159 of 300 embedding answers and 108 of 300 vote-section answers; the rest had no room (five items already) or label 1.
- **Kept as a named setting, off by default:** `--evidence-a cited-then-retrieved` (`Settings.evidence_a`). It costs no tokens; it embeds the pages the model was shown with e5 (CPU time), unless they are already cached.
- Not verified: whether the organisers' official evaluation also ignores extra items (the starter is the only scorer we have); asked in the report's open questions.
