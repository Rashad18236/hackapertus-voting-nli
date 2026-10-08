"""Download the booklet PDFs that the dev cases need (never the test booklets).

Run from track_2a/:  python3 scripts/fetch_dev_booklets.py

Writes output/booklets_dev/<date>_<lang>.pdf (git-ignored), the folder that
`make run` / `make compare` mount with BOOKLETS=output/booklets_dev. The URLs
come from the dataset's booklet_url column (data/raw/v1.1.parquet); files that
are already there are skipped.
"""

import json
import sys
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "booklets_dev"


def main():
    needed = set()
    for line in (ROOT / "data" / "dev" / "cases.jsonl").read_text(encoding="utf-8").splitlines():
        case = json.loads(line)
        if "booklet" in case:
            needed.add(Path(case["booklet"]["path"]).name)  # e.g. 2020_09_27_fr.pdf

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
    print(f"{len(needed)} dev booklets in {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
