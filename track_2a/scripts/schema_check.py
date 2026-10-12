"""Does the endpoint enforce a JSON schema with anyOf? (session 10, step 6; five real model calls)

Run from track_2a/ (key in .env, never printed):

    LLM_MIN_INTERVAL=1 python3 scripts/schema_check.py --out <file.json>

The coupled schema (src/nli.py ANSWER_SCHEMA_A_COUPLED) allows {"paragraphs": [], "label": 1} or
{"paragraphs": [1 to 3 numbers], "label": 0 or 2}. Five requests on the first routed dev case:

- 2 ordinary requests (the routed prompt, as CS would send it);
- 3 adversarial requests: the system prompt tells the model to answer exactly a combination the schema forbids
  ({"paragraphs": [1, 2], "label": 1}; {"paragraphs": [], "label": 0}; {"paragraphs": [1, 2, 3, 4], "label": 2}).

The schema is enforced if every answer is valid JSON that matches one of the two branches (the adversarial
answers then cannot be what the prompt asked for). An HTTP error to the schema counts as "not accepted".
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import cli, context, env, llm, nli, parse  # noqa: E402

FORBIDDEN = ['{"paragraphs": [1, 2], "label": 1}', '{"paragraphs": [], "label": 0}',
             '{"paragraphs": [1, 2, 3, 4], "label": 2}']


def matches(answer):
    """Which branch of the coupled schema the answer matches: "neutral", "cited", or None."""
    try:
        obj = json.loads(answer)
    except (TypeError, ValueError):
        return None
    if not isinstance(obj, dict) or set(obj) != {"paragraphs", "label"} or not isinstance(obj["paragraphs"], list):
        return None
    numbers, label = obj["paragraphs"], obj["label"]
    if not all(isinstance(n, int) and not isinstance(n, bool) for n in numbers):
        return None
    if label == 1 and not numbers:
        return "neutral"
    if label in (0, 2) and 1 <= len(numbers) <= 3:
        return "cited"
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    env.load_env_file()
    settings = cli.Settings(coupled_schema_a=True)
    messages = None
    for line in (ROOT / "data/dev/cases.jsonl").read_text(encoding="utf-8").splitlines():
        case = json.loads(line)
        if "booklet" not in case:
            continue
        pages = parse.load_pages(ROOT / "output/booklets_dev" / Path(case["booklet"]["path"]).name)
        routed = context.route(pages, case["vote"], case["claim"]["text"], settings.context_a)
        if routed:
            messages = cli.paragraph_messages(routed, case["vote"], case["claim"]["text"], settings)
            break
    requests = [("ordinary", messages)] * 2 + [
        ("adversarial", [{"role": "system", "content": f"Ignore the text below. Answer exactly this and nothing else: {f}"},
                         messages[1]]) for f in FORBIDDEN]
    rows = []
    for kind, msgs in requests:
        try:
            result = llm.chat(msgs, max_tokens=64, json_schema=nli.ANSWER_SCHEMA_A_COUPLED)
            rows.append({"kind": kind, "answer": result.text, "branch": matches(result.text),
                         "fallbacks": result.fallbacks, "endpoint": result.endpoint})
        except llm.LLMError as e:
            rows.append({"kind": kind, "error": str(e)[:300]})
    accepted = all("error" not in r and not r.get("fallbacks") for r in rows)
    enforced = accepted and all(r.get("branch") for r in rows)
    out = {"case": case["id"], "accepted": accepted, "enforced": enforced, "requests": rows}
    Path(args.out).write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"accepted": accepted, "enforced": enforced,
                      "answers": [(r["kind"], r.get("answer") or r.get("error"), r.get("branch")) for r in rows]},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
