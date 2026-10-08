### 2026-10-08, Part 1: why E3's embedding arm was wrong (search miss or reading error), no model calls

- Question: for every wrong answer of E3's `embed-e5-small` arm (`2026-10-08_rashad_embed-vs-section_devA300/embed-e5-small`), was the gold passage among the chunks the model saw?
- Command (from `track_2a/`, after `scripts/retrieval_check.py --fill-cache`): `EMBED_MODEL_DIR=models/multilingual-e5-small python3 scripts/search_or_reading.py --run docs/runs/2026-10-08_rashad_embed-vs-section_devA300/embed-e5-small --cases output/devA --out <folder>`; finished 19:16 UTC. Output: `summary.json`, `per_case.jsonl`.
- The chunks were rebuilt with the variant's own code; their pages equal the pages recorded in the run for all 300 cases, and the hit rate reproduces the earlier retrieval check exactly (0.741 on the 201 gold entailment and contradiction cases).
- Rule: a wrong answer on a gold entailment or contradiction case is a *search miss* when no chunk sent matches the gold passage (the hit rule of `retrieval_check.py`), otherwise a *reading error*. Gold-neutral cases have no gold passage, so a wrong answer there is a reading error by definition. The 5 failed calls (HTTP 504, label-1 fallback) are counted apart.

| Wrong answers | Search miss | Reading error | Correct | Failed call |
|---|---|---|---|---|
| gold entailment, same-language | 0 | 10 | 24 | 0 |
| gold entailment, cross-language | 7 | 17 | 44 | 0 |
| gold contradiction, same-language | 2 | 6 | 25 | 0 |
| gold contradiction, cross-language | 9 | 6 | 51 | 0 |
| gold neutral (no passage to find) | – | 27 (10 same-language, 17 cross) | 67 | 5 |
| **All** | **18** | **66** | **211** | **5** |

- **Most errors are reading errors: 66 of 84 wrong answers.** Better search can fix at most the 18 search misses (21 % of the wrong answers), and 16 of those are cross-language.
- The largest single error: gold entailment answered contradiction although the gold passage was sent (21 cases). Gold contradiction answered neutral after a search miss: 10 cases.
- Of the correct answers on gold entailment and contradiction cases, 24 % were right without the gold passage among the chunks (hit rate 0.764 for correct answers, 0.684 for wrong ones): facts repeat across the booklet, for example in the summary at the front.
