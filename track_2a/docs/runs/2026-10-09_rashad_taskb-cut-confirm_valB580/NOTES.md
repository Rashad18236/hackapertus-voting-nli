### Phase C on val: B-cut confirmed against B-current on the task B cases of all 580 val rows

**Command** (from `track_2a/`, code `86791db`; `src/` as in `dbb30fa` for task B): `EMBED_MODEL_DIR=models/multilingual-e5-small
python3 scripts/paired_run.py --cases output/valB/cases.jsonl --data-dir output/data_dev --out-dir
docs/runs/2026-10-09_rashad_taskb-cut-confirm_valB580 --min-interval 1.0 --arm '{"name": "B-current"}' --arm
'{"name": "B-cut", "context_b": "cut"}'`; 18:26:26 to 18:59:46 UTC. The cases are the starter's task B lines of
the 580 rows in `data/val/rows.json` (`scripts/make_val_b.py`, written to the git-ignored `output/valB/`).

**Interruption.** The run was started as a background job with the default 30-minute limit and was stopped
at 18:56 UTC after case 517 (B-current) and 516 (B-cut). It was continued with `--resume` at 18:57 UTC (same
command plus `--resume`): case 517 ran only its B-cut arm then, about a minute after its B-current arm; the
other 63 cases ran both arms back to back as before. `paired_run.log` holds both parts.

| | B-current | B-cut |
|---|---|---|
| Macro-F1 (all 580 = same backend) | 0.957 | **0.961** |
| F1 E / N / C | 0.984 / 0.945 / 0.942 | 0.984 / 0.951 / 0.947 |
| Mean input tokens (p95) | 1,957 (4,652) | **1,230** (2,200), **−37.1 %** |
| Mean / p95 time (ms) | 1,481 / 2,708 | 1,800 / 3,774 |
| Unreadable answers | 2 | 1 |
| Labels that differ | – | 6 (2 right → wrong, 4 wrong → right) |

All 1,160 answers came from one backend (`...dd237840`, blablador); 384 calls were gateway cache hits
(mostly the identical requests of the 384 short references, which B-cut sends unchanged: same label in all
384). On the 196 long references (179 gold neutral), B-current had 177 right and B-cut 179.

**Time.** B-cut costs time where it saves tokens: on the long references 2.8 s per case against 1.9 s
(embedding the reference's paragraphs with e5 on the CPU), +0.3 s per case over all 580. Phase D's gate
runs (CPU-heavy) did not overlap this run.

**Rule (fixed):** B-cut passes if its Macro-F1 is at most 0.01 below current (all cases and same-backend
cases) and its input tokens are at least 25 % lower; the same rule must hold on val.

- Dev (`2026-10-09_rashad_taskb-context_devB300`): 0.967 against 0.967, −38.3 % tokens: passes.
- Val (this run): 0.961 against 0.957 (+0.004, all cases = same-backend cases), −37.1 % tokens: **passes**.
- So **the task B default becomes `--context-b cut`** (commit after this run).
