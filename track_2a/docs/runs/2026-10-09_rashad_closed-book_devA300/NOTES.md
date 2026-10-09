### E2, closed book: the claim and the vote's name only (300 dev task A cases, one interleaved run)

Session 9, phase E2, **information only**. How much does Apertus answer from what it already knows about a
ballot, without the booklet? The official reference point is always the supplied source, so closed book is
not a solution; it measures how much the context matters.

**Command** (from `track_2a/`): `EMBED_MODEL_DIR=models/multilingual-e5-small python3 scripts/paired_run.py
--cases output/devA/cases.jsonl --data-dir output/data_dev --out-dir docs/runs/2026-10-09_rashad_closed-book_devA300
--min-interval 1.0 --arm '{"name": "section-route", "label_rule_a": true}' --arm '{"name": "closed-book",
"context_a": "closed-book"}'`; 20:50:37 to 21:09:40 UTC, order alternating. The closed-book prompt
(`A-v0-closed-book`, `src/nli.py`) gives VOTE and CLAIM and asks whether "the booklet" supports, does not deal
with, or contradicts the claim.

| | section-route (default) | closed book |
|---|---|---|
| Macro-F1 | **0.980** | 0.435 |
| Confusion rows gold E / N / C (pred E/N/C) | 100/0/2, 0/99/0, 2/2/95 | 16/85/1, 0/89/10, 0/62/37 |
| Input tokens, mean | 1,238 | 223 |
| Mean / p95 time | 2.3 / 4.2 s | 1.5 / 2.1 s |

All 600 answers from one backend (`...dd237840`); no cache hits. Without the booklet Apertus answers neutral in
236 of 300 cases (the closed-book status "no valid pages for label 0/2" on the other 64 only means it cited no
page, which it cannot); it confirms 16 of 102 true claims and refutes 37 of 99 false ones. **The booklet text
supplies almost all of the result**; Apertus's own knowledge of these ballots is thin, which also means the
task is not solved by memorised facts.
