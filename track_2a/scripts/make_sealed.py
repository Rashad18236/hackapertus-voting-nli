"""The sealed set (session 16, the final session): the cases of the test rows dated 2020-02-09, 2022-02-13 and
2022-05-15, copied once for the one run through the submission image.

Run from track_2a/:  python3 scripts/make_sealed.py [--fetch DIR]

The same method as data/probe/ (scripts/make_probe.py, whose functions are reused): only the lines of
data/test/cases.jsonl that name a sealed date's booklet are parsed; the task B lines and expected labels of exactly
these rows are picked by their id text. Writes data/sealed/cases.jsonl and data/sealed/expected-labels.jsonl (copies;
data/test/ is never changed). With --fetch DIR, downloads the three dates' booklets (the dataset's booklet_url column)
into DIR, which must lie outside the repository: no booklet PDF or text is committed.
"""

import argparse
import json
import sys
from pathlib import Path

import make_probe as mp

ROOT = Path(__file__).resolve().parent.parent
SEALED_DATES = mp.SEALED_DATES
OUT = ROOT / "data" / "sealed"


def fetch(cases, folder):
    import pandas as pd
    import requests
    folder = Path(folder).resolve()
    if ROOT.parent in folder.parents or folder == ROOT.parent:
        sys.exit(f"refusing a folder inside the repository: {folder}")
    names = {Path(json.loads(line)["booklet"]["path"]).name for line in cases if '"booklet"' in line}
    df = pd.read_parquet(ROOT / "data" / "raw" / "v1.1.parquet",
                         columns=["booklet_publish_date", "reference_language", "booklet_url"]).drop_duplicates()
    urls = {f"{str(date)[:10].replace('-', '_')}_{lang}.pdf": url
            for date, lang, url in df.itertuples(index=False) if str(date)[:10] in SEALED_DATES}
    folder.mkdir(parents=True, exist_ok=True)
    for name in sorted(names):
        target = folder / name
        if target.exists():
            continue
        response = requests.get(urls[name], timeout=120)
        response.raise_for_status()
        target.write_bytes(response.content)
        print(f"{name}: {len(response.content) // 1024} KB")
    print(f"{len(names)} booklets in {folder}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fetch", metavar="DIR", help="also download the sealed booklets into DIR (outside the repository)")
    args = ap.parse_args()
    test = ROOT / "data" / "test"
    case_lines = [line for line in (test / "cases.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    markers = [f'booklets/{d.replace("-", "_")}_' for d in SEALED_DATES]
    rows = set()
    for line in case_lines:  # only lines naming a sealed booklet are parsed (make_probe.probe_rows' rule)
        if any(m in line for m in markers):
            case = json.loads(line)
            assert any(m in case["booklet"]["path"] for m in markers)
            rows.add(int(case["id"].split("-")[2]))
    cases = mp.lines_of_rows(case_lines, rows)
    labels = mp.lines_of_rows((test / "expected-labels.jsonl").read_text(encoding="utf-8").splitlines(), rows)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cases.jsonl").write_text("".join(line + "\n" for line in cases), encoding="utf-8")
    (OUT / "expected-labels.jsonl").write_text("".join(line + "\n" for line in labels), encoding="utf-8")
    n_a = sum('"booklet"' in line for line in cases)
    print(f"{len(rows)} sealed rows: {n_a} task A and {len(cases) - n_a} task B cases, {len(labels)} expected labels")
    if args.fetch:
        fetch(cases, args.fetch)


if __name__ == "__main__":
    main()
