"""Self-checks for the splits and src/evaluate.py. Writes docs/self_checks.md.

Run from track_2a/:  python3 scripts/self_checks.py
Exits with status 1 if any check fails. Needs scikit-learn (requirements-dev.txt)
only for the comparison check.
"""

import json
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sklearn.metrics import f1_score  # noqa: E402

from src import evaluate as ev  # noqa: E402

DATA = ROOT / "data"
results = []  # (name, passed, detail)


def check(name, passed, detail):
    results.append((name, bool(passed), detail))


def dummy(golds, labels):
    return [{"id": g["id"], "label": lab, "evidence": []} for g, lab in zip(golds, labels)]


def main():
    dev_gold = ev.load_jsonl(DATA / "dev_gold.jsonl")
    test_gold = ev.load_jsonl(DATA / "test_gold.jsonl")
    dev_inputs = ev.load_jsonl(DATA / "dev_inputs.jsonl")
    test_inputs = ev.load_jsonl(DATA / "test_inputs.jsonl")
    sample_inputs = ev.load_jsonl(DATA / "sample_beginner.jsonl")
    gold_labels = [g["label"] for g in dev_gold]

    # 1. Unit tests
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), top_level_dir=str(ROOT))
    outcome = unittest.TextTestRunner(stream=open("/dev/null", "w"), verbosity=0).run(suite)
    check("evaluate unit tests pass", outcome.wasSuccessful(),
          f"{outcome.testsRun} tests, {len(outcome.failures)} failures, {len(outcome.errors)} errors")

    # 2. Macro-F1 equals scikit-learn on the same data. Random predictions with
    #    some invalid ones; invalid -> -1 for sklearn, which counts it wrong
    #    for every class, matching our definition.
    rng = random.Random(42)
    diffs = []
    for _ in range(20):
        preds = [rng.choice([0, 1, 2, None]) for _ in gold_labels]
        ours = ev.evaluate(dummy(dev_gold, preds), dev_gold)["labels"]["macro_f1"]
        theirs = f1_score(gold_labels, [-1 if p is None else p for p in preds],
                          labels=[0, 1, 2], average="macro", zero_division=0)
        diffs.append(abs(ours - theirs))
    check("Macro-F1 equals sklearn f1_score(average='macro')", max(diffs) < 1e-12,
          f"20 random prediction sets on dev (25 % invalid on average); max abs difference {max(diffs):.2e}")

    # 3. Always neutral. Expected: neutral precision n1/N, recall 1,
    #    F1 = 2*n1/(N+n1); the other two F1 are 0; Macro-F1 = that / 3.
    n, n1 = len(gold_labels), gold_labels.count(1)
    expected = (2 * n1 / (n + n1)) / 3
    actual = ev.evaluate(dummy(dev_gold, [1] * n), dev_gold)["labels"]["macro_f1"]
    check("always-neutral dummy matches the value expected from label counts", abs(actual - expected) < 1e-12,
          f"N={n}, neutral={n1}; expected (2*{n1}/({n}+{n1}))/3 = {expected:.4f}; actual {actual:.4f}")

    # 4. Random labels score near 1/3.
    rng = random.Random(42)
    rand = ev.evaluate(dummy(dev_gold, [rng.choice([0, 1, 2]) for _ in gold_labels]), dev_gold)
    mf = rand["labels"]["macro_f1"]
    check("random-label dummy scores near 0.33", 0.27 <= mf <= 0.40,
          f"seed 42, uniform over 0/1/2: Macro-F1 {mf:.4f} (accepted range 0.27-0.40, about 2 standard errors for N={n})")

    # 5. Gold against itself.
    for name, golds in (("dev", dev_gold), ("test", test_gold)):
        r = ev.evaluate(dummy(golds, [g["label"] for g in golds]), golds)
        lab = r["labels"]
        all_one = (lab["macro_f1"] == 1.0 and lab["accuracy"] == 1.0
                   and all(v[k] == 1.0 for v in lab["per_class"].values() for k in ("precision", "recall", "f1"))
                   and all(s["macro_f1"] == 1.0 for s in list(r["by_language_pair"].values())
                           + list(r["same_vs_cross"].values())))
        check(f"{name} gold scored against itself gives 1.0", all_one,
              f"Macro-F1 {lab['macro_f1']}, accuracy {lab['accuracy']}, all per-class and per-group scores 1.0: "
              f"{all_one}. Evidence: {r['evidence']['n_with_gold_evidence']} cases with gold evidence "
              "(the dataset has none), so evidence scores are n/a")

    # 6. No leakage.
    for name, rows in (("dev", dev_inputs), ("test", test_inputs), ("sample", sample_inputs)):
        keys = {tuple(sorted(r)) for r in rows}
        check(f"{name} inputs contain only id, reference, claim", keys == {("claim", "id", "reference")},
              f"key sets found: {sorted(keys)}")
    dev_ids, test_ids = {g["id"] for g in dev_gold}, {g["id"] for g in test_gold}
    check("no dev gold id in test inputs and no test gold id in dev inputs",
          not (dev_ids & {r["id"] for r in test_inputs}) and not (test_ids & {r["id"] for r in dev_inputs}),
          "ids are prefixed dev-/test-; each split's ids appear only in its own inputs file")
    check("inputs and gold files have the same ids, one-to-one",
          [r["id"] for r in dev_inputs] == [g["id"] for g in dev_gold]
          and [r["id"] for r in test_inputs] == [g["id"] for g in test_gold], "same order, same ids")
    dev_booklets, test_booklets = {g["booklet"] for g in dev_gold}, {g["booklet"] for g in test_gold}
    check("no dev booklet appears in test", not (dev_booklets & test_booklets),
          f"dev booklets {len(dev_booklets)}, test booklets {sorted(test_booklets)}")
    pairs = lambda rows: {(r["claim"]["text"], r["reference"]["text"]) for r in rows}  # noqa: E731
    check("no (claim, reference) pair shared by dev and test", not (pairs(dev_inputs) & pairs(test_inputs)), "")
    test_claims = {r["claim"]["text"] for r in test_inputs}
    check("sample cases (make run default) are not test cases",
          not ({r["claim"]["text"] for r in sample_inputs} & test_claims), "")

    lines = ["# Self-checks", "", "Generated by `scripts/self_checks.py`.", "",
             "| Check | Result | Detail |", "|---|---|---|"]
    lines += [f"| {name} | {'PASS' if ok else 'FAIL'} | {detail} |" for name, ok, detail in results]
    (ROOT / "docs/self_checks.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")
    sys.exit(0 if all(ok for _, ok, _ in results) else 1)


if __name__ == "__main__":
    main()
