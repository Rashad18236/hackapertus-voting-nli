"""Freeze the dev and test splits from data/raw/v1.1.parquet.

Run from track_2a/:  python3 scripts/make_splits.py
Needs pandas and pyarrow (requirements-dev.txt); not part of the pipeline.

Rules (see data/README.md and docs/decisions.md):
- drop exact duplicate rows;
- a "booklet" is one voting date (booklet_publish_date): the same booklet text
  exists in de, fr and it, so splitting by language version would leak;
- 5 of the 20 booklets (25 %) go to test, the rest is the dev pool;
- dev is up to 300 rows from the pool, balanced over the 27 cells
  (3 labels x 9 language pairs) by round-robin;
- one random generator seeded with 42 drives every random choice.
"""

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
LABEL_NAMES = {0: "entailment", 1: "neutral", 2: "contradiction"}


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


def write_split(frame, name, rng):
    """Write <name>_inputs.jsonl (no labels) and <name>_gold.jsonl."""
    order = list(frame.index)
    rng.shuffle(order)  # so row order says nothing about label or language
    frame = frame.loc[order]
    with open(DATA / f"{name}_inputs.jsonl", "w", encoding="utf-8") as fi, \
         open(DATA / f"{name}_gold.jsonl", "w", encoding="utf-8") as fg:
        for i, (source_row, row) in enumerate(frame.iterrows(), start=1):
            case_id = f"{name}-{i:04d}"
            fi.write(json.dumps({
                "id": case_id,
                "reference": {"text": row["reference_string"]},
                "claim": {"text": row["claim"]},
            }, ensure_ascii=False) + "\n")
            fg.write(json.dumps({
                "id": case_id,
                "label": int(row["entailment_label"]),
                "label_name": LABEL_NAMES[int(row["entailment_label"])],
                "evidence": None,  # the dataset has no gold evidence
                "claim_language": row["claim_language"],
                "reference_language": row["reference_language"],
                "booklet": row["booklet_publish_date"],
                "source_row": int(source_row),
            }, ensure_ascii=False) + "\n")


def main():
    rng = random.Random(SEED)
    df = pd.read_parquet(RAW).drop_duplicates()  # keeps the first copy and its row index

    booklets = sorted(df["booklet_publish_date"].unique())
    test_booklets = sorted(rng.sample(booklets, N_TEST_BOOKLETS))
    test = df[df["booklet_publish_date"].isin(test_booklets)]
    pool = df[~df["booklet_publish_date"].isin(test_booklets)]
    dev = balanced_sample(pool, DEV_SIZE, rng)

    write_split(dev, "dev", rng)
    write_split(test, "test", rng)

    print(f"rows after dedup: {len(df)}")
    print(f"test booklets: {test_booklets} -> {len(test)} rows ({len(test) / len(df):.1%})")
    print(f"dev pool: {len(pool)} rows from {len(booklets) - N_TEST_BOOKLETS} booklets; dev sample: {len(dev)}")
    print("dev labels:", dev["entailment_label"].value_counts().sort_index().to_dict())
    print(pd.crosstab([dev["claim_language"], dev["reference_language"]], dev["entailment_label"]))


if __name__ == "__main__":
    main()
