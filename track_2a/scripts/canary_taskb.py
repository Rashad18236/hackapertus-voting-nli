"""Task B canary: has the endpoint changed? (task B cheap-fixes stage)

Run from track_2a/:

    python3 scripts/canary_taskb.py --make --from-run docs/runs/<v3 run>   # once: fix the ids, store the answers
    python3 scripts/canary_taskb.py --out docs/runs/<next run>/canary.txt  # before each run

30 dev task B case ids (10 per gold label, seed 42) and the answer text that
v3-topic-first gave for them in the baseline run are stored in
docs/canary_taskb.json. Each check re-sends exactly the baseline request for
those cases (prompt v3-topic-first, max_tokens 32, no response_format,
temperature 0) through src/llm.py and compares the answer texts character for
character. Exit code 1 and "ENDPOINT CHANGED" if any text differs or a call
fails: then no run may start (Rashad's rule). The calls are real model calls
(about 30 x 2,000 input tokens).
"""

import argparse
import datetime
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import env, llm, nli  # noqa: E402

CANARY = ROOT / "docs" / "canary_taskb.json"
CASES = ROOT / "output" / "devB"
PROMPT, MAX_TOKENS, PER_LABEL, SEED = "v3-topic-first", 32, 10, 42


def load(path):
    return {json.loads(l)["id"]: json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()}


def make(run):
    gold = load(CASES / "expected-labels.jsonl")
    raws = load(run / "raw_answers.jsonl")
    rng = random.Random(SEED)
    ids = []
    for label in (0, 1, 2):
        pool = sorted(i for i, g in gold.items() if g["label"] == label and "answer" in raws[i])
        ids += sorted(rng.sample(pool, PER_LABEL))
    CANARY.write_text(json.dumps({
        "source_run": run.as_posix(), "prompt_version": PROMPT, "max_tokens": MAX_TOKENS, "response_format": None,
        "seed": SEED, "answers": {i: raws[i]["answer"] for i in ids}}, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"{len(ids)} canary cases stored in {CANARY.relative_to(ROOT)}")


def check(out):
    canary = json.loads(CANARY.read_text(encoding="utf-8"))
    cases = load(CASES / "cases.jsonl")
    env.load_env_file()
    lines, changed = [f"canary check {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M:%S} UTC, "
                      f"{len(canary['answers'])} cases, baseline {canary['source_run']}"], []
    for case_id, expected in canary["answers"].items():
        case = cases[case_id]
        try:
            result = llm.chat(nli.build_messages_b(case["reference"]["text"], case["claim"]["text"], PROMPT),
                              max_tokens=MAX_TOKENS)
            answer = result.text
        except llm.LLMError as e:
            answer = f"<call failed: {str(e)[:80]}>"
        if answer != expected:
            changed.append(case_id)
            lines.append(f"DIFFERS {case_id}: expected {expected[:60]!r}, got {answer[:60]!r}")
    lines.append("ENDPOINT CHANGED: do not run" if changed else
                 f"OK: all {len(canary['answers'])} answer texts identical to the baseline")
    text = "\n".join(lines) + "\n"
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(text, encoding="utf-8")
    print(text, end="")
    return 1 if changed else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--make", action="store_true")
    ap.add_argument("--from-run", type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    if args.make:
        make(args.from_run)
        return 0
    return check(args.out)


if __name__ == "__main__":
    sys.exit(main())
