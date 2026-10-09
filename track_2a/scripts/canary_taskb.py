"""Task B canary: is the endpoint answering like it did before? It no longer blocks runs.

Run from track_2a/:

    python3 scripts/canary_taskb.py --make --from-run docs/runs/<v3 run>   # once: fix the ids, store the answers
    python3 scripts/canary_taskb.py --when "before <run>"                  # immediately before a run
    python3 scripts/canary_taskb.py --when "after <run>"                   # immediately after it

30 dev task B case ids (10 per gold label, seed 42) and the answer text that
v3-topic-first gave for them in the baseline run are stored in
docs/canary_taskb.json. Each check re-sends exactly that request for the 30
cases (prompt v3-topic-first, max_tokens 32, no response_format, temperature
0) through src/llm.py, at most one request per MIN_INTERVAL seconds.

Since the task B cheap-fixes stage was continued (2026-10-09), the canary only
records; it never stops a run (versions are compared inside one interleaved
run, so a stored baseline is not needed). Each check appends:

- one line to docs/canary_results.jsonl: the time, the 30 answer texts, the
  failed calls, and the endpoint identity of every call (src/llm.py), as
  counts and per case;
- one section to docs/canary_log.md: the time, the 30 answers, and which
  earlier results it matches (all 30 texts identical), or the closest ones.

scripts/build_docs.py marks a task B run "endpoint changed during run" when
the canary results named before and after it in its run.json differ.

Public AI's gateway answers a request identical to one sent in the last ~10
minutes from its cache (found on 2026-10-09). The canary request is the same
as a v3 plain arm's, so a check right after such a run partly returns that
run's answers; the log counts these gateway cache hits.
"""

import argparse
import datetime
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import env, llm, nli  # noqa: E402

CANARY = ROOT / "docs" / "canary_taskb.json"
RESULTS = ROOT / "docs" / "canary_results.jsonl"
LOG = ROOT / "docs" / "canary_log.md"
CASES = ROOT / "output" / "devB"
PROMPT, MAX_TOKENS, PER_LABEL, SEED = "v3-topic-first", 32, 10, 42
MIN_INTERVAL = 1.0  # seconds between the starts of two requests (the endpoint answered HTTP 429 at about 96 per minute)


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


def earlier_results():
    if not RESULTS.is_file():
        return []
    return [json.loads(l) for l in RESULTS.read_text(encoding="utf-8").splitlines() if l.strip()]


def identical(a, b):
    """How many of the canary answers are identical in two results. Some early results kept only the start of
    an answer (their "prefix_only" ids); a full answer then matches if it starts with that kept start."""
    same = 0
    for case_id, text in a["answers"].items():
        other = b["answers"].get(case_id)
        if other is None:
            continue
        a_cut, b_cut = case_id in a.get("prefix_only", []), case_id in b.get("prefix_only", [])
        if a_cut and b_cut:
            same += text.startswith(other) or other.startswith(text)
        elif b_cut:
            same += text.startswith(other)
        elif a_cut:
            same += other.startswith(text)
        else:
            same += text == other
    return same


def shown(text):
    """An answer as one table cell: line breaks as \\n, no pipes or backticks that would break the table."""
    return text.replace("\n", "\\n").replace("|", "\\|").replace("`", "'")


def identity_key(identity):
    return json.dumps(identity, sort_keys=True)


def check(when):
    canary = json.loads(CANARY.read_text(encoding="utf-8"))
    cases, gold = load(CASES / "cases.jsonl"), load(CASES / "expected-labels.jsonl")
    env.load_env_file()
    started = datetime.datetime.now(datetime.timezone.utc)
    answers, failed, identities, http_429, last_start, per_case = {}, [], Counter(), 0, 0.0, {}
    for case_id in canary["answers"]:
        case = cases[case_id]
        time.sleep(max(0.0, last_start + MIN_INTERVAL - time.monotonic()))
        last_start = time.monotonic()
        try:
            call = llm.chat(nli.build_messages_b(case["reference"]["text"], case["claim"]["text"], PROMPT),
                            max_tokens=MAX_TOKENS)
            answers[case_id] = call.text
        except llm.LLMError as e:
            call = e
            answers[case_id] = f"<call failed: {str(e)[:80]}>"
            failed.append(case_id)
        http_429 += call.http_429
        identities[identity_key(call.endpoint)] += 1
        per_case[case_id] = call.endpoint

    result = {"time": f"{started:%Y-%m-%d %H:%M:%S}", "when": when,
              "request": f"{PROMPT}, max_tokens {MAX_TOKENS}, no response_format, temperature 0",
              "answers": answers, "failed_calls": len(failed), "http_429": http_429,
              "endpoint": [{"calls": n, "identity": json.loads(k)} for k, n in identities.most_common()],
              "endpoint_per_case": per_case}
    cache_hits = sum(1 for e in per_case.values() if e.get("gateway_cache_hit"))
    earlier = earlier_results()
    n = len(answers)
    scores = [(identical(result, e), e) for e in earlier]
    matches = [e["time"] for s, e in scores if s == n]
    with RESULTS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")

    baseline = canary["answers"]
    lines = [f"## {result['time']} UTC: {when}", "",
             f"- {n} calls ({result['request']}), {len(failed)} failed, {http_429} answered HTTP 429 first, "
             f"{cache_hits} answered from the gateway's cache.",
             "- Endpoint identity: " + ("the same in all calls:" if len(identities) == 1 else
                                         f"{len(identities)} different identities:"), ""]
    lines += [f"  - {e['calls']} calls: `{json.dumps(e['identity'], ensure_ascii=False)}`" for e in result["endpoint"]]
    lines.append("")
    if matches:
        lines.append(f"- **Matches the earlier results of {', '.join(matches)}** (all {n} answers identical).")
    else:
        closest = sorted(scores, key=lambda x: -x[0])[:3]
        lines.append(f"- **Matches no earlier result.** Closest: "
                     + ", ".join(f"{e['time']} ({s} of {n} identical)" for s, e in closest) + ".")
    lines += ["", "| Case | Gold | Answer | Same as the baseline (01:25) |", "|---|---|---|---|"]
    for case_id, text in answers.items():
        lines.append(f"| `{case_id}` | {gold[case_id]['label']} | `{shown(text)}` | "
                     f"{'yes' if text == baseline[case_id] else '**no**'} |")
    section = "\n".join(lines) + "\n"
    with LOG.open("a", encoding="utf-8") as f:
        f.write("\n" + section)
    print(section, end="")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--make", action="store_true")
    ap.add_argument("--from-run", type=Path)
    ap.add_argument("--when", help='what the check is for, e.g. "before <run>" or "after <run>"')
    args = ap.parse_args()
    if args.make:
        make(args.from_run)
        return 0
    if not args.when:
        ap.error("give --when")
    return check(args.when)


if __name__ == "__main__":
    sys.exit(main())
