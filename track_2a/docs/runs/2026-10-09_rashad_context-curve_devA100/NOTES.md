### E1, the context curve: how much booklet text Apertus needs (100 dev task A cases, one interleaved run)

Session 9, phase E1, **information only: no default changed**. The challenge's central experiment ("full
document → Apertus" against "selected context → Apertus") as one curve, all arms on the same cases back to
back.

**Command** (from `track_2a/`, code `5e1d864`): `EMBED_MODEL_DIR=models/multilingual-e5-small python3
scripts/paired_run.py --cases output/devA100/cases.jsonl --data-dir output/data_dev --out-dir
docs/runs/2026-10-09_rashad_context-curve_devA100 --min-interval 1.0 --arm '{"name": "full", "context_a":
"full"}' --arm '{"name": "embed-e5-small", "context_a": "embed-e5-small"}' --arm '{"name": "section-route",
"label_rule_a": true}' --arm '{"name": "section-k4", "section_top_k_a": 4, "label_rule_a": true}' --arm
'{"name": "section-k2", "section_top_k_a": 2, "label_rule_a": true}' --arm '{"name": "section-k1",
"section_top_k_a": 1, "label_rule_a": true}'`; 20:17:15 to 20:50:28 UTC; six arms in a balanced Latin square.
Cases: 100 dev task A cases sampled with `make_splits.py`'s round-robin over (label, claim language, booklet
language), seed 42 (`scripts/make_dev_sample.py`; 36 entailment, 36 neutral, 28 contradiction; rows in
`sample_rows.json`). The routed arms use L1 (`A-v4-section-route-L1`), which became the default after phase D.

| Context (what Apertus reads) | Macro-F1 | Evidence | Input tokens, mean (p95) | Mean / p95 time |
|---|---|---|---|---|
| whole booklet (`full`) | 0.858 | 0.422 | 37,586 (78,489) | 7.3 / 17.6 s |
| 8 chunks most similar to the claim (`embed-e5-small`) | 0.898 | 0.656 | 1,885 (2,482) | 4.9 / 15.3 s |
| the routed part (`section-route`, default) | **0.989** | **1.000** | 1,248 (1,986) | 1.9 / 3.0 s |
| the routed part's 4 most similar paragraphs | 0.979 | 0.984 | 804 (1,002) | 2.0 / 3.2 s |
| … 2 most similar paragraphs | 0.940 | 0.922 | 614 (822) | 1.8 / 2.6 s |
| … 1 most similar paragraph | 0.769 | 0.641 | 510 (680) | 1.9 / 2.9 s |

All 600 answers came from one backend (`...dd237840`, blablador); 6 were gateway cache hits. No failed call,
no unreadable answer (one `section-k1` contradiction cited no valid paragraph).

**Reading.** More text is not better: the whole booklet (30 times the tokens) is 0.13 below section-route, and
its errors are mostly contradictions and neutrals confused. The right part of the vote matters more than
similarity: the 8 most similar chunks of the booklet (embed-e5-small) score 0.09 below the routed part with
more tokens. Inside the routed part, 4 paragraphs keep most of the result (−0.011 at 64 % of the tokens),
2 lose 0.05, and 1 loses 0.22 (half the contradictions become neutral: the deciding detail is not in the one
paragraph). The 100-case sample is small (one case moves Macro-F1 by about 0.01); the curve's shape, not the
third decimal, is the result.
