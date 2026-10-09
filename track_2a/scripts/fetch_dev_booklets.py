"""Download the booklet PDFs that the dev cases need (never the test booklets).

Run from track_2a/:  python3 scripts/fetch_dev_booklets.py [--cases data/val/cases.jsonl]

--cases picks another case file (default data/dev/cases.jsonl); the script
refuses a case file that names a test booklet (data/splits.json).

Writes output/booklets_dev/<date>_<lang>.pdf (git-ignored), the folder that
`make run` / `make compare` mount with BOOKLETS=output/booklets_dev. The URLs
come from the dataset's booklet_url column (data/raw/v1.1.parquet); files that
are already there are skipped.
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "booklets_dev"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cases", type=Path, default=ROOT / "data" / "dev" / "cases.jsonl")
    args = ap.parse_args()
    needed = set()
    for line in args.cases.read_text(encoding="utf-8").splitlines():
        case = json.loads(line)
        if "booklet" in case:
            needed.add(Path(case["booklet"]["path"]).name)  # e.g. 2020_09_27_fr.pdf
    test_dates = json.loads((ROOT / "data" / "splits.json").read_text(encoding="utf-8"))["test_booklets"]
    test = {name for name in needed if name[:10].replace("_", "-") in test_dates}
    if test:
        sys.exit(f"Refusing test booklets: {sorted(test)}")

    df = pd.read_parquet(ROOT / "data" / "raw" / "v1.1.parquet")
    urls = {}
    for date, lang, url in df[["booklet_publish_date", "reference_language", "booklet_url"]].drop_duplicates().itertuples(index=False):
        urls[f"{str(date)[:10].replace('-', '_')}_{lang}.pdf"] = url

    OUT.mkdir(parents=True, exist_ok=True)
    missing = sorted(needed - set(urls))
    if missing:
        sys.exit(f"No URL for: {missing}")
    for name in sorted(needed):
        target = OUT / name
        if target.exists():
            continue
        response = requests.get(urls[name], timeout=120)
        response.raise_for_status()
        target.write_bytes(response.content)
        print(f"{name}: {len(response.content) // 1024} KB")
    print(f"{len(needed)} booklets for {args.cases.name} in {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
