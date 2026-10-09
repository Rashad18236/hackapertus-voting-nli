"""Snapshot of every request the pipeline sends, and replay of saved answers (session 8, no model calls).

Run from track_2a/ (dev and val booklets in --booklets, e5 files in models/multilingual-e5-small):

    python3 scripts/prompt_snapshot.py run --out DIR [--replay TABLE.json]
    python3 scripts/prompt_snapshot.py table --snapshot DIR/snapshot.json --runs RUN_DIR [RUN_DIR ...] --out TABLE.json
    python3 scripts/prompt_snapshot.py compare --reference REF_DIR --new DIR [--allow-evidence-change]

run: the real CLI (`src.cli.main()`, default settings) answers two input files against the fake model
(scripts/stub_llm.py), each in its own process with its own fake model, at the same time:

- dev: data/dev/cases.jsonl, all 600 cases (300 task A, 300 task B);
- val: data/val/cases.jsonl, all 580 task A cases.

The developer's .env is never read (src.env.load_env_file is replaced by a no-op, as in
tests/test_contract.py), BASE_URL points to the fake model, API_KEY is the dummy "stub", and the model name
is the pipeline's default (MODEL and LLM_* are removed from the environment). Each set runs from a temporary
folder holding its cases file and a link `booklets` to --booklets, as /data does in the container.

Every model call is matched to its case: the CLI handles the cases one after another and, against the
fake model, makes exactly one call for each case whose raw answer has an "answer". The match is checked:
the request must contain the case's claim. DIR/snapshot.json then holds, per case id: the task, the set,
request_sha256 (SHA-256 of the whole request body: model, messages, max_tokens, temperature,
response_format; stub_llm.request_hash) and, for task A, the path taken: "route:<part>", "fallback:<mode>"
(with " after route error" when routing raised), or "no call: ..." when the case got no model call.
DIR/<set>/ holds the predictions, raw answers and the CLI's log; DIR/summary.json the counts.

With --replay, the fake model answers every request whose hash is in the table with the answer saved for
that case (stub_llm --replay); others get the fake model's fixed answer. The requests do not depend on the
answers, so the snapshot of a replay run is the same as without --replay.

table: {request_sha256: saved answer} from a snapshot and the raw answers of saved runs (by case id).

compare: G1, every request hash and every path equal the reference; G2, every case's label and evidence
equal the reference's (metrics ignored). Exit 1 on any difference. --allow-evidence-change lists evidence
differences without failing on them (labels must still be equal).
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import stub_llm  # noqa: E402

SETS = {"dev": ROOT / "data" / "dev" / "cases.jsonl", "val": ROOT / "data" / "val" / "cases.jsonl"}
RUNNER = ("import sys, src.env\n"
          "src.env.load_env_file = lambda *a, **k: None\n"
          "from src import cli\n"
          "sys.exit(cli.main())\n")
REMOVED = ("BASE_URL", "API_KEY", "MODEL", "LLM_BASE_URL", "LLM_API_KEY", "LLM_NAME")


def load_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def path_taken(raw):
    """The path a case took through the pipeline, from its raw answer."""
    if raw.get("task") == "B":
        return "task B"
    if "route" in raw:
        return f"route:{raw['route']}"
    if "fallback" in raw:
        return f"fallback:{raw['fallback']}" + (" after route error" if "route_error" in raw else "")
    if "answer" in raw:
        return f"context:{raw.get('context')}"
    return f"no call: {raw.get('error') or 'no model call'}"


def run(args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    replay = json.loads(Path(args.replay).read_text(encoding="utf-8")) if args.replay else None
    booklets = Path(args.booklets).resolve()
    cache = Path(args.cache).resolve()
    work = Path(tempfile.mkdtemp(prefix="prompt-snapshot-"))
    jobs = {}
    for name, cases_file in SETS.items():
        server, url = stub_llm.start(replay=replay, keep_payloads=True)
        folder = work / name
        folder.mkdir()
        (folder / "cases.jsonl").write_bytes(cases_file.read_bytes())
        (folder / "booklets").symlink_to(booklets, target_is_directory=True)
        (out / name).mkdir(exist_ok=True)
        environment = {k: v for k, v in os.environ.items() if k not in REMOVED}
        environment.update({"BASE_URL": url, "API_KEY": "stub", "BOOKLET_CACHE_DIR": str(cache),
                            "EMBED_MODEL_DIR": str(ROOT / "models" / "multilingual-e5-small")})
        log = open(out / name / "cli.log", "w", encoding="utf-8")
        proc = subprocess.Popen([sys.executable, "-c", RUNNER, "--input", str(folder / "cases.jsonl"),
                                 "--output", str(out / name / "predictions.jsonl"),
                                 "--raw", str(out / name / "raw_answers.jsonl"), *args.cli_arg],
                                cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT)
        jobs[name] = (server, proc, log, time.time())

    snapshot, summary, problems = {}, {}, []
    for name, (server, proc, log, started) in jobs.items():
        code = proc.wait()
        seconds = round(time.time() - started, 1)
        log.close()
        server.shutdown()
        calls = server.config.calls
        cases = {c["id"]: c for c in load_jsonl(SETS[name])}
        raws = load_jsonl(out / name / "raw_answers.jsonl")
        called = [r for r in raws if "answer" in r]
        if code != 0:
            problems.append(f"{name}: CLI exit code {code}")
        if len(called) != len(calls):
            problems.append(f"{name}: {len(called)} cases with an answer but {len(calls)} model calls")
        for raw, call in zip(called, calls):
            claim = cases[raw["id"]]["claim"]["text"]
            if claim not in json.dumps(call["payload"]["messages"], ensure_ascii=False) and \
                    claim not in "".join(m.get("content", "") for m in call["payload"]["messages"]):
                problems.append(f"{name}: call {call['number']} does not contain the claim of {raw['id']}")
        hashes = {raw["id"]: call["request_sha256"] for raw, call in zip(called, calls)}
        for raw in raws:
            snapshot[raw["id"]] = {"task": raw.get("task"), "set": name, "request_sha256": hashes.get(raw["id"]),
                                   "path": path_taken(raw)}
        missing = sorted(set(cases) - {r["id"] for r in raws})
        if missing:
            problems.append(f"{name}: no raw answer for {len(missing)} cases, e.g. {missing[:3]}")
        summary[name] = {"cases": len(cases), "raw_answers": len(raws), "model_calls": len(calls),
                         "replayed": sum(1 for c in calls if c["kind"] == "replay"),
                         "fixed_answer": sum(1 for c in calls if c["kind"] == "ok"),
                         "paths": dict(Counter(snapshot[r["id"]]["path"] for r in raws).most_common()),
                         "seconds": seconds, "exit_code": code}
    (out / "snapshot.json").write_text(json.dumps(dict(sorted(snapshot.items())), indent=1, ensure_ascii=False) + "\n",
                                       encoding="utf-8")
    summary["problems"] = problems
    summary["replay_table"] = args.replay
    summary["cli_args"] = args.cli_arg
    (out / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    return 1 if problems else 0


def table(args):
    snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    answers, table_, clashes = {}, {}, []
    for run_dir in args.runs:
        for raw in load_jsonl(Path(run_dir) / "raw_answers.jsonl"):
            if "answer" in raw:
                answers[raw["id"]] = raw["answer"]
    for case_id, answer in sorted(answers.items()):
        entry = snapshot.get(case_id)
        if not entry or not entry["request_sha256"]:
            continue
        key = entry["request_sha256"]
        if key in table_ and table_[key] != answer:
            clashes.append(case_id)  # the same request was answered differently in the saved runs; first kept
            continue
        table_.setdefault(key, answer)
    Path(args.out).write_text(json.dumps(table_, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(table_)} requests with a saved answer ({len(answers)} saved answers; "
          f"{len(clashes)} identical requests with a different saved answer, first kept: {clashes})")
    return 0


def compare(args):
    ref, new = Path(args.reference), Path(args.new)
    s_ref = json.loads((ref / "snapshot.json").read_text(encoding="utf-8"))
    s_new = json.loads((new / "snapshot.json").read_text(encoding="utf-8"))
    g1 = [f"{i}: {s_ref.get(i)} -> {s_new.get(i)}" for i in sorted(set(s_ref) | set(s_new))
          if (s_ref.get(i) or {}).get("request_sha256") != (s_new.get(i) or {}).get("request_sha256")
          or (s_ref.get(i) or {}).get("path") != (s_new.get(i) or {}).get("path")]
    labels, evidence = [], []
    for name in SETS:
        p_ref = {p["id"]: p for p in load_jsonl(ref / name / "predictions.jsonl")}
        p_new = {p["id"]: p for p in load_jsonl(new / name / "predictions.jsonl")}
        for i in sorted(set(p_ref) | set(p_new)):
            a, b = p_ref.get(i), p_new.get(i)
            if a is None or b is None or (a["label"], a["label_name"]) != (b["label"], b["label_name"]):
                labels.append(f"{i}: {a and a['label']} -> {b and b['label']}")
            elif a["evidence"] != b["evidence"]:
                evidence.append(i)
    result = {"G1_request_or_path_differs": len(g1), "G2_label_differs": len(labels),
              "G2_evidence_differs": len(evidence), "g1_examples": g1[:10], "label_examples": labels[:10],
              "evidence_cases": evidence}
    print(json.dumps(result, indent=1, ensure_ascii=False))
    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    failed = g1 or labels or (evidence and not args.allow_evidence_change)
    print("G1", "FAIL" if g1 else "pass", "| G2", "FAIL" if (labels or (evidence and not args.allow_evidence_change))
          else "pass" + (f" (evidence differs in {len(evidence)} cases, allowed)" if evidence else ""))
    return 1 if failed else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    r = sub.add_parser("run")
    r.add_argument("--out", required=True)
    r.add_argument("--replay")
    r.add_argument("--cli-arg", action="append", default=[], help="extra argument for the CLI (session 9), repeatable")
    r.add_argument("--booklets", default=str(ROOT / "output" / "booklets_dev"))
    r.add_argument("--cache", default=str(Path(tempfile.gettempdir()) / "booklet-cache-snapshot"),
                   help="parsed-PDF cache (src/parse.py); its content depends only on the PDF")
    t = sub.add_parser("table")
    t.add_argument("--snapshot", required=True)
    t.add_argument("--runs", nargs="+", required=True)
    t.add_argument("--out", required=True)
    c = sub.add_parser("compare")
    c.add_argument("--reference", required=True)
    c.add_argument("--new", required=True)
    c.add_argument("--allow-evidence-change", action="store_true")
    c.add_argument("--json")
    args = ap.parse_args()
    return {"run": run, "table": table, "compare": compare}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
