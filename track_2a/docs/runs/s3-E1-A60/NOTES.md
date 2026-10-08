### 2026-10-08, session 3, E1: answer format by prompt vs json_schema (task A, 60-case sample, paired)

- Command: `python3 scripts/paired_run.py --cases output/devA60/cases.jsonl --data-dir output/data_dev --out-dir docs/runs/s3-E1-A60 --arm '{"name": "fulldoc-prompt"}' --arm '{"name": "fulldoc-schema", "schema_a": true, "max_tokens_a": 128}'` (the control used the then-default settings: prompt format, 64 tokens), 11:47 to 12:04 UTC. Scored per arm with the official scorer.
- Unparseable answers: prompt 3, schema 0. Failed calls (HTTP 504 through the retry): prompt 2, schema 1. Order balanced (30 first each).
- On the 58 cases where both arms got an answer: prompt 0.846, schema 0.863.
- Schema mean time 7.0 s against 10.2 s; input tokens equal (same prompt).
- The control produced far fewer prose answers than in session 2 (3/60 against 43 %): endpoint drift, which is why comparisons are now paired.
- **Kept:** json_schema with max_tokens 128 is now the task A default (`Settings.schema_a=True`, `max_tokens_a=128`).
- Session 3 paired runs (`scripts/paired_run.py`): both configurations on the same case back to back, alternating order, warm booklet cache, run on the host with the entrypoint's code (`cli.predict`). Rows of one comparison are only comparable with each other.
