"""Time and peak memory of the local steps of task A, per booklet, without any model call.

Run from track_2a/ (booklets from scripts/fetch_dev_booklets.py; e5 model files as in the Dockerfile):

    EMBED_MODEL_DIR=models/multilingual-e5-small python3 scripts/speed_memory.py \\
        --booklets output/booklets_dev --cases data/dev/cases.jsonl --out <file>.json

Inside the image (scripts/ and the data mounted read-only, limits as asked):

    docker run --rm --cpus 2 --memory 4g --read-only --tmpfs /tmp -v "$PWD/scripts:/app/scripts:ro" \\
        -v "$PWD/output/booklets_dev:/data/booklets:ro" -v "$PWD/data/dev/cases.jsonl:/data/cases.jsonl:ro" \\
        -v "$PWD/output:/output" --entrypoint python hackapertus-voting-nli scripts/speed_memory.py \\
        --booklets /data/booklets --cases /data/cases.jsonl --out /output/speed_container.json

Each booklet runs in a fresh Python process (so peak memory is per booklet and every step starts
cold), with an empty booklet cache. Steps, in this order:

  import      importing the pipeline's modules (src.cli and what it imports)
  pdf         src/parse.py: the PDF to page texts, no cache (then the cached read, "pdf_cached")
  sections    src/booklet.py: parse() once
  model_load  loading multilingual-e5-small (onnxruntime session and tokenizer)
  route       section-route's route() for each dev task A case on this booklet: claim router, booklet
              parse, vote match, and the e5 ranking of a long part's paragraphs (as src/cli.py does)
  embed       embed-e5-small's select_chunks() for each case: the first case embeds the whole booklet,
              later cases embed only the claim

Peak memory is the process's maximum resident set size (ru_maxrss) after each step.
"""

import argparse
import json
import os
import resource
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def peak_mb():
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)


def one(pdf, cases_file):
    """Measure one booklet in this process; returns a dict."""
    t0 = time.perf_counter()
    sys.path.insert(0, str(ROOT))
    from src import booklet, cli, parse  # noqa: F401  (cli: import cost of the entrypoint)
    from src.contexts import embed_e5_small, section_route
    out = {"booklet": pdf.name, "seconds": {}, "peak_mb": {}}
    sec, mem = out["seconds"], out["peak_mb"]
    sec["import"], mem["import"] = round(time.perf_counter() - t0, 3), peak_mb()

    cases = [json.loads(line) for line in Path(cases_file).read_text(encoding="utf-8").splitlines() if line.strip()]
    mine = [c for c in cases if "booklet" in c and Path(c["booklet"]["path"]).name == pdf.name]
    out["cases"] = len(mine)
    with tempfile.TemporaryDirectory() as cache:
        t = time.perf_counter()
        pages = parse.load_pages(pdf, cache_dir=cache)
        sec["pdf"], mem["pdf"] = round(time.perf_counter() - t, 3), peak_mb()
        t = time.perf_counter()
        parse.load_pages(pdf, cache_dir=cache)
        sec["pdf_cached"] = round(time.perf_counter() - t, 3)
    out["pages"], out["characters"] = len(pages), sum(len(x) for x in pages.values())

    t = time.perf_counter()
    booklet.parse(pages)
    sec["sections"], mem["sections"] = round(time.perf_counter() - t, 3), peak_mb()

    t = time.perf_counter()
    embed_e5_small._get_embedder()
    sec["model_load"], mem["model_load"] = round(time.perf_counter() - t, 3), peak_mb()

    route_times, routed = [], 0
    for case in mine:
        t = time.perf_counter()
        result = section_route.route(pages, case["vote"], case["claim"]["text"])
        route_times.append((round(time.perf_counter() - t, 3), case["id"]))
        routed += result is not None
    out["routed"] = routed
    sec["route_total"], mem["route"] = round(sum(x for x, _ in route_times), 3), peak_mb()
    sec["route_max"] = max(route_times)[0] if route_times else 0
    out["route_slowest_case"] = max(route_times)[1] if route_times else None

    embed_times = []
    for case in mine:
        t = time.perf_counter()
        embed_e5_small.select_chunks(pages, case["claim"]["text"])
        embed_times.append((round(time.perf_counter() - t, 3), case["id"]))
    sec["embed_first"] = embed_times[0][0] if embed_times else 0
    sec["embed_rest_mean"] = (round(sum(x for x, _ in embed_times[1:]) / (len(embed_times) - 1), 3)
                              if len(embed_times) > 1 else None)
    mem["embed"] = peak_mb()
    out["chunks"] = len(embed_e5_small.chunk_pages(pages))
    out["seconds_total"] = round(time.perf_counter() - t0, 3)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--booklets", type=Path, required=True)
    ap.add_argument("--cases", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--one", type=Path, help="internal: measure this booklet in this process and print JSON")
    args = ap.parse_args()
    if args.one:
        print(json.dumps(one(args.one, args.cases)))
        return
    cases = [json.loads(line) for line in args.cases.read_text(encoding="utf-8").splitlines() if line.strip()]
    names = sorted({Path(c["booklet"]["path"]).name for c in cases if "booklet" in c})
    results = []
    for name in names:
        t = time.perf_counter()
        done = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--one", str(args.booklets / name),
                               "--booklets", str(args.booklets), "--cases", str(args.cases)],
                              capture_output=True, text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        if done.returncode != 0:
            results.append({"booklet": name, "error": done.stderr[-500:]})
            continue
        r = json.loads(done.stdout.strip().splitlines()[-1])
        r["process_seconds"] = round(time.perf_counter() - t, 3)  # interpreter start included
        results.append(r)
        print(f"{name}: {r['pages']} pages, pdf {r['seconds']['pdf']} s, sections {r['seconds']['sections']} s, "
              f"model {r['seconds']['model_load']} s, route {r['seconds']['route_total']} s ({r['cases']} cases), "
              f"embed first {r['seconds']['embed_first']} s, peak {r['peak_mb']['embed']} MB", flush=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
