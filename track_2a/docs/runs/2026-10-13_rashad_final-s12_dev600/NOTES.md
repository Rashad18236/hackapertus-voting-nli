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

Local time and REF SCORE: measured through the same image (`scripts/local_time.py`, 2 CPUs pinned to CPUs 2-3, 4 GB, the
fake model replaying the final answers after the given delay; `local_time_*.json`; REF SCORE with its parts in
`ref_score.json`):

| Model latency per request | Task A local time per case (s) | Task B | S_A | S_B | REF SCORE |
|---|---|---|---|---|---|
| 1.0 s | 0.0170 | 0.0120 | 0.9060 | 0.8988 | **0.9031** |
| 0.3 s | 0.1599 | 0.0104 | 0.8029 | 0.9084 | **0.8451** |
| 0.1 s | 0.3639 | 0.1607 | 0.7766 | 0.8410 | **0.8024** |

A repeat of task A at 0.3 s gave 0.113 s per case (single measurements vary by up to about 0.03 s).

