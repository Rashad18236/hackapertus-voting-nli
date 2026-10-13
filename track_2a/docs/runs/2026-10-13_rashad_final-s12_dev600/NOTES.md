### Final defaults through the published image, dev (session 12 FINISH)

**Image** `ghcr.io/rashad18236/hackapertus-voting-nli:sha-828429cab766` (built by the publish workflow from `828429c`,
pulled from ghcr.io, run with `make run`; task A and task B in separate containers; the real endpoint, Public AI's
`swiss-ai/apertus-v1.5-8b`, one request per second). Cases: 300 task A and 300 task B cases. Every answer and every parsing or translation
call from one backend (blablador `vllm-0.23.1rc1`); 0 failed calls; 0 unreadable
answer(s) (the neutral fallback, the only labels Python wrote).

| | Macro-F1 | Evidence | Input + output tokens per case | Session 11's final image |
|---|---|---|---|---|
| Task A | **0.977** | **0.980** (197 of 201) | 1,240 + 14.7 | 0.980 / 0.985 |
| Task B | **0.987** | — | 815 + 8.7 | 0.987 |

Task A paths: council 102, summary 67, committee 48, detail 43, law 39, bm25-ap 1. The 1 case(s) section-route cannot route
(claims naming a part the vote does not have, or no vote match) went through the new fallback bm25-ap; no case needed
AP-structure (the parser gives a valid part for every vote) or the memory guard (no limit below 1.5 GiB).

Local time and REF SCORE: LT_PLACEHOLDER
