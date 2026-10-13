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

Local time and REF SCORE: measured through the same image (`scripts/local_time.py`, 2 CPUs pinned to CPUs 2-3, 4 GB, the
fake model replaying the final answers after the given delay; `local_time_*.json`; REF SCORE with its parts in
`ref_score.json`):

| Model latency per request | Task A local time per case (s) | Task B | S_A | S_B | REF SCORE |
|---|---|---|---|---|---|
| 1.0 s | 0.0401 | 0.0152 | 0.9054 | 0.8832 | **0.8965** |
| 0.3 s | 0.0275 | 0.0157 | 0.9054 | 0.8816 | **0.8959** |

Task A at 0.3 s: 0.028 s per case against session 11's 0.237 s: the 4 fallback cases no longer embed a whole booklet with e5 (bm25-ap).
Requests the replay table does not know (val task B, the probe) get the fake model's fixed answer; the local work is the same.

