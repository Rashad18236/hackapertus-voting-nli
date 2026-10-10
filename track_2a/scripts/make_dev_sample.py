"""A balanced sample of dev task A cases (session 9, phase E1: the context curve). Changes no split.

Run from track_2a/:

    python3 scripts/make_dev_sample.py --size 100 --out output/devA100

The dev rows (data/splits.json) are sampled with make_splits.py's round-robin over (label, claim language,
booklet language), seed 42; their task A lines are copied from output/devA (cases and expected labels,
unchanged) to the git-ignored --out folder, with rows.json listing the rows.
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

SEED = 42


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--size", type=int, default=100)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    splits = json.loads((ROOT / "data" / "splits.json").read_text(encoding="utf-8"))
    df = pd.read_parquet(RAW).drop_duplicates()
    sample = balanced_sample(df.loc[splits["dev_rows"]], args.size, random.Random(SEED))
    rows = {int(i) for i in sample.index}
    args.out.mkdir(parents=True, exist_ok=True)
    for name in ("cases.jsonl", "expected-labels.jsonl"):
        lines = (ROOT / "output" / "devA" / name).read_text(encoding="utf-8").splitlines()
        kept = [line for line in lines if row_of(json.loads(line)["id"]) in rows]
        assert len(kept) == len(rows), (name, len(kept), len(rows))
        (args.out / name).write_text("\n".join(kept) + "\n", encoding="utf-8")
    (args.out / "rows.json").write_text(json.dumps({"seed": SEED, "rows": sorted(rows)}) + "\n", encoding="utf-8")
    print(f"{args.out}: {len(rows)} task A cases")


if __name__ == "__main__":
    main()
