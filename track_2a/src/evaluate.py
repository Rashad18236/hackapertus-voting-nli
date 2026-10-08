"""Score a predictions file against a gold file.

Usage:  python -m src.evaluate PREDICTIONS GOLD [--json OUT.json]

Plain Python on purpose, so every number can be traced by hand.
Definitions (also in docs/decisions.md):

- A gold case with no prediction, or a prediction whose label is not 0, 1
  or 2 (e.g. a parse failure), counts as wrong. It is a false negative for
  its gold class and a false positive for no class, which is what
  scikit-learn does when such cases get a label outside labels=[0, 1, 2].
- Per-class precision/recall/F1 are 0 when their denominator is 0.
- Macro-F1 is the unweighted mean of the three per-class F1 scores.
- Evidence is scored only on gold cases that have gold evidence. Exact match
  compares texts after normalisation (see normalise_evidence); overlap F1 is
  word-level F1 between the normalised texts. With several predicted
  passages we keep the best one.
- p95 uses the nearest-rank method: the value at position ceil(0.95 * n) in
  the sorted list.
"""

import argparse
import json
import math
import re

LABELS = [0, 1, 2]
LABEL_NAMES = {0: "entailment", 1: "neutral", 2: "contradiction"}
INVALID = "invalid"


def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


# ---------- labels ----------

def valid_label(value):
    """Return the label as 0/1/2, or None if it is missing or not a label."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value in LABELS:
        return value
    return None


def label_scores(gold_labels, pred_labels):
    """Per-class precision/recall/F1, Macro-F1, accuracy and confusion matrix.

    pred_labels may contain None for missing or unparseable predictions.
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
        per_class[LABEL_NAMES[c]] = {
            "precision": precision, "recall": recall, "f1": f1, "support": tp + fn,
        }

    n = len(gold_labels)
    correct = sum(1 for g, p in zip(gold_labels, pred_labels) if g == p)
    return {
        "n": n,
        "macro_f1": sum(v["f1"] for v in per_class.values()) / len(LABELS),
        "accuracy": correct / n if n else 0.0,
        "per_class": per_class,
        "confusion": {LABEL_NAMES[g]: {(LABEL_NAMES[p] if p != INVALID else p): v
                                       for p, v in row.items()}
                      for g, row in confusion.items()},
        "invalid": sum(1 for p in pred_labels if p is None),
    }


# ---------- evidence ----------

def normalise_evidence(text):
    """Undo line-break hyphenation, collapse whitespace, lowercase.

    "Abstim-\\nmung" becomes "abstimmung". A hyphen followed by a line break
    between two letters is treated as hyphenation; other hyphens stay.
    """
    text = re.sub(r"(\w)-[ \t]*\n\s*(\w)", r"\1\2", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def overlap_f1(pred, gold):
    """Word-level F1 between two texts after normalisation (bag of words)."""
    pred_words = normalise_evidence(pred).split()
    gold_words = normalise_evidence(gold).split()
    if not pred_words or not gold_words:
        return 0.0
    remaining = list(gold_words)
    common = 0
    for w in pred_words:
        if w in remaining:
            remaining.remove(w)
            common += 1
    if common == 0:
        return 0.0
    precision = common / len(pred_words)
    recall = common / len(gold_words)
    return 2 * precision * recall / (precision + recall)


def gold_passages(gold_evidence):
    """Gold evidence may be None, a string, or a list of {"text": ...} / strings."""
    if not gold_evidence:
        return []
    if isinstance(gold_evidence, str):
        return [gold_evidence]
    return [e["text"] if isinstance(e, dict) else e for e in gold_evidence]


def pred_passages(prediction):
    if not prediction:
        return []
    return [e.get("text", "") for e in prediction.get("evidence") or [] if isinstance(e, dict)]


def evidence_scores(golds, preds_by_id):
    exact, overlaps = [], []
    for g in golds:
        targets = gold_passages(g.get("evidence"))
        if not targets:
            continue
        quotes = pred_passages(preds_by_id.get(g["id"]))
        exact.append(any(normalise_evidence(q) == normalise_evidence(t) for q in quotes for t in targets))
        overlaps.append(max((overlap_f1(q, t) for q in quotes for t in targets), default=0.0))
    if not exact:
        return {"n_with_gold_evidence": 0, "exact_match": None, "overlap_f1": None}
    return {
        "n_with_gold_evidence": len(exact),
        "exact_match": sum(exact) / len(exact),
        "overlap_f1": sum(overlaps) / len(overlaps),
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

def evaluate(predictions, golds):
    preds_by_id = {p["id"]: p for p in predictions}
    gold_ids = {g["id"] for g in golds}
    pred_labels = [valid_label((preds_by_id.get(g["id"]) or {}).get("label")) for g in golds]
    gold_labels = [g["label"] for g in golds]

    def subset(keep):
        idx = [i for i, g in enumerate(golds) if keep(g)]
        s = label_scores([gold_labels[i] for i in idx], [pred_labels[i] for i in idx])
        return {"n": s["n"], "macro_f1": s["macro_f1"], "accuracy": s["accuracy"], "invalid": s["invalid"]}

    pairs = sorted({(g["claim_language"], g["reference_language"]) for g in golds})
    present = [preds_by_id[g["id"]] for g in golds if g["id"] in preds_by_id]
    return {
        "labels": label_scores(gold_labels, pred_labels),
        "missing_predictions": sum(1 for g in golds if g["id"] not in preds_by_id),
        "parse_failures": sum(1 for p in present if p.get("parse_failure")),
        "extra_predictions": sum(1 for p in predictions if p["id"] not in gold_ids),
        "evidence": evidence_scores(golds, preds_by_id),
        "evidence_given_rate": _evidence_given_rate(present),
        "cost": cost_scores(present),
        "by_language_pair": {
            f"{c}->{r}": subset(lambda g, c=c, r=r: (g["claim_language"], g["reference_language"]) == (c, r))
            for c, r in pairs
        },
        "same_vs_cross": {
            "same-language": subset(lambda g: g["claim_language"] == g["reference_language"]),
            "cross-lingual": subset(lambda g: g["claim_language"] != g["reference_language"]),
        },
    }


def _evidence_given_rate(predictions):
    """Share of entailment/contradiction predictions that include evidence."""
    needing = [p for p in predictions if valid_label(p.get("label")) in (0, 2)]
    if not needing:
        return None
    return sum(1 for p in needing if pred_passages(p)) / len(needing)


def format_report(r):
    f = lambda x: "n/a" if x is None else f"{x:.3f}"  # noqa: E731
    lab = r["labels"]
    lines = [
        f"Cases: {lab['n']}   missing predictions: {r['missing_predictions']}   "
        f"parse failures: {r['parse_failures']}   invalid labels (incl. missing): {lab['invalid']}",
        f"Macro-F1: {f(lab['macro_f1'])}   accuracy: {f(lab['accuracy'])}",
        "",
        "label          precision  recall  f1     support",
    ]
    for name, s in lab["per_class"].items():
        lines.append(f"{name:<14} {s['precision']:.3f}      {s['recall']:.3f}   {s['f1']:.3f}  {s['support']}")
    lines += ["", "confusion (rows gold, columns predicted):",
              "               " + "  ".join(f"{c[:7]:>7}" for c in list(LABEL_NAMES.values()) + [INVALID])]
    for g, row in lab["confusion"].items():
        lines.append(f"{g:<14} " + "  ".join(f"{v:>7}" for v in row.values()))
    ev, cost = r["evidence"], r["cost"]
    lines += [
        "",
        f"Evidence: {ev['n_with_gold_evidence']} cases with gold evidence; exact match {f(ev['exact_match'])}; "
        f"overlap F1 {f(ev['overlap_f1'])}; evidence given for entail/contra predictions {f(r['evidence_given_rate'])}",
        f"Input tokens: sum {cost['input_tokens_sum']}, mean {f(cost['input_tokens_mean'])}   "
        f"Output tokens: sum {cost['output_tokens_sum']}, mean {f(cost['output_tokens_mean'])}",
        f"Time ms: mean {f(cost['time_ms_mean'])}, p95 {cost['time_ms_p95']}",
        "",
        "group            n    macro_f1  accuracy  invalid",
    ]
    for name, s in list(r["same_vs_cross"].items()) + list(r["by_language_pair"].items()):
        lines.append(f"{name:<16} {s['n']:<4} {s['macro_f1']:.3f}     {s['accuracy']:.3f}     {s['invalid']}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Score predictions against gold labels.")
    parser.add_argument("predictions")
    parser.add_argument("gold")
    parser.add_argument("--json", help="also write the full result as JSON")
    args = parser.parse_args()
    result = evaluate(load_jsonl(args.predictions), load_jsonl(args.gold))
    print(format_report(result))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)


if __name__ == "__main__":
    main()
