### Phase D on val: A-current, L1 and L2 on all 580 val task A cases (one interleaved run)

**Command** (from `track_2a/`; task A code as in `86791db`): `EMBED_MODEL_DIR=models/multilingual-e5-small
python3 scripts/paired_run.py --cases data/val/cases.jsonl --data-dir output/data_dev --out-dir
docs/runs/2026-10-09_rashad_label-errors-confirm_valA580 --min-interval 1.0 --arm '{"name": "A-current"}' --arm
'{"name": "L1", "label_rule_a": true}' --arm '{"name": "L2", "second_look_a": true}'`; 19:28:06 to 20:16:40
UTC, three arms rotating. L2 failed its rule on dev and runs here for information only.

| | A-current | L1 | L2 |
|---|---|---|---|
| Macro-F1 (all 580 = same backend) | 0.950 | **0.961** (+0.0104) | 0.954 (+0.0034) |
| Recall E / N / C | 0.984 / 1.000 / 0.877 | 0.979 / 1.000 / 0.910 | 0.984 / 1.000 / 0.886 |
| Gold contradictions answered neutral | 21 | 14 | 19 |
| Evidence score (starter) | 0.943 (378/401) | 0.958 (384/401) | 0.948 (380/401) |
| Mean input tokens (p95) | 1,178 (2,079) | 1,206 (2,107), +2.4 % | 1,217 (2,101), +3.3 % |
| Model calls | 580 | 580 | 619 |
| Mean / p95 time (ms) | 1,199 / 2,218 | 1,892 / 3,013 | 1,748 / 3,078 |
| Gateway cache hits | 386 | 2 | 195 |

All 1,779 answers came from one backend (`...dd237840`, blablador), so all cases are same-backend cases.
As on dev, L2's first call equals A-current's request, so one of the two is usually a gateway cache hit; the
time differences mean little.

**Flips.** L1: 7 wrong → right (rows 1162, 1215, 1237, 1325, 1360, 1389, 1452), 1 right → wrong (row 17).
L2: 2 wrong → right (rows 1053, 1162), none right → wrong; 199 first answers were neutral, 39 reached the
threshold (30 of them gold neutral, all kept), 2 changed; 22,445 extra input tokens.

**Rules (fixed):**

- L1: +0.01 on dev (+0.0137) and +0.005 on val (**+0.0104**), neutral recall ≥ 0.98 on both (1.000 and
  **1.000**): **passes. The task A default becomes `--label-rule-a`** (prompt `A-v4-section-route-L1`).
- L2: failed on dev (+0.0102 < +0.015); on val +0.0034 with +3.3 % input tokens. Stays off; an option.
