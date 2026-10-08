Task A, all 300 dev cases, context variant embed-e5-small (prompt A-v3-excerpts, top 8 chunks of <= 1,000 chars by intfloat/multilingual-e5-small, revision 614241f), max_tokens 64.
Run 2026-10-08 13:46-14:04 UTC via `make compare VARIANTS=embed-e5-small CASES=output/devA/cases.jsonl BOOKLETS=output/booklets_dev`, from the uncommitted session 3 working tree (parent commit 3fa8f58), Docker linux/amd64 emulated on an Apple M4 Pro.
A first attempt at 13:13 was stopped after 27 cases: every call failed with a connection error (endpoint outage, confirmed with a direct call); its log is not kept as a result.
Scored with the starter's evaluate.py (commit 559b598, unchanged) -> official_score.*, and src/evaluate.py -> breakdown.*.
