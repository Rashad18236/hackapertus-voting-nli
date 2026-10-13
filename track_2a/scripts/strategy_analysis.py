"""Analyse a robustness-experiment run (src/strategies.py, retriever variants): one table for all arms, alternative
combination rules recomputed offline from the saved sub-answers, and a REF SCORE estimate. No model calls.

Run from track_2a/ after scripts/paired_run.py:

    python3 scripts/strategy_analysis.py --run docs/runs/<run> --base base [--expected data/dev/expected-labels.jsonl]

Per arm and task: cases, labels right, Macro-F1, per-label F1, (task A) evidence score, mean input and output
tokens, mean case time, mean model time and mean local time (case time minus the model's time: what the
organisers' T counts), calls per case, and right/wrong flips against --base.

Offline rules (each recomputed from the arm's own saved sub-answers, so the requests are the same):
- xlang:     agree-else-tiebreak (what ran), agree-else-neutral, side S only, side C only; agreement rate and
             accuracy when the sides agree or disagree.
- negation:  neutral-replaced (what ran), base only, consistent-else-neutral (any inconsistent pair -> 1),
             consistency rate and accuracy of consistent and inconsistent pairs.
- decompose: parts combined (what ran), majority of parts; how many claims were split, into how many parts.

Macro-F1 and evidence are our re-implementation of the starter's rules (src/evaluate.py's Macro-F1; evidence
partial ratio >= 90 after normalising); the official numbers come from the starter's evaluate.py per arm.

REF SCORE (estimate): S_A = 0.50 F1 + 0.20 evidence + 0.15 T + 0.15 K, S_B = 0.70 F1 + 0.15 T + 0.15 K,
score = 0.6 S_A + 0.4 S_B, with K = base tokens / arm tokens and T = base local time / arm local time, both
capped at 1, i.e. as if the base arm were the best team. Only the differences between arms mean something.
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import strategies  # noqa: E402


def load(path):
    return {j["id"]: j for j in map(json.loads, Path(path).read_text(encoding="utf-8").splitlines()) if j}


def norm(text):
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def macro_f1(pairs):
    """Macro-F1 over the three labels from [(gold, predicted)]."""
    f1 = []
    for k in (0, 1, 2):
        tp = sum(g == k and p == k for g, p in pairs)
        fp = sum(g != k and p == k for g, p in pairs)
        fn = sum(g == k and p != k for g, p in pairs)
        f1.append(2 * tp / (2 * tp + fp + fn) if tp else 0.0)
    return sum(f1) / 3, f1


def evidence_hit(pred, gold):
    ref = norm(gold.get("reference") or "")
    return any(fuzz.partial_ratio(norm(e["text"]), ref) >= 90 for e in pred.get("evidence", [])[:5])


def arm_table(preds, raws, gold, task):
    ids = sorted(i for i in preds if i.endswith(f"-{task}") and i in gold)
    pairs = [(gold[i]["label"], preds[i]["label"]) for i in ids]
    f1, per = macro_f1(pairs)
    row = {"cases": len(ids), "right": sum(g == p for g, p in pairs), "macro_f1": round(f1, 4),
           "f1": [round(x, 4) for x in per]}
    if task == "A":
        ev = [i for i in ids if gold[i]["label"] in (0, 2) and gold[i].get("reference")]
        row["evidence"] = round(sum(evidence_hit(preds[i], gold[i]) for i in ev) / max(1, len(ev)), 4)
    m = [preds[i]["metrics"] for i in ids]
    n = max(1, len(ids))
    model = [raws.get(i, {}).get("model_ms", 0) or 0 for i in ids]
    row.update(input_tokens=round(sum(x["input_tokens"] for x in m) / n),
               output_tokens=round(sum(x["output_tokens"] for x in m) / n, 1),
               time_ms=round(sum(x["inference_time_ms"] for x in m) / n),
               model_ms=round(sum(model) / n),
               local_ms=round(sum(max(0, x["inference_time_ms"] - y) for x, y in zip(m, model)) / n),
               calls=round(sum(len((raws.get(i, {}).get("strategy") or {}).get("calls", [])) or 1 for i in ids) / n,
                           2))
    return row


def flips(base, arm, gold, task):
    ids = [i for i in arm if i.endswith(f"-{task}") and i in base and i in gold]
    good = sorted(i for i in ids if base[i]["label"] != gold[i]["label"] and arm[i]["label"] == gold[i]["label"])
    bad = sorted(i for i in ids if base[i]["label"] == gold[i]["label"] and arm[i]["label"] != gold[i]["label"])
    return good, bad


def calls_by_role(raw):
    return {c["role"]: c for c in (raw.get("strategy") or {}).get("calls", [])}


def offline_rules(raws, gold, task):
    """{rule: Macro-F1} and statistics for the strategy found in the raw answers of one arm."""
    with_strategy = sorted(i for i in raws if i.endswith(f"-{task}") and i in gold and raws[i].get("strategy"))
    # A strategy whose model call failed answered the case the normal way (src/cli.py); it has no rule to redo.
    ids = [i for i in with_strategy if "error" not in raws[i]["strategy"]]
    if not ids:
        return {}
    name = raws[ids[0]]["strategy"]["name"]
    rules, stats = {}, Counter()
    if len(ids) < len(with_strategy):
        stats["strategy failed, answered as today (left out of the rules)"] = len(with_strategy) - len(ids)

    def score(label_of):
        pairs = [(gold[i]["label"], label_of(i)) for i in ids]
        return round(macro_f1([(g, 1 if p is None else p) for g, p in pairs])[0], 4)

    if name == "xlang":
        def two(i):
            c = calls_by_role(raws[i])
            return (c["side_s"]["label"], c["side_c"]["label"]) if "side_s" in c else None

        def final(i, else_label=None, side=None):
            c = calls_by_role(raws[i])
            if "base" in c:
                return c["base"]["label"]
            if side:
                return c[side]["label"]
            s, k = two(i)
            if s == k:
                return s
            return c["tie_break"]["label"] if else_label is None else else_label
        rules = {"agree-else-tiebreak (ran)": score(final), "agree-else-neutral": score(lambda i: final(i, 1)),
                 "side S only": score(lambda i: final(i, side="side_s")),
                 "side C only": score(lambda i: final(i, side="side_c"))}
        for i in ids:
            t = two(i)
            if t is None:
                stats["one call (same language or no translation)"] += 1
                continue
            agree = t[0] == t[1]
            stats["sides agree" if agree else "sides disagree"] += 1
            right = final(i) == gold[i]["label"]
            stats[("agree" if agree else "disagree") + (" and right" if right else " and wrong")] += 1
        mt = [raws[i]["strategy"].get("mt_ms") for i in ids if raws[i]["strategy"].get("mt_ms") is not None]
        stats["mean MT ms (translated cases)"] = round(sum(mt) / max(1, len(mt)))
    elif name == "negation":
        def labels(i):
            c = calls_by_role(raws[i])
            return c["base"]["label"], c.get("negated", {}).get("label")

        def consistent(b, n):
            return n is not None and b is not None and strategies.IMPLIED[n] == b

        rules = {"neutral-replaced (ran)": score(lambda i: strategies.combine_negation(*labels(i))),
                 "base only": score(lambda i: labels(i)[0]),
                 "consistent-else-neutral": score(lambda i: labels(i)[0] if consistent(*labels(i)) else 1)}
        for i in ids:
            b, n = labels(i)
            if n is None:
                stats["no negation"] += 1
                continue
            ok = consistent(b, n)
            stats[("consistent" if ok else "inconsistent") + (" and base right" if b == gold[i]["label"]
                                                              else " and base wrong")] += 1
            stats[f"pair base={b} negated={n}"] += 1
    elif name == "decompose":
        def parts(i):
            c = calls_by_role(raws[i])
            return [v["label"] for k, v in c.items() if k.startswith("part_")]

        def majority(i):
            p = parts(i)
            if not p:
                return calls_by_role(raws[i])["base"]["label"]
            return Counter(1 if x is None else x for x in p).most_common(1)[0][0]
        rules = {"parts combined (ran)": score(lambda i: strategies.combine_parts(parts(i)) if parts(i)
                                               else calls_by_role(raws[i])["base"]["label"]),
                 "majority of parts": score(majority)}
        for i in ids:
            p = parts(i)
            stats[f"{len(p)} parts" if p else "not split"] += 1
            if p:
                stats["split and right" if raws[i]["strategy"] and strategies.combine_parts(p) == gold[i]["label"]
                      else "split and wrong"] += 1
    return {"strategy": name, "rules": rules, "stats": dict(stats)}


def ref_score(rows, base_rows):
    """REF SCORE estimate per arm (see the module docstring); None when an arm misses a task."""
    def part(task, row, base):
        k = min(1.0, (base["input_tokens"] + base["output_tokens"]) / max(1, row["input_tokens"] + row["output_tokens"]))
        t = min(1.0, max(1, base["local_ms"]) / max(1, row["local_ms"]))
        if task == "A":
            return 0.50 * row["macro_f1"] + 0.20 * row.get("evidence", 0) + 0.15 * t + 0.15 * k
        return 0.70 * row["macro_f1"] + 0.15 * t + 0.15 * k
    out = {}
    for task in ("A", "B"):
        if task in rows and task in base_rows and rows[task]["cases"]:
            out[task] = round(part(task, rows[task], base_rows[task]), 4)
    if len(out) == 2:
        out["total"] = round(0.6 * out["A"] + 0.4 * out["B"], 4)
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--base", default="base")
    p.add_argument("--expected", type=Path, default=ROOT / "data" / "dev" / "expected-labels.jsonl")
    args = p.parse_args()
    gold = load(args.expected)
    arms = sorted(d.name for d in args.run.iterdir() if (d / "predictions.jsonl").is_file())
    data = {a: (load(args.run / a / "predictions.jsonl"), load(args.run / a / "raw_answers.jsonl")) for a in arms}
    tasks = [t for t in ("A", "B") if any(i.endswith(f"-{t}") for i in data[arms[0]][0])]
    report = {"arms": {}}
    for a in arms:
        preds, raws = data[a]
        rows = {t: arm_table(preds, raws, gold, t) for t in tasks}
        report["arms"][a] = {"tables": rows, "offline": {t: offline_rules(raws, gold, t) for t in tasks}}
        if args.base in data and a != args.base:
            report["arms"][a]["flips"] = {t: dict(zip(("wrong_to_right", "right_to_wrong"),
                                                      flips(data[args.base][0], preds, gold, t))) for t in tasks}
    if args.base in report["arms"]:
        base_rows = report["arms"][args.base]["tables"]
        for a in arms:
            report["arms"][a]["ref_score"] = ref_score(report["arms"][a]["tables"], base_rows)
    (args.run / "analysis.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    for t in tasks:
        print(f"\n### Task {t}\n")
        head = "| arm | right | Macro-F1 | F1 E / N / C |" + (" evidence |" if t == "A" else "") + \
               " input tok | output tok | calls | time ms | model ms | local ms | wrong→right | right→wrong | REF |"
        print(head)
        print("|" + "---|" * (head.count("|") - 1))
        for a in arms:
            r, info = report["arms"][a]["tables"][t], report["arms"][a]
            fl = info.get("flips", {}).get(t, {})
            ev = f" {r['evidence']:.3f} |" if t == "A" else ""
            print(f"| {a} | {r['right']}/{r['cases']} | {r['macro_f1']:.4f} | {' / '.join(f'{x:.3f}' for x in r['f1'])} |"
                  f"{ev} {r['input_tokens']:,} | {r['output_tokens']} | {r['calls']} | {r['time_ms']:,} | "
                  f"{r['model_ms']:,} | {r['local_ms']:,} | {len(fl.get('wrong_to_right', []))} | "
                  f"{len(fl.get('right_to_wrong', []))} | {info.get('ref_score', {}).get(t, '')} |")
        for a in arms:
            off = report["arms"][a]["offline"].get(t)
            if off:
                print(f"\n{a} ({off['strategy']}), task {t}: rules {off['rules']}; {off['stats']}")
    totals = {a: report["arms"][a].get("ref_score", {}).get("total") for a in arms}
    if any(v is not None for v in totals.values()):
        print("\nREF SCORE total (estimate, base = best):", totals)


if __name__ == "__main__":
    main()
