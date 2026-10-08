"""Run two pipeline configurations on the same cases, back to back, for a fair comparison.

Run from track_2a/:

    python3 scripts/paired_run.py --cases CASES.jsonl --data-dir DIR --out-dir OUT \\
        --arm '{"name": "fulldoc-prompt"}' --arm '{"name": "fulldoc-schema", "schema_a": true, "max_tokens_a": 128}'

Each arm is a JSON object: "name" plus any fields of src.cli.Settings.
For every case both arms run one after the other, and the order alternates
(even cases: first arm first; odd cases: second arm first), so endpoint drift
over time and prompt-prefix caching affect both arms equally.

Before timing starts, every booklet referenced by the cases is parsed once
(warm cache), so neither arm's times include PDF parsing.

Output per arm: OUT/<name>/predictions.jsonl and raw_answers.jsonl, appended
after every case (a stopped run keeps its finished cases), and run.log.
Calls the same code as the official entrypoint (src.cli.predict).
"""

import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import cli, env, parse  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cases", type=Path, required=True)
    p.add_argument("--data-dir", type=Path, required=True, help="folder that booklet paths are relative to")
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--arm", action="append", required=True, help="JSON settings; give exactly two")
    args = p.parse_args()
    if len(args.arm) != 2:
        p.error("give exactly two --arm options")
    arms = [json.loads(a) for a in args.arm]
    names = [a.pop("name") for a in arms]
    settings = [cli.Settings(**a) for a in arms]

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    env.load_env_file()
    cases = [json.loads(line) for line in args.cases.read_text(encoding="utf-8").splitlines() if line.strip()]

    booklets = sorted({c["booklet"]["path"] for c in cases if "booklet" in c})
    for b in booklets:  # warm the cache: parsing time stays out of the comparison
        if (args.data_dir / b).is_file():
            parse.load_pages(args.data_dir / b)
    print(f"{len(cases)} cases, {len(booklets)} booklets parsed; arms: {names}", flush=True)

    out = {}
    for name, s in zip(names, settings):
        d = args.out_dir / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "settings.json").write_text(json.dumps({"name": name, **vars(s)}, indent=1) + "\n", encoding="utf-8")
        out[name] = (open(d / "predictions.jsonl", "w", encoding="utf-8"),
                     open(d / "raw_answers.jsonl", "w", encoding="utf-8"), Counter())

    for i, case in enumerate(cases):
        order = [0, 1] if i % 2 == 0 else [1, 0]
        line = []
        for k in order:
            name, s = names[k], settings[k]
            try:
                resp, status, raw = cli.predict(case, args.data_dir, s)
            except Exception as e:  # same guarantee as the CLI: never drop a case
                resp, status, raw = cli.response(case["id"], cli.FALLBACK_LABEL), f"unexpected error ({type(e).__name__})", {"id": case["id"]}
            raw["order"] = order.index(k) + 1
            preds, raws, counts = out[name]
            preds.write(json.dumps(resp, ensure_ascii=False) + "\n")
            raws.write(json.dumps(raw, ensure_ascii=False) + "\n")
            preds.flush()
            raws.flush()
            counts[status] += 1
            line.append(f"{name}: {resp['label_name']}{'' if status == 'ok' else ' (' + status + ')'}")
        print(f"[{i + 1}/{len(cases)}] {case['id']} | " + " | ".join(line), flush=True)

    for name in names:
        preds, raws, counts = out[name]
        preds.close()
        raws.close()
        summary = ", ".join(f"{k}: {v}" for k, v in counts.most_common())
        (args.out_dir / name / "run.log").write_text(summary + "\n", encoding="utf-8")
        print(f"{name}: {summary}", flush=True)


if __name__ == "__main__":
    main()
