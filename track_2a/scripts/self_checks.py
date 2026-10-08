"""Self-checks for the splits and the scorers. Writes docs/self_checks.md.

Run from track_2a/:

    python3 scripts/self_checks.py --starter DIR [--run PREDICTIONS.jsonl ...]

DIR is a checkout of the starter repository with its environment installed
(`uv sync --locked`); its evaluate.py is the official scorer and is run
unchanged. --run adds real prediction files to the scorer comparison.
Exits with status 1 if any check fails. Needs scikit-learn and pandas
(requirements-dev.txt).
"""

import argparse
import json
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
from sklearn.metrics import f1_score  # noqa: E402

from src import evaluate as ev  # noqa: E402

DATA = ROOT / "data"
NAMES = {0: "entailment", 1: "neutral", 2: "contradiction"}
results = []  # (name, passed, detail)


def check(name, passed, detail):
    results.append((name, bool(passed), detail))


def write_predictions(path, labels_by_id):
    with open(path, "w", encoding="utf-8") as f:
        for case_id, label in labels_by_id.items():
            pred = {"id": case_id, "evidence": [],
                    "metrics": {"input_tokens": 0, "output_tokens": 0, "inference_time_ms": 0}}
            if label is not None:  # None -> deliberately invalid response
                pred.update(label=label, label_name=NAMES[label])
            f.write(json.dumps(pred) + "\n")


def starter_scores(starter, predictions, split):
    """Run the starter's evaluate.py unchanged; return {task: macro_f1}."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "score.json"
        subprocess.run(["uv", "run", "--no-sync", "python", "evaluate.py",
                        "--predictions", str(predictions), "--expected", str(DATA / split / "expected-labels.jsonl"),
                        "--cases", str(DATA / split / "cases.jsonl"), "--json", str(out)],
                       cwd=starter, check=True, capture_output=True)
        report = json.loads(out.read_text(encoding="utf-8"))
    return {task: r["macro_f1"] for task, r in report["tasks"].items()}


def our_scores(predictions, split):
    cases = {c["id"]: c for c in ev.load_jsonl(DATA / split / "cases.jsonl")}
    r = ev.evaluate(ev.load_jsonl(predictions), ev.load_jsonl(DATA / split / "expected-labels.jsonl"), cases)
    return {task: t["labels"]["macro_f1"] for task, t in r["tasks"].items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--starter", type=Path, required=True)
    parser.add_argument("--run", type=Path, action="append", default=[], help="real dev predictions to compare")
    args = parser.parse_args()

    dev_cases = ev.load_jsonl(DATA / "dev/cases.jsonl")
    dev_expected = ev.load_jsonl(DATA / "dev/expected-labels.jsonl")
    test_cases = ev.load_jsonl(DATA / "test/cases.jsonl")
    test_expected = ev.load_jsonl(DATA / "test/expected-labels.jsonl")
    example_cases = ev.load_jsonl(ROOT / "examples/cases.jsonl")
    gold = {e["id"]: e["label"] for e in dev_expected}
    gold_b = [e["label"] for e in dev_expected if e["id"].endswith("-B")]

    # 1. Unit tests
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), top_level_dir=str(ROOT))
    with open("/dev/null", "w") as devnull:
        outcome = unittest.TextTestRunner(stream=devnull, verbosity=0).run(suite)
    check("unit tests pass (tests/: evaluate, parser, CLI)", outcome.wasSuccessful(),
          f"{outcome.testsRun} tests, {len(outcome.failures)} failures, {len(outcome.errors)} errors")

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        rng = random.Random(42)
        dummies = {
            "always neutral": {i: 1 for i in gold},
            "random labels (seed 42)": {i: rng.choice([0, 1, 2]) for i in gold},
            "gold": dict(gold),
            "random with 25 % invalid (seed 42)": {i: rng.choice([0, 1, 2, None]) for i in gold},
        }
        scores = {}
        for name, labels in dummies.items():
            path = tmp / (name.replace(" ", "_") + ".jsonl")
            write_predictions(path, labels)
            scores[name] = (our_scores(path, "dev"), starter_scores(args.starter, path, "dev"))
        for path in args.run:
            scores[f"run {path.name}"] = (our_scores(path, "dev"), starter_scores(args.starter, path, "dev"))

    # 2. Our Macro-F1 equals the starter's (official) Macro-F1, per task, on every file.
    worst = max(abs(ours[t] - theirs[t]) for ours, theirs in scores.values() for t in theirs)
    detail = "; ".join(f"{name}: " + ", ".join(f"{t} {theirs[t]:.4f}/{ours[t]:.4f}" for t in sorted(theirs))
                       for name, (ours, theirs) in scores.items())
    check("our evaluate.py gives the starter's Macro-F1 (starter/ours, per task)", worst < 1e-9,
          f"max abs difference {worst:.1e}. {detail}")

    # 3. Independent check against scikit-learn directly (task B, invalid -> -1).
    rng = random.Random(7)
    diffs = []
    for _ in range(20):
        preds = [rng.choice([0, 1, 2, None]) for _ in gold_b]
        ours = ev.label_scores(gold_b, preds)["macro_f1"]
        sk = f1_score(gold_b, [-1 if p is None else p for p in preds], labels=[0, 1, 2],
                      average="macro", zero_division=0)
        diffs.append(abs(ours - sk))
    check("Macro-F1 equals sklearn f1_score(average='macro')", max(diffs) < 1e-12,
          f"20 random task B prediction sets with invalid entries; max abs difference {max(diffs):.1e}")

    # 4. Always neutral: expected from label counts, per task.
    n, n1 = len(gold_b), gold_b.count(1)
    expected_value = (2 * n1 / (n + n1)) / 3
    actual = scores["always neutral"][1]
    check("always-neutral dummy matches the value expected from label counts",
          all(abs(actual[t] - expected_value) < 1e-12 for t in actual),
          f"per task N={n}, neutral={n1}; expected (2*{n1}/({n}+{n1}))/3 = {expected_value:.4f}; "
          f"official scorer: A {actual['A']:.4f}, B {actual['B']:.4f}")

    # 5. Random labels near 1/3.
    rand = scores["random labels (seed 42)"][1]
    check("random-label dummy scores near 0.33", all(0.27 <= v <= 0.40 for v in rand.values()),
          f"official scorer: A {rand['A']:.4f}, B {rand['B']:.4f} (accepted 0.27-0.40, about 2 standard errors)")

    # 6. Gold against itself.
    g = scores["gold"]
    check("gold scored against itself gives 1.0 (both scorers)",
          all(v == 1.0 for side in g for v in side.values()), f"ours {g[0]}, starter {g[1]}")

    # 7. No leakage.
    for name, rows in (("dev", dev_cases), ("test", test_cases), ("examples", example_cases)):
        leaked = [r["id"] for r in rows if "label" in r or "label_name" in r or "entailment_label" in r]
        check(f"{name} cases contain no label fields", not leaked, f"{len(rows)} requests checked")
    check("cases and expected labels have the same ids, per split",
          [r["id"] for r in dev_cases] == [e["id"] for e in dev_expected]
          and [r["id"] for r in test_cases] == [e["id"] for e in test_expected], "same ids, same order")

    raw = pd.read_parquet(DATA / "raw/v1.1.parquet")
    row_of = lambda case_id: int(case_id.split("-row-")[1].rsplit("-", 1)[0])  # noqa: E731
    booklets = lambda rows: {raw.iloc[row_of(r["id"])]["booklet_publish_date"] for r in rows}  # noqa: E731
    dev_rows, test_rows = {row_of(r["id"]) for r in dev_cases}, {row_of(r["id"]) for r in test_cases}
    check("no dev id or row appears in test", not ({r["id"] for r in dev_cases} & {r["id"] for r in test_cases})
          and not (dev_rows & test_rows), f"dev rows {len(dev_rows)}, test rows {len(test_rows)}")
    check("no dev booklet (voting date) appears in test", not (booklets(dev_cases) & booklets(test_cases)),
          f"dev booklets {len(booklets(dev_cases))}, test booklets {sorted(booklets(test_cases))}")
    check("example cases (make run) come from dev rows, not test",
          {row_of(r["id"]) for r in example_cases} <= dev_rows, f"{[r['id'] for r in example_cases]}")
    split = json.loads((DATA / "splits.json").read_text())
    check("dev and test files match data/splits.json",
          sorted(dev_rows) == split["dev_rows"] and sorted(test_rows) == split["test_rows"], "")

    lines = ["# Self-checks", "", "Generated by `scripts/self_checks.py`. The official scorer is the starter's "
             "`evaluate.py` (commit `559b598`), run unchanged.", "",
             "| Check | Result | Detail |", "|---|---|---|"]
    lines += [f"| {name} | {'PASS' if ok else 'FAIL'} | {detail} |" for name, ok, detail in results]
    (ROOT / "docs/self_checks.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")
    sys.exit(0 if all(ok for _, ok, _ in results) else 1)


if __name__ == "__main__":
    main()
