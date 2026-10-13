"""Replay table for an arm with Apertus in a parsing role (session 11, step 3: local time of AP-all). No model calls.

Run from track_2a/ after the arm's run (scripts/paired_run.py saved every answer, the parsing calls' too):

    EMBED_MODEL_DIR=models/multilingual-e5-small python3 scripts/ap_replay_table.py \\
        --run docs/runs/<run>/AP-all --cases output/devA/cases.jsonl --data-dir output/data_dev \\
        --ap-part-a all --ap-structure-a all --fallback-a vw+bw [--base <replay table>] --out <table.json>

The pipeline's own code (src.cli.prepare and complete, with the arm's settings from the CLI arguments) builds every
request the container would send, in this process; instead of sending it, the request's hash
(scripts/stub_llm.request_hash, as the fake model computes it) is stored with the answer the arm got: for a claim
call the case's AP-part answer, for a contents call the booklet's AP-structure answer, else the case's answer. The
table then lets scripts/local_time.py replay the arm through the image (--replay), so the container takes the same
path as in the run and its local time can be measured. As in scripts/prompt_snapshot.py, .env is not read and the
model name is the pipeline's default.
"""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

for name in ("BASE_URL", "API_KEY", "MODEL", "LLM_BASE_URL", "LLM_API_KEY", "LLM_NAME", "LLM_MIN_INTERVAL"):
    os.environ.pop(name, None)
os.environ.update(BASE_URL="http://127.0.0.1:9/v1", API_KEY="stub")

import stub_llm  # noqa: E402
from src import ap_parse, cli, env, llm  # noqa: E402

env.load_env_file = lambda *a, **k: None


class Answer:
    """Just enough of a requests.Response for src/llm.py."""

    def __init__(self, text):
        self.status_code, self.headers, self.text = 200, {}, ""
        self._body = {"choices": [{"message": {"content": text}}], "usage": {"prompt_tokens": 0, "completion_tokens": 0}}

    def json(self):
        return self._body


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True, help="the arm's folder (raw_answers.jsonl)")
    ap.add_argument("--cases", type=Path, required=True)
    ap.add_argument("--data-dir", type=Path, required=True)
    ap.add_argument("--ap-part-a", default="off", choices=cli.AP_PART_MODES)
    ap.add_argument("--ap-structure-a", default="off", choices=cli.AP_STRUCTURE_MODES)
    ap.add_argument("--fallback-a", default="embed", choices=cli.FALLBACK_LEVELS)
    ap.add_argument("--base", type=Path, help="a replay table to add to (e.g. the session's G1/G2 reference)")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    raw = {}
    for line in (args.run / "raw_answers.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            raw[r["id"]] = r
    cases = [json.loads(line) for line in args.cases.read_text(encoding="utf-8").splitlines() if line.strip()]
    structure_answer = {}  # booklet path -> the contents call's answer (saved with the booklet's first case)
    for case in cases:
        for call in (raw.get(case["id"]) or {}).get("ap_calls", []):
            if call.get("version") == ap_parse.STRUCTURE_VERSION and "answer" in call:
                structure_answer.setdefault(case["booklet"]["path"], call["answer"])

    table = json.loads(args.base.read_text(encoding="utf-8")) if args.base else {}
    current, missing = {}, []

    def fake_post(base, payload, headers, counts):
        counts["attempts"] += 1
        schema = ((payload.get("response_format") or {}).get("json_schema") or {}).get("schema")
        r = raw.get(current["id"]) or {}
        if schema == ap_parse.CLAIM_SCHEMA:
            calls = [c for c in r.get("ap_calls", []) if c.get("version") == ap_parse.CLAIM_VERSION]
            text = calls[0].get("answer") if calls else None
        elif schema == ap_parse.STRUCTURE_SCHEMA:
            text = structure_answer.get(current["path"])
        else:
            text = r.get("answer")
        if text is None:
            missing.append(current["id"])
            text = ""
        table[stub_llm.request_hash(payload)] = text
        return Answer(text)

    llm._post = fake_post
    settings = cli.Settings(ap_part_a=args.ap_part_a, ap_structure_a=args.ap_structure_a, fallback_a=args.fallback_a)
    for case in cases:
        current.update(id=case["id"], path=case["booklet"]["path"])
        cli.complete(cli.prepare(case, str(args.data_dir), settings), settings)
    args.out.write_text(json.dumps(table, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(table)} requests in the table; {len(missing)} requests without a saved answer: {missing[:10]}")


if __name__ == "__main__":
    main()
