"""Arms of one interleaved run: one table for all arms, the flips of each comparison, endpoint identity.

Written for task B; since session 9 also for task A (--task A: the starter's evidence score per arm, and a
second call of L2 counted in "calls").

Run from track_2a/ after scoring every arm with the starter's evaluate.py (official_score.json in each arm):

    python3 scripts/interleaved_analysis.py --run docs/runs/<run> --arms A-v3-plain B-v3-schema C-v5-min D-v5-ballot \\
        --compare B-v3-schema:A-v3-plain --compare C-v5-min:B-v3-schema --compare D-v5-ballot:C-v5-min \\
        [--canary "<time before>" "<time after>"]

Per arm: Macro-F1 and per-label F1 (official_score.json, the starter's
scorer), the confusion matrix, mean and p95 input tokens, mean output tokens,
tokens per case (mean input + mean output), mean and p95 time, failed calls,
unreadable answers, HTTP 429 answers and retries, the forms of the answer
texts, and mean time by position in the case's order.

Per comparison NEW:OLD: the change in Macro-F1, per-label F1 and tokens per
case, and the cases that went from right to wrong and from wrong to right.

Endpoint identity (src/llm.py, recorded per call): how many different
identities the run's calls (and the two canary checks given with --canary)
had, and which fields took more than one value.

Backends: the backend that wrote an answer is named by the answer's
system_fingerprint (on a gateway cache hit the routing headers show the
gateway's current choice, the fingerprint the cached answer's origin). Per
arm: calls per backend, Macro-F1 on each backend's cases, and gateway cache
hits (marked by src/llm.py since 2026-10-09 02:50 UTC; before that, a
response without the upstream llm_provider-server header). Per comparison:
the same numbers on the cases where both arms were answered by the same
backend and on those where they were not.

Writes analysis.json to --run and prints a markdown summary. Only arms of the
same run are compared (decision of 2026-10-09 02:00 UTC).
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import evaluate  # noqa: E402

LABELS = ("entailment", "neutral", "contradiction")


def load(path):
    return {json.loads(l)["id"]: json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()}


def answer_form(text):
    """Group answer texts: exactly {"label": n}, the same with other spacing, JSON plus more text, or other."""
    if text is None:
        return "no answer (failed call)"
    stripped = text.strip()
    if stripped in ('{"label": 0}', '{"label": 1}', '{"label": 2}'):
        return 'exactly {"label": n}'
    try:
        json.loads(stripped)
        return "JSON with other spacing"
    except ValueError:
        return "JSON plus text" if stripped.startswith("{") else "other text"


def backend(raw):
    """The backend that wrote this answer: its system_fingerprint (None for a failed call without one)."""
    return (raw.get("endpoint") or {}).get("system_fingerprint")


def cache_hit(raw):
    identity = raw.get("endpoint") or {}
    if "gateway_cache_hit" in identity:
        return identity["gateway_cache_hit"]
    return bool(identity.get("headers")) and "llm_provider-server" not in identity["headers"]


def macro(ids, gold, preds):
    if not ids:
        return None
    return round(evaluate.label_scores([gold[i]["label"] for i in ids], [preds[i]["label"] for i in ids])["macro_f1"], 4)


def arm_numbers(folder, gold, task="B"):
    preds, raws = load(folder / "predictions.jsonl"), load(folder / "raw_answers.jsonl")
    official = json.loads((folder / "official_score.json").read_text(encoding="utf-8"))["tasks"][task]
    ids = list(gold)
    inputs = [preds[i]["metrics"]["input_tokens"] for i in ids]
    outputs = [preds[i]["metrics"]["output_tokens"] for i in ids]
    times = [preds[i]["metrics"]["inference_time_ms"] for i in ids]
    confusion = [[sum(1 for i in ids if gold[i]["label"] == g and preds[i]["label"] == p) for p in range(3)]
                 for g in range(3)]
    by_position = defaultdict(list)
    for i in ids:
        by_position[raws[i].get("order")].append(preds[i]["metrics"]["inference_time_ms"])
    numbers = {
        "macro_f1": round(official["macro_f1"], 6),
        "f1": {k: round(official["per_class"][k]["f1"], 6) for k in LABELS},
        "recall": {k: round(official["per_class"][k]["recall"], 6) for k in LABELS},
        "calls": sum(1 + ("answer" in (raws[i].get("second_look") or {}) or "error" in (raws[i].get("second_look") or {}))
                     for i in ids),
        "confusion_rows_gold_cols_pred": confusion,
        "mean_input_tokens": round(sum(inputs) / len(ids), 1),
        "p95_input_tokens": evaluate.p95(inputs),
        "mean_output_tokens": round(sum(outputs) / len(ids), 2),
        "tokens_per_case": round((sum(inputs) + sum(outputs)) / len(ids), 1),
        "mean_time_ms": round(sum(times) / len(ids)),
        "p95_time_ms": evaluate.p95(times),
        "failed_calls": sum(1 for i in ids if raws[i].get("error")),
        "unreadable_answers": sum(1 for i in ids if raws[i].get("parse_reason")),
        "http_429": sum(raws[i].get("http_429", 0) for i in ids),
        "retries": sum(max(0, raws[i].get("attempts", 1) - 1) for i in ids),
        "answer_forms": dict(Counter(answer_form(raws[i].get("answer")) for i in ids).most_common()),
        "mean_time_ms_by_position": {str(k): round(sum(v) / len(v)) for k, v in sorted(by_position.items())},
        "gateway_cache_hits": sum(1 for i in ids if cache_hit(raws[i])),
        "by_backend": {str(b): {"calls": len(sub), "macro_f1": macro(sub, gold, preds),
                                "unreadable_answers": sum(1 for i in sub if raws[i].get("parse_reason")),
                                "mean_time_ms": round(sum(preds[i]["metrics"]["inference_time_ms"] for i in sub) / len(sub))}
                       for b, sub in group_by(ids, lambda i: backend(raws[i])).items()},
    }
    if task == "A":
        numbers["evidence"] = {"score": round(official["evidence_score"], 6), "found": official["evidence"]["found"],
                               "cases": official["evidence"]["cases"]}
    return numbers, preds, raws


def group_by(ids, key):
    groups = defaultdict(list)
    for i in ids:
        groups[key(i)].append(i)
    return dict(sorted(groups.items(), key=lambda kv: -len(kv[1])))


def identity_report(identities):
    """identities: list of (where, identity dict). Distinct identities with counts; fields with more than one value."""
    flat = []
    for where, ident in identities:
        fields = {k: v for k, v in ident.items() if k != "headers"}
        fields.update({f"header {k}": v for k, v in (ident.get("headers") or {}).items()})
        flat.append((where, fields))
    distinct = Counter(json.dumps(f, sort_keys=True) for _, f in flat)
    names = sorted({k for _, f in flat for k in f})
    varying = {}
    for name in names:
        values = Counter(str(f.get(name, "<absent>")) for _, f in flat)
        if len(values) > 1:
            varying[name] = dict(values.most_common())
    return {"calls": len(flat), "distinct_identities": len(distinct),
            "identities": [{"calls": n, "identity": json.loads(k)} for k, n in distinct.most_common()],
            "fields_that_vary": varying}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--arms", nargs="+", required=True)
    ap.add_argument("--compare", action="append", default=[], help="NEW:OLD")
    ap.add_argument("--cases", type=Path, default=ROOT / "output" / "devB")
    ap.add_argument("--canary", nargs=2, metavar=("BEFORE", "AFTER"), help="times of the canary checks")
    ap.add_argument("--task", choices=("A", "B"), default="B")
    args = ap.parse_args()

    gold = load(args.cases / "expected-labels.jsonl")
    arms, preds, raws = {}, {}, {}
    for name in args.arms:
        arms[name], preds[name], raws[name] = arm_numbers(args.run / name, gold, args.task)

    comparisons = {}
    for pair in args.compare:
        new, old = pair.split(":")
        right = lambda arm, i: preds[arm][i]["label"] == gold[i]["label"]  # noqa: E731
        to_wrong = sorted(i for i in gold if right(old, i) and not right(new, i))
        to_right = sorted(i for i in gold if not right(old, i) and right(new, i))
        comparisons[pair] = {
            "macro_f1_change": round(arms[new]["macro_f1"] - arms[old]["macro_f1"], 4),
            "f1_change": {k: round(arms[new]["f1"][k] - arms[old]["f1"][k], 4) for k in LABELS},
            "tokens_per_case_change": round(arms[new]["tokens_per_case"] - arms[old]["tokens_per_case"], 1),
            "input_tokens_change": round(arms[new]["mean_input_tokens"] - arms[old]["mean_input_tokens"], 1),
            "output_tokens_change": round(arms[new]["mean_output_tokens"] - arms[old]["mean_output_tokens"], 2),
            "unreadable_new": arms[new]["unreadable_answers"],
            "right_to_wrong": len(to_wrong), "wrong_to_right": len(to_right),
            "labels_differ": sum(1 for i in gold if preds[new][i]["label"] != preds[old][i]["label"]),
            "right_to_wrong_ids": to_wrong, "wrong_to_right_ids": to_right,
        }
        for kind, same in (("same_backend", True), ("different_backend", False)):
            sub = [i for i in gold if (backend(raws[new][i]) == backend(raws[old][i])) == same]
            comparisons[pair][kind] = {
                "cases": len(sub), "macro_f1_old": macro(sub, gold, preds[old]), "macro_f1_new": macro(sub, gold, preds[new]),
                "labels_differ": sum(1 for i in sub if preds[new][i]["label"] != preds[old][i]["label"]),
                "right_to_wrong": sum(1 for i in sub if i in to_wrong), "wrong_to_right": sum(1 for i in sub if i in to_right)}

    identities = [(f"{name} {i}", raws[name][i].get("endpoint") or {}) for name in args.arms for i in gold]
    canary = {}
    if args.canary:
        results = {json.loads(l)["time"]: json.loads(l)
                   for l in (ROOT / "docs" / "canary_results.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
        for when, t in zip(("before", "after"), args.canary):
            r = results[t]
            canary[when] = {"time": t, "failed_calls": r["failed_calls"], "http_429": r["http_429"]}
            identities += [(f"canary {when}", e["identity"]) for e in r["endpoint"] for _ in range(e["calls"])]
        before, after = (results[t]["answers"] for t in args.canary)
        canary["answers_differ"] = sorted(i for i in before if before[i] != after[i])
    hosts = defaultdict(Counter)  # fingerprint -> backend hosts named in the headers of answers that were not cached
    for name in args.arms:
        for i in gold:
            if not cache_hit(raws[name][i]):
                base = ((raws[name][i].get("endpoint") or {}).get("headers") or {}).get("x-litellm-model-api-base")
                hosts[str(backend(raws[name][i]))][str(base)] += 1
    out = {"run": args.run.as_posix(), "arms": arms, "comparisons": comparisons, "canary": canary,
           "endpoint_identity": identity_report(identities),
           "backend_hosts": {fp: dict(c.most_common()) for fp, c in hosts.items()}}
    (args.run / "analysis.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    rows = [("Macro-F1", lambda a: f"{a['macro_f1']:.3f}"),
            ("F1 E / N / C", lambda a: " / ".join(f"{a['f1'][k]:.3f}" for k in LABELS)),
            ("Confusion, gold E (pred E/N/C)", lambda a: " / ".join(map(str, a["confusion_rows_gold_cols_pred"][0]))),
            ("Confusion, gold N", lambda a: " / ".join(map(str, a["confusion_rows_gold_cols_pred"][1]))),
            ("Confusion, gold C", lambda a: " / ".join(map(str, a["confusion_rows_gold_cols_pred"][2]))),
            ("Input tokens, mean / p95", lambda a: f"{a['mean_input_tokens']:,.1f} / {a['p95_input_tokens']:,}"),
            ("Output tokens, mean", lambda a: f"{a['mean_output_tokens']:.2f}"),
            ("Tokens per case (input + output)", lambda a: f"{a['tokens_per_case']:,.1f}"),
            ("Time, mean / p95 (ms)", lambda a: f"{a['mean_time_ms']:,} / {a['p95_time_ms']:,}"),
            ("Failed calls", lambda a: str(a["failed_calls"])),
            ("Unreadable answers", lambda a: str(a["unreadable_answers"])),
            ("HTTP 429 answers / retries", lambda a: f"{a['http_429']} / {a['retries']}"),
            ("Recall E / N / C", lambda a: " / ".join(f"{a['recall'][k]:.3f}" for k in LABELS)),
            ("Model calls", lambda a: str(a["calls"]))]
    if args.task == "A":
        rows.append(("Evidence score", lambda a: f"{a['evidence']['score']:.3f} ({a['evidence']['found']}/{a['evidence']['cases']})"))
    print("| | " + " | ".join(args.arms) + " |")
    print("|---|" + "---|" * len(args.arms))
    for label, fmt in rows:
        print(f"| {label} | " + " | ".join(fmt(arms[n]) for n in args.arms) + " |")
    print()
    for pair, c in comparisons.items():
        print(f"{pair}: Macro-F1 {c['macro_f1_change']:+.4f}, F1 E/N/C "
              + " / ".join(f"{c['f1_change'][k]:+.4f}" for k in LABELS)
              + f", tokens per case {c['tokens_per_case_change']:+.1f} (input {c['input_tokens_change']:+.1f}, "
              f"output {c['output_tokens_change']:+.2f}), unreadable {c['unreadable_new']}, "
              f"right->wrong {c['right_to_wrong']}, wrong->right {c['wrong_to_right']}, labels differ {c['labels_differ']}")
    ident = out["endpoint_identity"]
    print(f"\nendpoint identity: {ident['calls']} calls, {ident['distinct_identities']} distinct; "
          f"fields that vary: {json.dumps(ident['fields_that_vary'], ensure_ascii=False)}")
    if canary:
        print(f"canary before {canary['before']['time']}, after {canary['after']['time']}: "
              f"answers differ in {len(canary['answers_differ'])} cases {canary['answers_differ']}")
    for name in args.arms:
        print(f"{name}: forms {arms[name]['answer_forms']}; time by position {arms[name]['mean_time_ms_by_position']}; "
              f"gateway cache hits {arms[name]['gateway_cache_hits']}")
        for b, v in arms[name]["by_backend"].items():
            print(f"   backend {b[:24]}: {v}")
    for pair, c in comparisons.items():
        print(f"{pair}: same backend {c['same_backend']}; different backend {c['different_backend']}")
    print("backend hosts by fingerprint (answers not from the cache):", json.dumps(out["backend_hosts"]))


if __name__ == "__main__":
    main()
