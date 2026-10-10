### Phase D on dev: A-current, L1 and L2 on all 300 dev task A cases (one interleaved run)

**Command** (from `track_2a/`; `src/` as in `86791db`): `EMBED_MODEL_DIR=models/multilingual-e5-small python3
scripts/paired_run.py --cases output/devA/cases.jsonl --data-dir output/data_dev --out-dir
docs/runs/2026-10-09_rashad_label-errors_devA300 --min-interval 1.0 --arm '{"name": "A-current"}' --arm
'{"name": "L1", "label_rule_a": true}' --arm '{"name": "L2", "second_look_a": true}'`. Started 18:56:29 UTC,
stopped after 2 cases to let the phase C val run finish first (one model run at a time), continued with
`--resume` at 19:00 and finished at 19:27:21 UTC. Three arms: the order rotates (A-current, L1, L2 / L1, L2,
A-current / L2, A-current, L1). Model `swiss-ai/apertus-v1.5-8b` on Public AI. Progress log:
`paired_run.log`; numbers: `analysis.json` (`scripts/interleaved_analysis.py --task A`) and each arm's
`official_score.json` (the starter's scorer).

| | A-current | L1 | L2 |
|---|---|---|---|
| Macro-F1 (all 300 = same backend) | 0.966 | **0.980** | 0.976 |
| F1 E / N / C | 0.985 / 0.966 / 0.947 | 0.980 / 0.990 / 0.969 | 0.985 / 0.980 / 0.964 |
| Recall E / N / C | 0.990 / 1.000 / 0.909 | 0.980 / 1.000 / 0.960 | 0.990 / 1.000 / 0.939 |
| Gold contradictions answered neutral | 7 | 2 | 4 |
| Evidence score (starter) | 0.955 (192/201) | 0.980 (197/201) | 0.970 (195/201) |
| Mean input tokens (p95) | 1,210 (2,104) | 1,238 (2,132), +2.3 % | 1,244 (2,107), +2.8 % |
| Model calls | 300 | 300 | 317 |
| Mean / p95 time (ms) | 1,453 / 2,760 | 1,986 / 3,135 | 1,923 / 3,654 |
| Gateway cache hits | 200 | 1 | 101 |

**Backends and cache.** All 917 answers came from one backend (`...dd237840`, blablador), so all cases are
same-backend cases. L2's first call is the same request as A-current's, so whichever of the two ran second got
the gateway's cached answer (A-current ran after L2 in two of the three orders: 200 hits; L2 after A-current
in one: 101). This makes A-current's time look shorter than a model call; the time differences in this run say
little.

**Flips.** L1 against A-current: 5 wrong → right (4 contradictions that A-current called neutral, 1 it
called entailment: rows 1014, 1117, 1230, 1384, 1468) and 1 right → wrong (row 232, an entailment L1 calls a
contradiction). L2 against A-current: 3 wrong → right (rows 1014, 1016, 1384), none right → wrong.

**L2's second looks.** 106 first answers were neutral; 17 reached the threshold 0.845 and got a second call
(10,337 extra input tokens, +34 per case on average). Of the 11 that were gold neutral, all 11 stayed neutral;
of the 6 wrong neutral answers, 3 became contradictions (right) and 3 stayed neutral.

**Rules (fixed):**

- L1: Macro-F1 +0.01 on dev and +0.005 on val, and neutral recall ≥ 0.98 on both. Dev: **+0.0137**, neutral
  recall **1.000**: passes on dev; confirmation on all 580 val cases follows
  (`2026-10-09_rashad_label-errors-confirm_valA580`).
- L2: Macro-F1 +0.015 on both and mean input tokens up by at most 5 %. Dev: +0.0102 (tokens +2.8 %): **fails
  on dev**; reported as an option (gain and cost above), default unchanged. It runs on val as a third arm for
  information only.
