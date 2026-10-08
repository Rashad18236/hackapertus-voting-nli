"""Per-language breakdown of a predictions file. NOT the official score.

The source of truth for scores is the starter's evaluate.py (official rules,
see docs/official_contract.md). This script exists for the breakdowns the
starter does not print: same-language versus cross-lingual, per claim
language, per source language, a confusion matrix, and p95 time.

Usage:
    python -m src.evaluate --predictions P.jsonl --expected E.jsonl --cases C.jsonl [--json OUT]

The validity rules copy the starter, so the per-task Macro-F1 printed here must
equal the starter's on the same files (scripts/self_checks.py verifies this):
- a missing response, a duplicated id, a label outside 0/1/2, or a label_name
  that does not match the label counts as wrong: a false negative for the gold
  class and a false positive for no class;
- per-class precision/recall/F1 are 0 when their denominator is 0;
- Macro-F1 averages F1 over the classes that occur in the gold labels or the
  valid predictions (with all three present, that is the plain mean of three).
p95 uses the nearest-rank method: the value at position ceil(0.95 * n).
Language pairs are written source->claim, as in the starter.
"""

import argparse
import json
import math
from collections import Counter

LABELS = [0, 1, 2]
LABEL_NAMES = {0: "entailment", 1: "neutral", 2: "contradiction"}
INVALID = "invalid"


def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


# ---------- labels ----------

def valid_label(prediction):
    """Return the label as 0/1/2, or None if the response breaks the contract."""
    if not prediction:
        return None
    label = prediction.get("label")
    if isinstance(label, bool) or not isinstance(label, int) or label not in LABELS:
        return None
    if prediction.get("label_name") != LABEL_NAMES[label]:
        return None
    return label


def label_scores(gold_labels, pred_labels):
    """Per-class precision/recall/F1, Macro-F1, accuracy and confusion matrix.

    pred_labels may contain None for missing or invalid responses.
    """
    confusion = {g: {p: 0 for p in LABELS + [INVALID]} for g in LABELS}
    for g, p in zip(gold_labels, pred_labels):
        confusion[g][INVALID if p is None else p] += 1

    per_class = {}
    for c in LABELS:
        tp = confusion[c][c]
        fp = sum(confusion[g][c] for g in LABELS if g != c)
        fn = sum(confusion[c][p] for p in LABELS + [INVALID] if p != c)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[LABEL_NAMES[c]] = {"precision": precision, "recall": recall, "f1": f1, "support": tp + fn}

    present = set(gold_labels) | {p for p in pred_labels if p is not None}
    n = len(gold_labels)
    return {
        "n": n,
        "macro_f1": sum(per_class[LABEL_NAMES[c]]["f1"] for c in present) / len(present) if present else 0.0,
        "accuracy": sum(1 for g, p in zip(gold_labels, pred_labels) if g == p) / n if n else 0.0,
        "per_class": per_class,
        "confusion": {LABEL_NAMES[g]: {(LABEL_NAMES[p] if p != INVALID else p): v for p, v in row.items()}
                      for g, row in confusion.items()},
        "invalid": sum(1 for p in pred_labels if p is None),
    }


# ---------- tokens and time ----------

def p95(values):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[math.ceil(0.95 * len(ordered)) - 1]


def cost_scores(predictions):
    metrics = [p.get("metrics") or {} for p in predictions]
    inp = [m["input_tokens"] for m in metrics if "input_tokens" in m]
    out = [m["output_tokens"] for m in metrics if "output_tokens" in m]
    ms = [m["inference_time_ms"] for m in metrics if "inference_time_ms" in m]
    mean = lambda xs: sum(xs) / len(xs) if xs else None  # noqa: E731
    return {
        "input_tokens_sum": sum(inp), "input_tokens_mean": mean(inp),
        "output_tokens_sum": sum(out), "output_tokens_mean": mean(out),
        "time_ms_mean": mean(ms), "time_ms_p95": p95(ms),
    }


# ---------- everything together ----------

def task_of(case):
    return "A" if "booklet" in case else "B"


def source_language(case):
    return (case.get("booklet") or case.get("reference") or {}).get("language", "?")


def evaluate(predictions, expected, cases):
    """Scores per task, with breakdowns. cases maps id -> request."""
    counts = Counter(p.get("id") for p in predictions)
    preds_by_id = {p.get("id"): p for p in predictions if counts[p.get("id")] == 1}  # duplicates are invalid
    issues = {
        "missing": sum(1 for e in expected if e["id"] not in counts),
        "duplicated ids": sum(1 for v in counts.values() if v > 1),
        "unknown ids": sum(1 for i in counts if i not in {e["id"] for e in expected}),
    }

    report = {"issues": issues, "tasks": {}}
    for task in sorted({task_of(cases[e["id"]]) for e in expected}):
        rows = [e for e in expected if task_of(cases[e["id"]]) == task]
        gold = [e["label"] for e in rows]
        pred = [valid_label(preds_by_id.get(e["id"])) for e in rows]

        def subset(keep):
            idx = [i for i, e in enumerate(rows) if keep(cases[e["id"]])]
            s = label_scores([gold[i] for i in idx], [pred[i] for i in idx])
            return {"n": s["n"], "macro_f1": s["macro_f1"], "accuracy": s["accuracy"], "invalid": s["invalid"]}

        def lang_pair(c):
            return f"{source_language(c)}->{c['claim']['language']}"

        pairs = sorted({lang_pair(cases[e["id"]]) for e in rows})
        languages = sorted({c["claim"]["language"] for c in cases.values()})
        report["tasks"][task] = {
            "labels": label_scores(gold, pred),
            "cost": cost_scores([preds_by_id[e["id"]] for e in rows if e["id"] in preds_by_id]),
            "same_vs_cross": {
                "same-language": subset(lambda c: source_language(c) == c["claim"]["language"]),
                "cross-lingual": subset(lambda c: source_language(c) != c["claim"]["language"]),
            },
            "by_claim_language": {lang: subset(lambda c, lang=lang: c["claim"]["language"] == lang)
                                  for lang in languages},
            "by_source_language": {lang: subset(lambda c, lang=lang: source_language(c) == lang)
                                   for lang in languages},
            "by_language_pair": {pair: subset(lambda c, pair=pair: lang_pair(c) == pair) for pair in pairs},
        }
    return report


def format_report(report):
    f = lambda x: "n/a" if x is None else f"{x:.3f}"  # noqa: E731
    lines = ["Issues: " + ", ".join(f"{k} {v}" for k, v in report["issues"].items())]
    for task, r in report["tasks"].items():
        lab, cost = r["labels"], r["cost"]
        lines += [
            "", f"=== Task {task}: {lab['n']} cases, invalid or missing {lab['invalid']}",
            f"Macro-F1: {f(lab['macro_f1'])}   accuracy: {f(lab['accuracy'])}",
            "confusion (rows gold, columns predicted):",
            "               " + "  ".join(f"{c[:7]:>7}" for c in list(LABEL_NAMES.values()) + [INVALID]),
        ]
        for g, row in lab["confusion"].items():
            lines.append(f"{g:<14} " + "  ".join(f"{v:>7}" for v in row.values()))
        lines += [
            f"Input tokens: sum {cost['input_tokens_sum']}, mean {f(cost['input_tokens_mean'])}   "
            f"Output tokens: mean {f(cost['output_tokens_mean'])}   "
            f"Time ms: mean {f(cost['time_ms_mean'])}, p95 {cost['time_ms_p95']}",
            "", "group                n    macro_f1  accuracy  invalid",
        ]
        groups = (list(r["same_vs_cross"].items())
                  + [(f"claim {k}", v) for k, v in r["by_claim_language"].items()]
                  + [(f"source {k}", v) for k, v in r["by_source_language"].items()]
                  + list(r["by_language_pair"].items()))
        for name, s in groups:
            lines.append(f"{name:<20} {s['n']:<4} {s['macro_f1']:.3f}     {s['accuracy']:.3f}     {s['invalid']}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Per-language breakdown (not the official score).")
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--expected", required=True)
    parser.add_argument("--cases", required=True)
    parser.add_argument("--json", help="also write the full result as JSON")
    args = parser.parse_args()
    cases = {c["id"]: c for c in load_jsonl(args.cases)}
    report = evaluate(load_jsonl(args.predictions), load_jsonl(args.expected), cases)
    print(format_report(report))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)


if __name__ == "__main__":
    main()
