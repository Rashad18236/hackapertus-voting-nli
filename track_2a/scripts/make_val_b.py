"""Task B cases for the 580 val rows (session 9, phase C confirmation). Changes no split.

Run from track_2a/:

    python3 scripts/make_val_b.py --starter-cases DIR --out output/valB

DIR holds cases.jsonl and expected-labels.jsonl written by the starter's prepare_cases.py for all rows (as for
scripts/make_val.py). The task B lines of the rows in data/val/rows.json ("val_rows") are copied unchanged.
The output goes to a git-ignored folder; data/val/ stays as session 7 froze it.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from make_splits import row_of  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--starter-cases", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    rows = set(json.loads((ROOT / "data" / "val" / "rows.json").read_text(encoding="utf-8"))["val_rows"])
    args.out.mkdir(parents=True, exist_ok=True)
    for name in ("cases.jsonl", "expected-labels.jsonl"):
        lines = (args.starter_cases / name).read_text(encoding="utf-8").splitlines()
        kept = [line for line in lines if json.loads(line)["id"].endswith("-B") and row_of(json.loads(line)["id"]) in rows]
        assert len(kept) == len(rows), (name, len(kept), len(rows))
        (args.out / name).write_text("\n".join(kept) + "\n", encoding="utf-8")
    print(f"{args.out}: {len(rows)} task B cases")


if __name__ == "__main__":
    main()
