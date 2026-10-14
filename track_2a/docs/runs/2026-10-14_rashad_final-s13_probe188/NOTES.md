### Final defaults through the published image, probe (session 13 FINISH)

**Image** `ghcr.io/rashad18236/hackapertus-voting-nli:sha-54032b4a7970` (built by the publish workflow from `54032b4`,
also tagged `session-13`; pulled from ghcr.io, run with `make run`; task A and task B in separate containers; the real
endpoint, Public AI's `swiss-ai/apertus-v1.5-8b`, one request per second). Cases: 94 task A and 94 task B
cases. Every answer and every translation call from one backend (blablador `vllm-0.23.1rc1`); 0 failed calls;
0 unreadable answer(s) (the neutral fallback, the only labels Python wrote).

New defaults against session 12's: model S ranks a long part's paragraphs, the fallback's chunks and vote names by
meaning (S RULE, step 6); evidence adds the page hedge H (step 3). Session 12's final image in the last column
(another run; not a comparison).

| | Macro-F1 | Evidence | Input + output tokens per case | Session 12's final image |
|---|---|---|---|---|
| Task A | **0.981** | **0.985** (64 of 65) | 1,172 + 16.6 | 0.971 / 0.969 |
| Task B | **0.977** | — | 789 + 8.9 | 0.977 |

Task A paths: council 34, summary 20, law 16, detail 10, committee 10, fallback (bm25-ap) 4; translation calls (bm25-ap across languages): 3. No case needed AP-part or
AP-structure.

Local time and REF SCORE: measured through the same image (`scripts/local_time.py`, 2 CPUs pinned to CPUs 2-3, 4 GB, the
fake model replaying the final answers after the given delay, 01:17 to 02:05 UTC; `local_time_*.json`; REF SCORE with its
parts in `ref_score.json`):

| Model latency per request | Task A local time per case (s) | Task B | S_A | S_B | REF SCORE |
|---|---|---|---|---|---|
| 1.0 s | 0.0352 | 0.0139 | 0.9130 | 0.8878 | **0.9029** |
| 0.3 s | 0.0273 | 0.0152 | 0.9130 | 0.8832 | **0.9011** |

The probe has no replay table of its own, so the fake model gives its fixed answer to every probe request (replay misses); local work does not depend on the answer.
