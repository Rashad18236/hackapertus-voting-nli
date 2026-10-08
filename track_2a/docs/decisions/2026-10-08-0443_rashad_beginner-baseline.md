## Beginner baseline stage (2026-10-08)

### Data and splits

- **A booklet is one voting date (`booklet_publish_date`).** v1.1 has no booklet id, and each date has one booklet in de, fr and it; splitting by URL would put the same text in dev and test in different languages.
- **`reference_language` stands in for `booklet_language`.** v1.1 has no `booklet_language` column, and `reference_language` always matches the language code in `booklet_url`.
- **Exact duplicates are dropped and the first copy is kept.** 335 rows are full copies; keeping them would count the same case twice in scores.
- **5 of 20 booklets (25 %) go to test, drawn with seed 42.** That is in the 20 to 30 % range, and those booklets hold 23.2 % of the rows.
- **The dev sample uses round-robin over 27 cells (label × language pair).** It is the simplest way to get "as balanced as the data allows"; every cell had enough rows, so cells hold 11 or 12.
- **Rows are shuffled before ids are assigned, and ids are `dev-NNNN` / `test-NNNN`.** That way neither id nor file position reveals label, language or source row.
- **The rule "no gold id in any inputs file" is read as: no id crosses splits, and inputs files hold only id, reference and claim.** A split's own ids must appear in its inputs file, otherwise predictions could not be matched to gold.
- **Gold evidence is `null`.** The dataset has no evidence column; we do not invent one.
- **`sample_beginner.jsonl` now holds the first two dev cases.** The old sample rows (300 and 1281) fell into test booklets.
- **The raw parquet (2.7 MB, MIT licence) is committed.** It is small, the licence allows it, and it makes the splits reproducible offline.
- **pandas, pyarrow, scikit-learn and pytest are listed in `requirements-dev.txt` only.** They are needed for profiling, splits and checks, not by the pipeline; the Docker image stays small.

### Evaluation

- **`evaluate.py` is plain Python; scikit-learn is used only in the self-check.** Every number can be traced by hand, and sklearn serves as an independent check.
- **A missing or unparseable prediction counts as a false negative for its gold class and a false positive for none.** It is "counted as wrong" without inventing a predicted class, and it matches sklearn with an out-of-range label.
- **Precision, recall and F1 are 0 when the denominator is 0.** This is the usual convention and the same as sklearn's `zero_division=0`.
- **p95 uses the nearest-rank method (value at position ceil(0.95·n)).** It is easy to check on paper and always a value that actually occurred.
- **Evidence normalisation: a hyphen + line break between two letters is removed, whitespace is collapsed, text is lowercased.** That is what "line-break hyphenation, whitespace and case" asks for, and real hyphens such as "Covid-19" stay.
- **Overlap F1 is word-level bag-of-words F1 (SQuAD style); with several predicted passages, the best one counts.** This is the standard, simple definition of overlap.
- **`evidence_given_rate` (the share of entailment/contradiction predictions with kept evidence) was added.** With no gold evidence it is the only evidence signal available on this dataset.
- **The random dummy is accepted between 0.27 and 0.40.** That is about ±2 standard errors around 1/3 for 300 cases; one fixed seed keeps it reproducible.
- **The tests are written with `unittest` and run with pytest or `python -m unittest`.** They need no extra dependency.

### Prompt and parsing (`v1-json`)

- **System message holds the instructions; user message holds the reference and claim; the prompt is in English.** This follows the brief, and claims and references are never translated.
- **Labels are asked for as numbers 0/1/2, with names and definitions in the prompt.** The numbers match the output format, and the definitions include "true in the real world but not covered = neutral".
- **The model is asked for "the shortest passage ... copied character for character".** Shorter quotes are more likely to be exact and closer to a gold passage.
- **`max_tokens` is 400.** It is enough for a JSON object with one passage; too low would cut the JSON and cause parse failures.
- **The parser takes the first JSON object in the answer (code fences and prose are tolerated).** The 10-case trial showed clean JSON, but small models often add fences.
- **Labels are accepted as int, digit string or exact label name; anything else is a parse failure with `label: null`.** These forms are unambiguous; anything else would be a guess.
- **Evidence matching allows whitespace and letter-case differences and returns the reference's own characters.** The output stays verbatim. The trial showed a quote that differed only in a capitalised first word.
- **Evidence for neutral predictions is dropped.** The output format says evidence may be empty for neutral, and it cannot justify "not covered".
- **A failed API call gives `label: null`, `error`, 0 tokens, and the run continues.** One failure should not lose 299 other predictions; there are still no retries.
- **`label: null` in the output is acceptable for dev runs only.** The submission format needs an int; how to handle failures there is an open decision for a later stage.

### Running

- **The baseline ran on the host (`python -m src.cli`), not in Docker.** In this sandbox containers need proxy flags; the code is identical, and Docker was verified separately.
- **Run outputs (predictions and raw answers) are committed in `docs/runs/`.** That lets the review and results be traced and rescored without new API calls.
- **The 10 trial cases (dev-0001 to dev-0010) are part of the full dev run.** Only the parser was changed after seeing them; the prompt was not tuned on them.
- **Branch `baseline-v0` was made from the setup branch, not `main`.** `main` does not contain the setup work yet; nothing is merged into `main`.

### After the baseline run

- **The prompt's label definitions are our own.** The brief points to definitions in the dataset README, but the README (commit `9ff08597`) contains only the licence. The 0/1/2 order is confirmed by the data; finer rules are not.
- **Failed calls (HTTP 504) were not rerun.** Rerunning only the failures would mix two runs in one row; they count as wrong, as the rules for this stage say.
- **Mean input tokens and mean time in `results.md` include failed calls (0 tokens, about 61 s).** These are the numbers `evaluate.py` reports; the values without failed calls are given in the run notes.
- **Section 3b of the review uses a word-overlap measure on same-language cases only.** Word overlap across languages means nothing; it is a diagnostic, not part of the pipeline.
