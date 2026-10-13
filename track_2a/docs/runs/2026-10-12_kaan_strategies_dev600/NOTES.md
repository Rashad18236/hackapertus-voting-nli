### Strategies on dev: cross-language tournament, negation check, claim decomposition (one interleaved run, 600 cases)

**Command** (from `track_2a/`): `EMBED_MODEL_DIR=models/multilingual-e5-small MT_MODEL_DIR=models/m2m100_418M-ct2
python3 scripts/paired_run.py --cases data/dev/cases.jsonl --data-dir output/data_dev --out-dir
docs/runs/2026-10-12_kaan_strategies_dev600 --min-interval 2 --arm '{"name":"base"}' --arm '{"name":"xlang",
"strategy_a":"xlang","strategy_b":"xlang"}' --arm '{"name":"negation","strategy_a":"negation","strategy_b":"negation"}'
--arm '{"name":"decompose","strategy_a":"decompose","strategy_b":"decompose"}'`; 13:13 to 16:22 UTC, four arms
rotating, `swiss-ai/apertus-v1.5-8b` on Public AI. 600 responses per arm, 0 HTTP 429, 0 retries; one xlang call
(row 980 A) failed to connect and that case was answered the normal way, as designed. Scores: the starter's
`evaluate.py` at `559b598` (`official_score.txt` per arm); tables and offline rules: `scripts/strategy_analysis.py`
(`analysis.json`).

| | base | xlang | negation | decompose |
|---|---|---|---|---|
| Task A Macro-F1 (right of 300) | 0.9833 (295) | 0.9799 (294) | **0.9867** (296) | 0.9632 (289) |
| Task A evidence | 0.9851 | 0.9801 | **0.9900** | 0.9652 |
| Task B Macro-F1 (right of 300) | 0.9666 (290) | **0.9699** (291) | 0.9597 (288) | 0.9370 (281) |
| Calls per case A / B | 1.0 / 1.0 | 1.70 / 1.76 | 2.99 / 3.0 | 1.72 / 1.73 |
| Mean input tokens A / B | 1,238 / 1,231 | 2,060 / 2,106 | 2,642 / 2,636 | 1,861 / 1,842 |
| Mean local time A / B (ms) | 39 / 2 | 2,205 / 2,080 | 58 / 6 | 25 / 51 |
| Flips A (wrong→right / right→wrong) | – | 0 / 1 | 1 / 0 | 0 / 6 |
| Flips B | – | 2 / 1 | 0 / 2 | 0 / 9 |
| REF SCORE estimate (base = best team) | 0.984 | 0.774 | 0.833 | 0.858 |

Local time = case time minus the model's time (what the organisers' T counts); the tournament's is the local
translation (mean 3.2 s per translated case).

**Offline rules** (from the saved sub-answers, no new calls): xlang "agree else neutral" 0.937 / 0.915, "side S
only" 0.960 / 0.954, "side C only" 0.956 / 0.927 (A / B), all below what ran. Negation "consistent else neutral"
0.932 / 0.946. Decompose "majority of parts" 0.980 / 0.960 (better than "any part contradicted", still below base).

**Negation consistency as an error detector.** Task B: all 10 of base's wrong answers are among the 23 cases
where the claim's and the negation's labels are inconsistent (13 of those 23 are right); none among the 275
consistent. Task A: 4 of the 5 wrong answers among 19 inconsistent cases. The check finds errors but its rule
does not fix them.
