"""Freeze the validation set "val": task A cases from rows in neither dev nor test (session 7).

Run from track_2a/:

    python3 scripts/make_val.py --starter-cases DIR

where DIR holds cases.jsonl and expected-labels.jsonl written by the starter's
own prepare_cases.py for all rows (as for scripts/make_splits.py). The cases
come from the starter unchanged; this script only decides which rows go where
and copies the task A lines.

Rows:
- the deduplicated dataset rows (the first copy stays, as in make_splits.py)
  that are neither dev rows nor in a test booklet (data/splits.json): 586;
- minus ROUTER_ROWS, the six rows whose claim openings were used to add
  patterns to src/claim_router.py in session 6 (they would not be unseen):
  580 rows.
Their booklets are the 15 dev booklets (voting dates); test booklets are
excluded by construction.

The paired run uses a balanced sample of SAMPLE_SIZE rows: make_splits.py's
round-robin over (label, claim language, booklet language), seed 42.

Writes data/val/cases.jsonl and expected-labels.jsonl (all 580), the same two
files for the sample in data/val/sample300/, and data/val/rows.json. The
expected labels never go into the prediction container (data/ is not in the
Docker build context).
"""

import argparse
import json
import random
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from make_splits import RAW, balanced_sample, row_of  # noqa: E402

DATA = ROOT / "data"
SEED = 42
SAMPLE_SIZE = 300
# Rows 323, 592, 756, 1068, 1078 and 1301: the six claims the session 6 router did not match on the
# rows outside dev and test, for which four patterns were added ("In der Zusammenfassung",
# "Im Abstimmungstext", "Si cette proposition / la motion est adoptée", "L'adoption du vote").
ROUTER_ROWS = (323, 592, 756, 1068, 1078, 1301)


def val_rows():
    splits = json.loads((DATA / "splits.json").read_text(encoding="utf-8"))
    df = pd.read_parquet(RAW).drop_duplicates()
    test_dates = set(splits["test_booklets"])
    dates = df["booklet_publish_date"].astype(str).str[:10]
    pool = df[~dates.isin(test_dates) & ~df.index.isin(splits["dev_rows"]) & ~df.index.isin(splits["test_rows"])]
    assert len(pool) == 586, len(pool)
    return df, pool[~pool.index.isin(ROUTER_ROWS)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--starter-cases", type=Path, required=True)
    args = ap.parse_args()

    df, val = val_rows()
    sample = balanced_sample(val, SAMPLE_SIZE, random.Random(SEED))
    lines = {name: (args.starter_cases / name).read_text(encoding="utf-8").splitlines()
             for name in ("cases.jsonl", "expected-labels.jsonl")}
    for folder, rows in ((DATA / "val", set(val.index)), (DATA / "val" / "sample300", set(sample.index))):
        folder.mkdir(parents=True, exist_ok=True)
        for name, file_lines in lines.items():
            kept = [line for line in file_lines
                    if json.loads(line)["id"].endswith("-A") and row_of(json.loads(line)["id"]) in rows]
            assert len(kept) == len(rows), (folder, name, len(kept), len(rows))
            (folder / name).write_text("\n".join(kept) + "\n", encoding="utf-8")
        print(f"{folder.relative_to(ROOT)}: {len(rows)} task A cases")
    (DATA / "val" / "rows.json").write_text(json.dumps({
        "dataset": "OSTswiss/MNLIoverSwissVotingBooklets v1.1 (commit 9ff08597)",
        "definition": "deduplicated rows in neither dev nor test (586), minus the six router-pattern rows",
        "excluded_router_rows": list(ROUTER_ROWS),
        "val_rows": sorted(int(i) for i in val.index),
        "sample300_seed": SEED,
        "sample300_rows": sorted(int(i) for i in sample.index),
    }, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
