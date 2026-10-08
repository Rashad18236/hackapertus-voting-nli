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
