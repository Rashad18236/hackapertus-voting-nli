# Decisions

One line per decision, with the reason. Newest stage at the bottom.

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

## Contract alignment stage (2026-10-08)

### Sources of truth

- **The organisers' guide is saved as `docs/official_contract.md` and wins over CLAUDE.md.** Future sessions and the technical report need the exact wording.
- **The starter repository (`gitlab.com/ifsoftware/hackapertus-starter`, commit `559b598`) is cloned outside our repository and not copied in.** It has no licence file and our repository is public; we run its scripts unchanged from the clone.
- **The starter's scripts run in its own locked environment (`uv sync --locked`).** That way they run with exactly the dependency versions it pins (rapidfuzz 3.14.6, scikit-learn 1.9.1).
- **Items 1, 2, 3, 4, 5 and 7 were started from the guide before the starter URL arrived; all were checked against the starter afterwards.** The guide gave exact field names, flags and rules. Nothing had to be redone.

### Entry point and requests (items 1, 3, 4)

- **The entrypoint is `python -m src.cli --input ... --output ...`, with both flags required and input ≠ output enforced.** This follows the contract and the starter's `main.py`.
- **The task is taken from the request: `booklet` → A, `reference` → B; anything else is an invalid request.** The contract says each request has exactly one of the two.
- **Task A is a placeholder that returns label 1 with no model call, marked by `TASK_A_PLACEHOLDER` in the code and "task A placeholder" in the stderr summary.** No extra fields go into the response, since unknown fields could make a strict scorer reject it.
- **The fallback label for every failure is 1 (neutral).** As instructed; a missing response is always wrong, while neutral is right for about a third of cases. This replaces the baseline rule "never guess a label".
- **Failures are counted by kind (invalid request, model call failed, unparseable answer, task A placeholder) and summarised on stderr.** Fallbacks must stay visible even though the output looks valid.
- **A line with broken JSON or without `id` is logged and skipped.** There is no id to answer, so no valid response is possible.
- **Any unexpected exception inside a case becomes a label 1 response.** One bad case must not stop the run.
- **Raw model answers are written only with `--raw` (development).** Judges get only the predictions file in `/output`.
- **Responses keep only the contract fields (`id`, `label`, `label_name`, `evidence`, `metrics`).** The baseline's extra `parse_failure` and `error` fields are gone; failures now live in the stderr summary and the `--raw` file.

### Variables (item 2)

- **`BASE_URL`/`API_KEY` are read first, then `LLM_BASE_URL`/`LLM_API_KEY`.** These are the official names first, with our local `.env` names kept so that `.env` needs no change.
- **The model comes from `MODEL`, then `LLM_NAME`, then `swiss-ai/Apertus-v1.5-8B`.** The guide names no model variable; `LLM_NAME` keeps the user's Public AI name working.
- **The `User-Agent` header stays on every request.** Public AI requires it, and other endpoints ignore it.

### Task B prompt (item 5)

- **Prompt `v2-label-only` asks only for `{"label": n}`, and evidence is always `[]`.** Task B evidence is not scored; it also removes the long quotes that broke the JSON.
- **The label definitions now include the guide's wording (supports / insufficient information / refutes).** Those are the official definitions.
- **`max_tokens` is 32.** A label-only JSON object needs about 7 tokens; the extra room covers a code fence. Output tokens are not scored, and a cut-off answer would become a fallback.
- **`vote` is not used in the task B prompt yet.** Item 5 only removes the evidence request. Adding the vote name is a separate prompt experiment (see `baseline_review.md`, section 3b).

### Data and scoring (item 6)

- **Dev and test cases are the starter's `prepare_cases.py` output, filtered to our rows.** The rows are the same as the baseline (verified), so old and new runs cover the same cases.
- **Row positions are used as the link between our split and the starter's ids.** The starter ids are `v1.1-row-<position>-<task>`; `v1.1.jsonl` and our parquet have identical row order (verified row by row).
- **`--download-booklets` is not used yet.** Task A is a placeholder; the PDFs come with the task A stage.
- **The row selection is stored in `data/splits.json`.** Ids no longer carry our split, and the self-checks need it.
- **The old `dev_inputs`/`dev_gold`/`test_*`/`sample_beginner` files were removed.** They are replaced by the official format and remain in git history (commit `305dd3d`).
- **Our `evaluate.py` is reduced to breakdowns and copies the starter's validity rules** (label_name must match, duplicate ids are invalid, Macro-F1 over present classes). The two must agree; the self-check shows a difference of 0 on dummies, gold and the real run.
- **Our evidence exact-match and overlap metrics were removed.** Task B evidence is not scored, and the starter scores task A evidence.
- **`scripts/baseline_review.py` was removed.** It reads the deleted pre-contract files; the review it produced stays.
- **Language pairs are written source→claim.** This matches the starter's report.

### Docker (items 1 and 7)

- **Only `requirements.txt` and `src/` are copied into the image; `.dockerignore` also excludes `data/`, `examples/`, `docs/`, `tests/`, `scripts/`, `.env*` and `**/__pycache__`.** No data, gold labels or secrets can reach the image; the first build showed that root-only `__pycache__/` patterns leak.
- **`--platform linux/amd64` is passed by the Makefile, not hardcoded in `FROM`.** Docker warns against a constant `FROM --platform`.
- **`make run` uses `--read-only --tmpfs /tmp`.** That enforces "write only to /output and /tmp" instead of trusting it.
- **`make run` mounts only the cases file (`CASES`), and optionally `BOOKLETS`, never a whole data folder.** `expected-labels.jsonl` must stay outside the prediction container.
- **`PYTHONDONTWRITEBYTECODE=1` is set in the image.** On a read-only filesystem Python cannot write `.pyc` files anyway.

### Rerun (item 8)

- **The task B rerun goes through `make run` in Docker, on `data/dev/cases.jsonl` (all 600 cases).** It tests the real entrypoint and mixed input; the 300 task A placeholders cost no model calls.
- **The run artefacts (predictions, raw answers, official and breakdown scores, start/finish times) are committed in `docs/runs/contract-v2-dev/`.** That lets the results row be checked and rescored without new calls.
- **The failed call (HTTP 502) was not rerun; it kept its fallback label 1.** That is exactly what a judge run would get.
- **The old results row is kept and marked "pre-contract".** As instructed; its failure handling and scorer differ, so the two rows are not directly comparable.

### Notes from the official challenge page

- **The page asks for the README's label definitions, but the README has none (still licence-only on 2026-10-08), so the prompt keeps the guide's wording.** Quoting text that does not exist is impossible; the CLAUDE.md note says to check again before each prompt change.
- **Local booklet parsing is assumed to be allowed until the organisers say otherwise.** The contract says "local parsing, OCR, or embeddings may run locally".
