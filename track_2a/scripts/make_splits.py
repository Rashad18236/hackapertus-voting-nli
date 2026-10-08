"""Freeze the dev and test splits, in the official request format.

Run from track_2a/:

    python3 scripts/make_splits.py --starter-cases DIR

where DIR holds cases.jsonl and expected-labels.jsonl written by the starter's
own prepare_cases.py for all rows and both tasks (see data/README.md). The
cases themselves come from the starter, unchanged; this script only decides
which rows go where and copies those lines.

Needs pandas and pyarrow (requirements-dev.txt); not part of the pipeline.

Row selection (unchanged since the baseline stage, see docs/decisions.md):
- drop exact duplicate rows (the first copy stays);
- a "booklet" is one voting date (booklet_publish_date): the same booklet text
  exists in de, fr and it, so splitting by language version would leak;
- 5 of the 20 booklets (25 %) go to test, the rest is the dev pool;
- dev is up to 300 rows from the pool, balanced over the 27 cells
  (3 labels x 9 language pairs) by round-robin;
- one random generator seeded with 42 drives every random choice.
Each selected row gives one task A and one task B case.
"""

import argparse
import json
import random
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw/v1.1.parquet"
DATA = ROOT / "data"
SEED = 42
N_TEST_BOOKLETS = 5
DEV_SIZE = 300


def balanced_sample(pool, size, rng):
    """Round-robin over (label, claim_language, reference_language) cells.

    Each cell is shuffled, then we take one row from every non-empty cell in
    turn until we have `size` rows. Small cells run out early and the larger
    ones fill the rest, so the result is as balanced as the data allows.
    """
    cells = {}
    for key, group in pool.groupby(["entailment_label", "claim_language", "reference_language"]):
        indices = list(group.index)
        rng.shuffle(indices)
        cells[key] = indices
    chosen = []
    while len(chosen) < size and any(cells.values()):
        for key in sorted(cells):
            if cells[key] and len(chosen) < size:
                chosen.append(cells[key].pop())
    return pool.loc[chosen]


def select_rows():
    """Return (dev rows, test rows, test booklets). Rows are positions in v1.1."""
    rng = random.Random(SEED)
    df = pd.read_parquet(RAW).drop_duplicates()  # keeps the first copy and its row position
    booklets = sorted(df["booklet_publish_date"].unique())
    test_booklets = sorted(rng.sample(booklets, N_TEST_BOOKLETS))
    test = df[df["booklet_publish_date"].isin(test_booklets)]
    pool = df[~df["booklet_publish_date"].isin(test_booklets)]
    dev = balanced_sample(pool, DEV_SIZE, rng)
    return sorted(int(i) for i in dev.index), sorted(int(i) for i in test.index), test_booklets


def row_of(case_id):
    """'v1.1-row-123-B' -> 123"""
    return int(case_id.split("-row-")[1].rsplit("-", 1)[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--starter-cases", type=Path, required=True,
                        help="directory with the starter's cases.jsonl and expected-labels.jsonl")
    args = parser.parse_args()

    dev_rows, test_rows, test_booklets = select_rows()
    lines = {}
    for name in ("cases.jsonl", "expected-labels.jsonl"):
        lines[name] = (args.starter_cases / name).read_text(encoding="utf-8").splitlines()

    for split, rows in (("dev", set(dev_rows)), ("test", set(test_rows))):
        (DATA / split).mkdir(exist_ok=True)
        for name, file_lines in lines.items():
            kept = [line for line in file_lines if row_of(json.loads(line)["id"]) in rows]
            (DATA / split / name).write_text("\n".join(kept) + "\n", encoding="utf-8")
        print(f"{split}: {len(rows)} rows -> {len(rows) * 2} cases (task A and B)")

    (DATA / "splits.json").write_text(json.dumps({
        "dataset": "OSTswiss/MNLIoverSwissVotingBooklets v1.1 (commit 9ff08597)",
        "seed": SEED,
        "test_booklets": test_booklets,
        "dev_rows": dev_rows,
        "test_rows": test_rows,
    }, indent=1) + "\n", encoding="utf-8")
    print(f"test booklets: {test_booklets}")


if __name__ == "__main__":
    main()
