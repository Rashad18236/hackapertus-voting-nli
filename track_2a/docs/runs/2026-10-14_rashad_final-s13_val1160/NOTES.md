### Final defaults through the published image, val (session 13 FINISH)

**Image** `ghcr.io/rashad18236/hackapertus-voting-nli:sha-54032b4a7970` (built by the publish workflow from `54032b4`,
also tagged `session-13`; pulled from ghcr.io, run with `make run`; task A and task B in separate containers; the real
endpoint, Public AI's `swiss-ai/apertus-v1.5-8b`, one request per second). Cases: 580 task A and 580 task B
cases. Every answer and every translation call from one backend (blablador `vllm-0.23.1rc1`); 0 failed calls;
1 unreadable answer(s) (the neutral fallback, the only labels Python wrote).

New defaults against session 12's: model S ranks a long part's paragraphs, the fallback's chunks and vote names by
meaning (S RULE, step 6); evidence adds the page hedge H (step 3). Session 12's final image in the last column
(another run; not a comparison).

| | Macro-F1 | Evidence | Input + output tokens per case | Session 12's final image |
|---|---|---|---|---|
| Task A | **0.969** | **0.965** (387 of 401) | 1,225 + 14.7 | 0.961 / 0.960 |
| Task B | **0.968** | — | 820 + 9.4 | 0.969 |

Task A paths: council 175, summary 139, committee 102, law 87, detail 74, fallback (bm25-ap) 3; translation calls (bm25-ap across languages): 2. No case needed AP-part or
AP-structure.

LOCAL_TIME_val1160
