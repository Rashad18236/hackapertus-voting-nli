"""Session 9, phase E3 (information only): Apertus as the router, against src/claim_router.py's rules.

Run from track_2a/ (calls the model named in .env, at most one request per second):

    LLM_MIN_INTERVAL=1 python3 scripts/llm_router_check.py --out docs/runs/<folder>

Claims: the 300 dev task A claims (output/devA/cases.jsonl; no intended part is recorded for them, so only the
agreement with the rules is measured) and the 300 openings of the router stress test (scripts/router_stress.py,
each with the part a careful reader would route it to, or none).

For each claim one call: the prompt ROUTER_PROMPT asks which part of the vote's section the claim's opening
names (summary, council, committee, law, detail, or none), answered as {"part": ...} under a JSON schema. The
pipeline is not changed: the rules stay the router; this only measures whether Apertus would agree, and at
what cost in tokens and time.

Writes per_claim.jsonl and summary.json to --out; prints the summary.
"""

import argparse
import json
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import router_stress  # noqa: E402
from src import claim_router, env, llm  # noqa: E402

PARTS = ("summary", "council", "committee", "law", "detail", "none")
ROUTER_PROMPT = """A CLAIM about an official Swiss federal voting booklet usually opens by naming the part of the booklet's section on a ballot that it draws on. Say which part its opening names:
- "summary": the booklet's summary or overview of the ballot;
- "council": the arguments or recommendation of the Federal Council (and Parliament);
- "committee": the arguments or recommendation of the initiative or referendum committee;
- "law": the text put to the vote, the legal text itself;
- "detail": what happens or changes if the ballot is accepted, the detailed explanation;
- "none": the opening names none of these.
The claim may be in German, French or Italian.

Answer with one JSON object and nothing else, for example:
{"part": "council"}"""
SCHEMA = {"type": "object", "properties": {"part": {"type": "string", "enum": list(PARTS)}},
          "required": ["part"], "additionalProperties": False}


def claims():
    rows = []
    for line in (ROOT / "output" / "devA" / "cases.jsonl").read_text(encoding="utf-8").splitlines():
        case = json.loads(line)
        rows.append({"set": "dev", "id": case["id"], "language": case["claim"]["language"],
                     "claim": case["claim"]["text"], "intended": None})
    for language, base in (("de", router_stress.DE), ("fr", router_stress.FR), ("it", router_stress.IT)):
        for n, (intended, text, variant) in enumerate(router_stress.with_variants(base), start=1):
            rows.append({"set": "stress", "id": f"stress-{language}-{n}", "language": language, "claim": text,
                         "intended": intended or "none", "variant": variant})
    return rows


def ask(claim):
    messages = [{"role": "system", "content": ROUTER_PROMPT}, {"role": "user", "content": f"CLAIM:\n{claim}"}]
    try:
        result = llm.chat(messages, max_tokens=16, json_schema=SCHEMA)
    except llm.LLMError as e:
        return {"error": str(e), "endpoint": e.endpoint}
    try:
        part = json.loads(result.text).get("part")
    except ValueError:
        part = None
    return {"answer": result.text, "part": part if part in PARTS else None, "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens, "elapsed_ms": result.elapsed_ms, "endpoint": result.endpoint}


def summarise(rows):
    out = {}
    for name in ("dev", "stress"):
        mine = [r for r in rows if r["set"] == name]
        ok = [r for r in mine if "error" not in r]
        entry = {"claims": len(mine), "failed_calls": len(mine) - len(ok),
                 "unreadable": sum(1 for r in ok if r["part"] is None),
                 "agrees_with_rules": sum(1 for r in ok if r["part"] == r["rules"]),
                 "model_parts": dict(Counter(str(r["part"]) for r in ok)),
                 "rule_parts": dict(Counter(r["rules"] for r in mine)),
                 "disagreements_rules_to_model": dict(Counter(f"{r['rules']} -> {r['part']}" for r in ok
                                                              if r["part"] != r["rules"])),
                 "mean_input_tokens": round(statistics.mean(r["input_tokens"] for r in ok), 1) if ok else None,
                 "mean_output_tokens": round(statistics.mean(r["output_tokens"] for r in ok), 2) if ok else None,
                 "mean_time_ms": round(statistics.mean(r["elapsed_ms"] for r in ok)) if ok else None}
        if name == "stress":
            entry["model_right"] = sum(1 for r in ok if r["part"] == r["intended"])
            entry["rules_right"] = sum(1 for r in mine if r["rules"] == r["intended"])
            entry["model_wrong_part"] = sum(1 for r in ok if r["part"] not in (r["intended"], "none", None))
            entry["rules_wrong_part"] = sum(1 for r in mine if r["rules"] not in (r["intended"], "none"))
        out[name] = entry
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--limit", type=int, help="only the first N claims of each set (a smoke test)")
    args = ap.parse_args()
    env.load_env_file(ROOT / ".env")
    rows = claims()
    if args.limit:
        rows = [r for r in rows if r["set"] == "dev"][:args.limit] + [r for r in rows if r["set"] == "stress"][:args.limit]
    args.out.mkdir(parents=True, exist_ok=True)
    started = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    with (args.out / "per_claim.jsonl").open("w", encoding="utf-8") as f:
        for n, row in enumerate(rows, start=1):
            row["rules"] = claim_router.route(row["claim"]) or "none"
            row.update(ask(row["claim"]))
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            if n % 50 == 0:
                print(f"[{n}/{len(rows)}]", flush=True)
    summary = {"started_utc": started, "ended_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
               **summarise(rows)}
    (args.out / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
