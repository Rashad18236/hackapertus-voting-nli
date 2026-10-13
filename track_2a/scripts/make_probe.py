"""The probe set (session 10, step 4): the cases of the test rows dated 2021-03-07 and 2025-09-28, copied.

Run from track_2a/:  python3 scripts/make_probe.py [--fetch]

Writes data/probe/cases.jsonl and data/probe/expected-labels.jsonl (copies; data/test/ is never changed) and,
with --fetch, downloads the two dates' booklets into output/booklets_probe/ (git-ignored).

The other three test dates (2020-02-09, 2022-02-13, 2022-05-15) are sealed: their rows are never run, parsed or
opened. So nothing here parses a line of data/test/ before knowing it belongs to a probe row:

1. A task A line names its booklet (`"path": "booklets/2021_03_07_de.pdf"`). Lines whose text contains a
   probe date's booklet path are parsed; every other line is skipped as text, unparsed.
2. Their ids give the probe rows (`v1.1-row-<n>-A`); the task B lines and expected labels of exactly these rows
   are then picked by their id text (`"id": "v1.1-row-<n>-B"`), again before any parsing.
3. The booklet URLs come from the dataset's booklet_url column (data/raw/v1.1.parquet), reading only the three
   booklet columns (date, language, URL) and keeping only the two probe dates; claims and references are not read.
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROBE_DATES = ("2021-03-07", "2025-09-28")
SEALED_DATES = ("2020-02-09", "2022-02-13", "2022-05-15")
TEST = ROOT / "data" / "test"
OUT = ROOT / "data" / "probe"
BOOKLETS = ROOT / "output" / "booklets_probe"


def probe_rows(lines):
    """Row numbers of the task A lines that name a probe date's booklet (only those lines are parsed)."""
    markers = [f'booklets/{d.replace("-", "_")}_' for d in PROBE_DATES]
    rows = set()
    for line in lines:
        if not any(m in line for m in markers):
            continue
        case = json.loads(line)
        assert any(m in case["booklet"]["path"] for m in markers)
        rows.add(int(re.fullmatch(r"v1\.1-row-(\d+)-A", case["id"]).group(1)))
    return rows


def lines_of_rows(lines, rows):
    """The lines whose id is v1.1-row-<n>-A or -B for a row n in rows, chosen by text before parsing."""
    wanted = {f'"v1.1-row-{n}-{t}"' for n in rows for t in "AB"}
    picked = []
    for line in lines:
        match = re.search(r'"id":\s*("v1\.1-row-\d+-[AB]")', line)
        if match and match.group(1) in wanted:
            picked.append(line)
    return picked


def fetch(cases):
    import pandas as pd
    import requests

    names = {Path(json.loads(line)["booklet"]["path"]).name for line in cases if '"booklet"' in line}
    df = pd.read_parquet(ROOT / "data" / "raw" / "v1.1.parquet",
                         columns=["booklet_publish_date", "reference_language", "booklet_url"]).drop_duplicates()
    urls = {f"{str(date)[:10].replace('-', '_')}_{lang}.pdf": url
            for date, lang, url in df.itertuples(index=False) if str(date)[:10] in PROBE_DATES}
    BOOKLETS.mkdir(parents=True, exist_ok=True)
    for name in sorted(names):
        if any(name.startswith(d.replace("-", "_")) for d in SEALED_DATES):
            sys.exit(f"refusing a sealed booklet: {name}")
        target = BOOKLETS / name
        if target.exists():
            continue
        response = requests.get(urls[name], timeout=120)
        response.raise_for_status()
        target.write_bytes(response.content)
        print(f"{name}: {len(response.content) // 1024} KB")
    print(f"{len(names)} booklets in {BOOKLETS.relative_to(ROOT)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fetch", action="store_true", help="also download the probe booklets")
    args = ap.parse_args()
    case_lines = [line for line in (TEST / "cases.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = probe_rows(case_lines)
    cases = lines_of_rows(case_lines, rows)
    labels = lines_of_rows((TEST / "expected-labels.jsonl").read_text(encoding="utf-8").splitlines(), rows)
    for line in cases:  # a last check, on the probe lines only
        if any(d.replace("-", "_") in line for d in SEALED_DATES):
            sys.exit("a probe line names a sealed date")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cases.jsonl").write_text("".join(line + "\n" for line in cases), encoding="utf-8")
    (OUT / "expected-labels.jsonl").write_text("".join(line + "\n" for line in labels), encoding="utf-8")
    n_a = sum('"booklet"' in line for line in cases)
    print(f"{len(rows)} probe rows: {n_a} task A and {len(cases) - n_a} task B cases, {len(labels)} expected labels")
    if args.fetch:
        fetch(cases)


if __name__ == "__main__":
    main()
