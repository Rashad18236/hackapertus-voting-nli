"""Local time per case of the Docker image, as the organisers count it (session 10, step 1). No model calls.

Run from track_2a/ (Docker running, image built):

    python3 scripts/local_time.py --image hackapertus-voting-nli --cases output/devA/cases.jsonl \\
        --booklets output/booklets_dev --delay 1.0 --out <folder> \\
        [--replay docs/runs/2026-10-12_rashad_prompt-snapshot-final-s10_devAB-valA/replay_table.json]

The organisers' rule (docs/official_scoring.md): local time = the wall-clock time of the container run minus
the time during which at least one model request is in flight. This script measures exactly that against
the fake model (scripts/stub_llm.py), started in this process on 127.0.0.1:

1. The fake model answers every request after --delay seconds (a stand-in for the real model's latency).
   With --replay it returns the saved real answer for a known request (so the run follows the same path
   as the real one, second calls included); an unknown request gets the fake model's fixed answer and is
   counted as a replay miss.
2. The image runs with the organisers' command (`--input /data/cases.jsonl --output /output/predictions.jsonl`),
   a read-only root, /tmp as tmpfs, the data read-only, on the host network (to reach the fake model),
   limited to --cpus CPUs and --memory memory (defaults 2 and 4g, as session 8's speed check).
3. Wall-clock = from just before `docker run` starts to just after it exits. The fake model logs when each
   request arrived and when its answer was written; their union is the time "in flight".

Writes <folder>/local_time.json (the numbers below), predictions.jsonl, calls.jsonl (the fake model's log)
and stderr.log (the CLI's log), and prints a summary:

    wall_s                 container run, start to exit
    in_flight_s            union of the request intervals
    local_s                wall_s - in_flight_s;  local_per_case_s = local_s / cases
    to_first_request_s     start of the run to the first request (container start, imports, first case)
    gaps_s                 sum of the gaps between requests (the local work of every later case)
    tail_s                 last answer to the end of the run (writing, exit, container removal)

Never mount expected labels. Nothing leaves the machine.
"""

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import stub_llm  # noqa: E402

REPLAY_DEFAULT = ROOT / "docs/runs/2026-10-12_rashad_prompt-snapshot-final-s10_devAB-valA/replay_table.json"


def union_length(intervals, lo, hi):
    """Total length of the union of [start, end] intervals, clipped to [lo, hi]."""
    total, cur_start, cur_end = 0.0, None, None
    for start, end in sorted((max(lo, s), min(hi, e)) for s, e in intervals):
        if end <= start:
            continue
        if cur_end is None or start > cur_end:
            if cur_end is not None:
                total += cur_end - cur_start
            cur_start, cur_end = start, end
        else:
            cur_end = max(cur_end, end)
    if cur_end is not None:
        total += cur_end - cur_start
    return total


def gaps(intervals):
    """The idle stretches between consecutive requests (none in flight), in order."""
    out, cur_end = [], None
    for start, end in sorted(intervals):
        if cur_end is not None and start > cur_end:
            out.append(start - cur_end)
        cur_end = end if cur_end is None else max(cur_end, end)
    return out


def summarise(wall_start, wall_end, intervals, n_cases):
    wall = wall_end - wall_start
    in_flight = union_length(intervals, wall_start, wall_end)
    local = wall - in_flight
    gap_list = gaps(intervals)
    out = {"cases": n_cases, "requests": len(intervals), "wall_s": round(wall, 3), "in_flight_s": round(in_flight, 3),
           "local_s": round(local, 3), "local_per_case_s": round(local / n_cases, 4) if n_cases else None}
    if intervals:
        out["to_first_request_s"] = round(min(s for s, _ in intervals) - wall_start, 3)
        out["tail_s"] = round(wall_end - max(e for _, e in intervals), 3)
        out["gaps_s"] = round(sum(gap_list), 3)
        out["gap_count"] = len(gap_list)
        if gap_list:
            ordered = sorted(gap_list)
            out["gap_median_s"] = round(statistics.median(ordered), 4)
            out["gap_p95_s"] = round(ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))], 4)
            out["gap_max_s"] = round(ordered[-1], 3)
        out["max_in_flight"] = max_concurrency(intervals)
    return out


def max_concurrency(intervals):
    events = sorted([(s, 1) for s, _ in intervals] + [(e, -1) for _, e in intervals], key=lambda x: (x[0], x[1]))
    cur = best = 0
    for _, step in events:
        cur += step
        best = max(best, cur)
    return best


def docker_command(args, base_url, out_dir):
    cases = Path(args.cases).resolve()
    cmd = ["docker", "run", "--rm", "--platform", "linux/amd64", "--network", "host",
           "--cpus", str(args.cpus), "--memory", args.memory, "--memory-swap", args.memory,
           "--read-only", "--tmpfs", "/tmp", "--user", f"{os.getuid()}:{os.getgid()}",
           "-e", f"BASE_URL={base_url}", "-e", "API_KEY=stub",
           "-v", f"{cases}:/data/cases.jsonl:ro"]
    if args.booklets:
        cmd += ["-v", f"{Path(args.booklets).resolve()}:/data/booklets:ro"]
    if args.src:
        cmd += ["-v", f"{Path(args.src).resolve()}:/app/src:ro"]
    if args.models:  # session 11: e.g. the folder with e5's 8-bit export next to model.onnx
        cmd += ["-v", f"{Path(args.models).resolve()}:/app/models/multilingual-e5-small:ro"]
    for item in args.env:  # session 11: e.g. PROFILE_PHASES=1 (src/timing.py)
        cmd += ["-e", item]
    cmd += ["-v", f"{out_dir}:/output"]
    cli = ["--input", "/data/cases.jsonl", "--output", "/output/predictions.jsonl"] + args.cli_args
    if args.peak_memory:  # the CLI under sh, which then copies the container's peak memory (cgroup v1) to /output
        return cmd + ["--entrypoint", "sh", args.image, "-c",
                      'python -m src.cli "$@"; code=$?; cat /sys/fs/cgroup/memory/memory.max_usage_in_bytes '
                      '> /output/peak_memory_bytes 2>/dev/null; exit $code', "sh"] + cli
    return cmd + [args.image] + cli


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--image", required=True)
    ap.add_argument("--cases", required=True)
    ap.add_argument("--booklets", help="folder mounted as /data/booklets (task A)")
    ap.add_argument("--replay", default=str(REPLAY_DEFAULT), help="request hash -> saved answer (prompt_snapshot)")
    ap.add_argument("--delay", type=float, default=1.0, help="seconds the fake model takes per answer")
    ap.add_argument("--cpus", default="2")
    ap.add_argument("--memory", default="4g")
    ap.add_argument("--src", help="mount this folder over the image's /app/src (measure working-tree code)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--models", help="mount this folder over the image's e5 folder (session 11)")
    ap.add_argument("--env", action="append", default=[], help="KEY=VALUE for the container (session 11)")
    ap.add_argument("--peak-memory", action="store_true",
                    help="also record the container's peak memory (cgroup v1; the CLI then runs under sh)")
    ap.add_argument("cli_args", nargs="*", help="extra arguments for the CLI, after --")
    args = ap.parse_args()

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    n_cases = sum(1 for line in Path(args.cases).read_text(encoding="utf-8").splitlines() if line.strip())
    replay = json.loads(Path(args.replay).read_text(encoding="utf-8")) if args.replay else None
    server, base_url = stub_llm.start(host="127.0.0.1", port=0, replay=replay, delay=args.delay)
    cmd = docker_command(args, base_url, out_dir)
    try:
        with open(out_dir / "stderr.log", "w", encoding="utf-8") as log:
            wall_start = time.time()
            code = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT).returncode
            wall_end = time.time()
    finally:
        server.shutdown()
    calls = list(server.config.calls)
    intervals = [(c["t_start"], c["t_end"]) for c in calls if "t_start" in c]
    result = summarise(wall_start, wall_end, intervals, n_cases)
    kinds = {}
    for c in calls:
        kinds[c.get("kind", "?")] = kinds.get(c.get("kind", "?"), 0) + 1
    predictions = [json.loads(line) for line in (out_dir / "predictions.jsonl").read_text(encoding="utf-8").splitlines()
                   if line.strip()] if (out_dir / "predictions.jsonl").exists() else []
    tokens_in = sum(p.get("metrics", {}).get("input_tokens", 0) for p in predictions)
    tokens_out = sum(p.get("metrics", {}).get("output_tokens", 0) for p in predictions)
    result.update({
        "exit_code": code, "image": args.image, "image_id": image_id(args.image), "cases_file": args.cases,
        "delay_s": args.delay, "cpus": args.cpus, "memory": args.memory, "cli_args": args.cli_args,
        "src_mounted": bool(args.src), "responses": len(predictions),
        "unique_ids": len({p.get("id") for p in predictions}), "answer_kinds": kinds,
        "replay_misses": kinds.get("ok", 0),
        "input_tokens_per_case": round(tokens_in / n_cases, 1) if n_cases else None,
        "output_tokens_per_case": round(tokens_out / n_cases, 1) if n_cases else None,
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(wall_start)),
    })
    if args.peak_memory and (out_dir / "peak_memory_bytes").exists():
        result["peak_memory_mib"] = round(int((out_dir / "peak_memory_bytes").read_text().strip()) / 2**20)
    phases = [json.loads(line[7:]) for line in (out_dir / "stderr.log").read_text(encoding="utf-8").splitlines()
              if line.startswith("PHASES ")] if (out_dir / "stderr.log").exists() else []
    if phases:  # session 11, step 4a: src/timing.py's per-process totals (PROFILE_PHASES=1)
        result["phases"] = phases
        totals = {}
        for ph in phases:
            for k, v in ph["seconds"].items():
                totals[k] = round(totals.get(k, 0) + v, 3)
        result["phase_totals_s"] = totals
    with open(out_dir / "calls.jsonl", "w", encoding="utf-8") as f:
        for c in calls:
            f.write(json.dumps({k: v for k, v in c.items() if k != "payload"}) + "\n")
    (out_dir / "local_time.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(f"{args.cases}: {n_cases} cases, {result['requests']} requests, exit {code}, "
          f"{result['responses']} responses, replay misses {result['replay_misses']}")
    print(f"  wall {result['wall_s']} s, in flight {result['in_flight_s']} s, local {result['local_s']} s "
          f"= {result['local_per_case_s']} s per case")
    if "to_first_request_s" in result:
        print(f"  to first request {result['to_first_request_s']} s, gaps {result['gaps_s']} s "
              f"(median {result.get('gap_median_s')} s, p95 {result.get('gap_p95_s')} s, max {result.get('gap_max_s')} s), "
              f"tail {result['tail_s']} s")
    return code


def image_id(image):
    try:
        return subprocess.run(["docker", "image", "inspect", image, "--format", "{{.Id}}"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


if __name__ == "__main__":
    sys.exit(main())
