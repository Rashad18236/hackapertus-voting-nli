### 2026-10-08, `16ec6af`, v1-json (pre-contract)

- Our own input format and our own `evaluate.py`, before the official contract was known. Kept for comparison; not comparable in every detail (failed cases had no label, not label 1).
- Command: `python3 -m src.cli data/dev_inputs.jsonl docs/runs/baseline-v0_dev_predictions.jsonl --raw docs/runs/baseline-v0_dev_raw_answers.jsonl`, run on the host from a sandbox (not in Docker), 04:56 to 05:17 UTC.
- Score: `python3 -m src.evaluate docs/runs/baseline-v0_dev_predictions.jsonl data/dev_gold.jsonl` at that commit (full output in `docs/runs/baseline-v0/baseline-v0_dev_scores.json`). scikit-learn's `f1_score(average="macro")` gives the same 0.202.
- 17 of 300 cases have no label and count as wrong: 8 parse failures (5 answers cut off at the 400-token limit while quoting) and 9 calls that failed with HTTP 504 from the Public AI gateway after about 61 s.
- Mean input tokens include the 9 failed calls as 0 tokens; over the 291 completed calls the mean is 1998. Mean time includes the 9 failed calls at about 61 s each; without them it is 2355 ms.
- Accuracy 0.310. Per-class F1: entailment 0.000, neutral 0.000, contradiction 0.606. The model never answered 0.
- Evidence was kept for 34.6 % of entailment/contradiction predictions; the rest were empty or not verbatim.
- Files: moved into `docs/runs/baseline-v0/` (same file names) on 2026-10-08, when every run got its own folder.
