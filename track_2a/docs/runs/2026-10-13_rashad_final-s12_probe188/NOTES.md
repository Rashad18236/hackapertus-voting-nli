### Final defaults through the published image, probe (session 12 FINISH)

**Image** `ghcr.io/rashad18236/hackapertus-voting-nli:sha-828429cab766` (built by the publish workflow from `828429c`,
pulled from ghcr.io, run with `make run`; task A and task B in separate containers; the real endpoint, Public AI's
`swiss-ai/apertus-v1.5-8b`, one request per second). Cases: the 94 task A and 94 task B cases of the test rows dated 2021-03-07 and 2025-09-28. Every answer and every parsing or translation
call from one backend (blablador `vllm-0.23.1rc1`); 0 failed calls; 0 unreadable
answer(s) (the neutral fallback, the only labels Python wrote).

| | Macro-F1 | Evidence | Input + output tokens per case | Session 11's final image |
|---|---|---|---|---|
| Task A | **0.971** | **0.969** (63 of 65) | 1,169 + 16.5 | 0.971 / 0.954 |
| Task B | **0.977** | — | 789 + 8.6 | 0.977 |

Task A paths: council 34, summary 20, law 16, detail 10, committee 10, bm25-ap 4. The 4 case(s) section-route cannot route
(claims naming a part the vote does not have, or no vote match) went through the new fallback bm25-ap; no case needed
AP-structure (the parser gives a valid part for every vote) or the memory guard (no limit below 1.5 GiB).

Local time and REF SCORE: LT_PLACEHOLDER
