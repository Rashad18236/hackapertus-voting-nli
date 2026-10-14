### Final defaults through the published image, dev (session 13 FINISH)

**Image** `ghcr.io/rashad18236/hackapertus-voting-nli:sha-54032b4a7970` (built by the publish workflow from `54032b4`,
also tagged `session-13`; pulled from ghcr.io, run with `make run`; task A and task B in separate containers; the real
endpoint, Public AI's `swiss-ai/apertus-v1.5-8b`, one request per second). Cases: 300 task A and 300 task B
cases. Every answer and every translation call from one backend (blablador `vllm-0.23.1rc1`); 0 failed calls;
0 unreadable answer(s) (the neutral fallback, the only labels Python wrote).

New defaults against session 12's: model S ranks a long part's paragraphs, the fallback's chunks and vote names by
meaning (S RULE, step 6); evidence adds the page hedge H (step 3). Session 12's final image in the last column
(another run; not a comparison).

| | Macro-F1 | Evidence | Input + output tokens per case | Session 12's final image |
|---|---|---|---|---|
| Task A | **0.973** | **0.985** (198 of 201) | 1,251 + 14.8 | 0.977 / 0.980 |
| Task B | **0.987** | — | 815 + 8.8 | 0.987 |

Task A paths: council 102, summary 67, committee 48, detail 43, law 39, fallback (bm25-ap) 1; translation calls (bm25-ap across languages): 1. No case needed AP-part or
AP-structure.

Local time and REF SCORE: measured through the same image (`scripts/local_time.py`, 2 CPUs pinned to CPUs 2-3, 4 GB, the
fake model replaying the final answers after the given delay, 01:17 to 02:05 UTC; `local_time_*.json`; REF SCORE with its
parts in `ref_score.json`):

| Model latency per request | Task A local time per case (s) | Task B | S_A | S_B | REF SCORE |
|---|---|---|---|---|---|
| 1.0 s | 0.0161 | 0.0080 | 0.9047 | 0.9301 | **0.9149** |
| 0.3 s | 0.0171 | 0.0090 | 0.9047 | 0.9196 | **0.9107** |
| 0.1 s | 0.0249 | 0.1315 | 0.9047 | 0.8420 | **0.8796** |

A repeat of task A at 0.3 s gave 0.0146 s per case. Session 12's final image (e5): task A 0.0170 / 0.1599 / 0.3639 s at 1.0 / 0.3 / 0.1 s; model S keeps task A's local work small at every speed.
