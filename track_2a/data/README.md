# Data

| File | What it is |
|---|---|
| `raw/v1.1.parquet` | `OSTswiss/MNLIoverSwissVotingBooklets`, file `v1.1.parquet`, dataset commit `9ff08597`, downloaded 2026-10-08. MIT licence. 1,488 rows. |
| `dev_inputs.jsonl` | 300 dev cases in the beginner input format: `id`, `reference`, `claim`. No labels. |
| `dev_gold.jsonl` | Answers for the dev cases: `id`, `label`, `label_name`, `evidence`, `claim_language`, `reference_language`, `booklet`, `source_row`. |
| `test_inputs.jsonl` | 267 held-out test cases, same format as dev inputs. **Do not run on these until the final evaluation.** |
| `test_gold.jsonl` | Answers for the test cases. |
| `sample_beginner.jsonl` | The first two dev cases; the default input for `make run`. |

## How the splits were made

Script: `scripts/make_splits.py` (rerun it to get identical files). A single
random generator with seed 42 drives every random choice.

1. **Drop exact duplicates.** 335 of the 1,488 rows are exact copies of
   another row (all columns equal); 1,153 rows remain. No claim/reference pair
   occurs with two different labels. The first copy keeps its row number,
   recorded as `source_row` in the gold files.
2. **Split by booklet.** The dataset has no booklet id. One voting date
   (`booklet_publish_date`) is one booklet, published in German, French and
   Italian (three `booklet_url`s). We treat the voting date as the booklet,
   so the same text cannot appear in dev in one language and in test in
   another. There are 20 booklets.
3. **Test set.** 5 of the 20 booklets (25 %) are drawn at random:
   2020-02-09, 2021-03-07, 2022-02-13, 2022-05-15, 2025-09-28. All their 267
   deduplicated rows (23.2 % of rows) form the test set.
4. **Dev sample.** From the other 15 booklets (886 rows) we draw 300 rows,
   balanced over 27 cells: 3 labels x 9 (claim language, reference language)
   pairs. Each cell is shuffled, then one row is taken from each cell in turn
   until 300 rows are reached. Every cell had enough rows, so the result is
   11 or 12 rows per cell; labels are 102 / 99 / 99.
5. **Ids and order.** Rows are shuffled before ids (`dev-0001`, ...,
   `test-0001`, ...) are assigned, so neither the id nor the position says
   anything about label or language.

The dataset has **no gold evidence**, so `evidence` is `null` in both gold
files and evidence exact match / overlap F1 cannot be computed yet.

`reference_language` is used as the booklet language: v1.1 has no
`booklet_language` column, and `reference_language` always matches the
language in `booklet_url`.

Size: the whole `data/` directory is about 7 MB (limit 100 MB).
