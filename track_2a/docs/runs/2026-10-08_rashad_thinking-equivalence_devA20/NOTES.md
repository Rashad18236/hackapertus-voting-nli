### 2026-10-08, check: does `apertus-v1.5-8b-thinking` answer like `apertus-v1.5-8b`? (20 task A dev cases, paired)

- Why: `apertus-v1.5-8b` was down on Public AI during E3 (`2026-10-08_rashad_embed-vs-section_devA300`), while `apertus-v1.5-8b-thinking` (an Apertus v1.5 model, so allowed) answered. The check decides whether it may finish E3.
- Cases: 20 of E3's cases 1 to 172 that `apertus-v1.5-8b` had answered in both arms, evenly spaced (17 booklets); filtered by id into `output/devA20eq/`.
- Command (from `track_2a/`): `LLM_NAME=swiss-ai/apertus-v1.5-8b-thinking EMBED_MODEL_DIR=models/multilingual-e5-small python3 scripts/paired_run.py` on those cases with the same two arms as E3, 18:18 to 18:23 UTC, written to the session's scratch folder and copied here.
- Just before, the task A example case (`examples/cases.jsonl`, `v1.1-row-2-A`, vote section) gave exactly `apertus-v1.5-8b`'s answer from `make run`: label 0, pages 4 and 58 to 61, 15,579 input and 29 output tokens.
- Against `apertus-v1.5-8b`'s answers in E3 for the same cases: vote-section same label 19/20, identical answer text 17/20; embed-e5-small 19/20 and 18/20. Correct labels: 8B 9 + 14 = 23, thinking 10 + 13 = 23. Input tokens equal in all 40; mean output tokens 24 against 23 and 24 (json_schema leaves no room for reasoning). Mean time vote-section 2.9 s (8B) against 4.1 s (thinking).
- For scale: `apertus-v1.5-8b` against its own E2 answers on the same 20 vote-section cases: same label 10/20, identical text 3/20 (E2 ran these cases on an earlier server, see E3's notes).
- The Macro-F1 of 20 cases (0.379 and 0.520 in the table) means little on its own; the point of this run is the agreement.
