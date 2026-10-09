### Phase C on dev: B-current, B-cut and B-para on all 300 dev task B cases (one interleaved run)

**Command** (from `track_2a/`, code `dbb30fa`): `EMBED_MODEL_DIR=models/multilingual-e5-small python3
scripts/paired_run.py --cases output/devB/cases.jsonl --data-dir output/data_dev --out-dir
docs/runs/2026-10-09_rashad_taskb-context_devB300 --min-interval 1.0 --arm '{"name": "B-current"}' --arm
'{"name": "B-cut", "context_b": "cut"}' --arm '{"name": "B-para", "context_b": "para"}'`; 17:53:20 to 18:20:24
UTC; the three arms answer each case back to back, the order rotating (three arms: plain rotation). Model
`swiss-ai/apertus-v1.5-8b` on Public AI. Progress log: `paired_run.log`; numbers: `analysis.json`
(`scripts/interleaved_analysis.py`), each arm's `official_score.json` (the starter's scorer).

| | B-current | B-cut | B-para |
|---|---|---|---|
| Macro-F1 (all 300) | 0.967 | 0.967 | 0.963 |
| F1 E / N / C | 0.985 / 0.963 / 0.951 | 0.985 / 0.963 / 0.951 | 0.985 / 0.961 / 0.942 |
| Mean input tokens (p95) | 1,994 (4,463) | 1,231 (2,182) | 1,375 (2,336) |
| Change against B-current | – | **−38.3 %** | −31.0 % |
| Mean output tokens | 8.5 | 8.4 | 14.0 |
| Mean / p95 time (ms) | 1,252 / 2,217 | 1,864 / 6,325 | 2,118 / 5,444 |
| Unreadable answers | 3 | 0 | 0 |
| Gateway cache hits | 66 | 129 | 0 |

**Backends.** All 900 answers came from one backend (system_fingerprint `...dd237840`, blablador), so
"same-backend cases" are all 300 cases and both views of the rule give the same numbers.

**Long and short references.** The 195 references of at most 8,000 characters are sent unchanged by B-cut:
the same request as B-current, and the same label in all 195 (many from the gateway's cache, which explains
B-cut's 129 cache hits). On the 105 long references (99 of them gold neutral; `docs/analysis_offline.md`, B4):
B-current 97 right, B-cut 97 right (3 right → wrong, 3 wrong → right; B-current's 3 unreadable answers were
on long references), B-para 104 right. B-para loses on short references instead (185 of 195 right against
193: 8 contradictions answered neutral), so B-para's total is lower.

**Time.** B-cut's long cases took 3.6 s on average against 1.5 s for B-current: the reference's paragraphs
are embedded with e5 on the CPU for each new reference (and the first long case loads the model). Two gate runs
of the fake model (`scripts/prompt_snapshot.py`, both CPU-heavy) ran on the same machine between about 17:54
and 18:13, so these times are inflated by an unknown amount; the val run measures them without that load.
Time is not part of phase C's rule.

**Rule (Rashad's, fixed):** B-cut passes if its Macro-F1 is at most 0.01 below current (all cases and
same-backend cases) and its input tokens are at least 25 % lower. B-para replaces it only if it beats B-cut by
at least 0.02.

- B-cut: 0.9666 against 0.9666 (difference 0.000, all and same-backend), input tokens −38.3 %: **passes**.
- B-para: 0.9628, 0.004 below B-cut: does not replace B-cut.
- Next: confirm B-cut against B-current on the task B cases of all 580 val rows
  (`2026-10-09_rashad_taskb-cut-confirm_valB580`); only if the same rule holds there does the default change.
