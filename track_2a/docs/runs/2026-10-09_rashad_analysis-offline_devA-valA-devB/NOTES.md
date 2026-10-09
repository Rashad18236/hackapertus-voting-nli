### Offline analyses B1–B6 (session 9, phase B)

`scripts/analysis_offline.py`, run at commit `dbb30fa` with `EMBED_MODEL_DIR=models/multilingual-e5-small`;
no model calls. `analysis.json` holds every number, `per_case.jsonl` the B2 and B6 rows. The write-up is
`docs/analysis_offline.md`.

B5 and B6 rebuild the paragraphs sent with today's code; session 8's gate G1 showed that the code sends the
same requests for these cases as when E5 and E6 ran.
