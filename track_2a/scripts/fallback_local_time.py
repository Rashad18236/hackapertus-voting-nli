"""Local work per fallback case for each fallback level (session 11, step 2). No model calls.

Run from track_2a/ (dev booklets in output/booklets_dev; e5 in models/multilingual-e5-small):

    EMBED_MODEL_DIR=models/multilingual-e5-small python3 scripts/fallback_local_time.py \\
        --cases output/devA/cases.jsonl --data-dir output/data_dev --out <file.json>

For each level, in a fresh process (cold caches, as in a container run): every case is put into the level's
situation the way scripts/paired_run.py forces it ("no part" for today's fallback and VW, "no vote" for BW), and
src/cli.prepare() builds the request (booklet reading, parsing, selection, embedding; no model call). Reported: the
seconds of prepare() per case, in all and without the first case of each booklet (which also reads the PDF), the
model-free part of each level's local time. Booklet pages are read once before timing starts (as in paired_run), so
PDF reading is not counted; e5 loading and every embedding are.
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

LEVELS = {"today-fallback": ("no part", "embed"), "VW": ("no part", "vw"), "BW": ("no vote", "bw"),
          "today-routed": (None, "embed")}


def one_level(level, cases_file, data_dir):
    import paired_run
    from src import cli, parse
    force, fallback = LEVELS[level]
    if force:
        paired_run.install_forces()
    paired_run._force["mode"] = force
    settings = cli.Settings(fallback_a=fallback)
    cases = [json.loads(line) for line in Path(cases_file).read_text(encoding="utf-8").splitlines() if line.strip()]
    for path in sorted({c["booklet"]["path"] for c in cases}):
        parse.load_pages(Path(data_dir) / path)
    times, seen, paths = [], set(), {}
    for case in cases:
        paired_run._current["id"], paired_run._current["vote"] = case["id"], case["vote"]
        start = time.perf_counter()
        prepared = cli.prepare(case, data_dir, settings)
        seconds = time.perf_counter() - start
        first = case["booklet"]["path"] not in seen
        seen.add(case["booklet"]["path"])
        times.append((seconds, first))
        path = prepared.raw.get("route") or prepared.raw.get("fallback") or prepared.kind
        paths[path] = paths.get(path, 0) + 1
    later = [s for s, first in times if not first]
    return {"level": level, "cases": len(times), "seconds_per_case": round(sum(s for s, _ in times) / len(times), 4),
            "seconds_per_case_later_cases_of_a_booklet": round(sum(later) / len(later), 4) if later else None,
            "seconds_total": round(sum(s for s, _ in times), 1), "paths": paths}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cases", type=Path, required=True)
    ap.add_argument("--data-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--level", choices=sorted(LEVELS))
    args = ap.parse_args()
    if args.level:  # the child: one level in this fresh process
        print(json.dumps(one_level(args.level, args.cases, args.data_dir)))
        return
    results = []
    for level in LEVELS:
        out = subprocess.run([sys.executable, __file__, "--cases", str(args.cases), "--data-dir", str(args.data_dir),
                              "--out", str(args.out), "--level", level], capture_output=True, text=True, check=True)
        results.append(json.loads(out.stdout.strip().splitlines()[-1]))
        print(results[-1], flush=True)
    args.out.write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
