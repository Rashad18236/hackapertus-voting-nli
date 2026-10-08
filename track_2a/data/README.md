# Data

| Path | What it is |
|---|---|
| `raw/v1.1.parquet` | `OSTswiss/MNLIoverSwissVotingBooklets`, file `v1.1.parquet`, dataset commit `9ff08597`, downloaded 2026-10-08. MIT licence. 1,488 rows. Used for the profile and the row selection. |
| `dev/cases.jsonl` | 600 requests (300 rows × task A and B) in the official format. No labels. |
| `dev/expected-labels.jsonl` | Gold labels for dev (and the gold passage for non-neutral rows), as written by the starter. **Never mount this into the prediction container.** |
| `test/cases.jsonl`, `test/expected-labels.jsonl` | 534 held-out requests (267 rows × 2) and their labels. **Do not run on these until the final evaluation.** |
| `splits.json` | Which dataset rows are in dev and test, the test booklets, and the seed. |

`examples/cases.jsonl` (outside `data/`) holds two dev requests, one task A
and one task B, for `make run`.

## How the files were made

1. **Generate all cases with the starter.** In a checkout of
   `https://gitlab.com/ifsoftware/hackapertus-starter` (commit `559b598`),
   after `uv sync --locked`:

   ```bash
   uv run python prepare_cases.py --output-dir /some/dir
   ```

   This downloads `v1.1.jsonl` from the dataset's `main` branch (still commit
   `9ff08597` on 2026-10-08) and writes 2,976 cases (1,488 rows × 2 tasks) with
   ids `v1.1-row-<row>-<A|B>`, plus `expected-labels.jsonl`. We did not pass
   `--download-booklets`: task A is a placeholder so far.
2. **Select rows and copy their lines** (from `track_2a/`):

   ```bash
   python3 scripts/make_splits.py --starter-cases /some/dir
   ```

   Lines are copied unchanged. Row positions in `v1.1.jsonl` and
   `raw/v1.1.parquet` were checked to be identical.

### Row selection

One random generator with seed 42 drives every random choice; rerunning gives
identical files.

1. **Drop exact duplicates.** 335 of the 1,488 rows are exact copies of
   another row; the first copy stays (1,153 rows). No claim/reference pair
   occurs with two different labels.
2. **Split by booklet.** One voting date (`booklet_publish_date`) is one
   booklet, published in German, French and Italian. We split by voting date
   so the same text cannot be in dev in one language and in test in another.
   There are 20 booklets.
3. **Test:** 5 of the 20 booklets (25 %), drawn at random: 2020-02-09,
   2021-03-07, 2022-02-13, 2022-05-15, 2025-09-28. All their 267 rows (23.2 %
   of deduplicated rows).
4. **Dev:** 300 rows from the other 15 booklets (886 rows), balanced over 27
   cells (3 labels × 9 claim/source language pairs) by round-robin: 11 or 12
   rows per cell; labels 102 / 99 / 99. Each row gives a task A and a task B
   case.

These are the same rows as in the pre-contract baseline (`baseline-v0`);
only the file format changed.

Size: the whole `data/` directory is about 10 MB (limit 100 MB).
