### Final defaults through the published image, val (session 12 FINISH)

**Image** `ghcr.io/rashad18236/hackapertus-voting-nli:sha-828429cab766` (built by the publish workflow from `828429c`,
pulled from ghcr.io, run with `make run`; task A and task B in separate containers; the real endpoint, Public AI's
`swiss-ai/apertus-v1.5-8b`, one request per second). Cases: 580 task A and 580 task B cases. Every answer and every parsing or translation
call from one backend (blablador `vllm-0.23.1rc1`); 0 failed calls; 1 unreadable
answer(s) (the neutral fallback, the only labels Python wrote).

| | Macro-F1 | Evidence | Input + output tokens per case | Session 11's final image |
|---|---|---|---|---|
| Task A | **0.961** | **0.960** (385 of 401) | 1,211 + 14.7 | 0.959 / 0.955 |
| Task B | **0.969** | — | 820 + 9.4 | 0.968 |

Task A paths: council 175, summary 139, committee 102, law 87, detail 74, bm25-ap 3. The 3 case(s) section-route cannot route
(claims naming a part the vote does not have, or no vote match) went through the new fallback bm25-ap; no case needed
AP-structure (the parser gives a valid part for every vote) or the memory guard (no limit below 1.5 GiB).

Local time and REF SCORE: measured through the same image (`scripts/local_time.py`, 2 CPUs pinned to CPUs 2-3, 4 GB, the
fake model replaying the final answers after the given delay; `local_time_*.json`; REF SCORE with its parts in
`ref_score.json`):

| Model latency per request | Task A local time per case (s) | Task B | S_A | S_B | REF SCORE |
|---|---|---|---|---|---|
| 1.0 s | 0.0093 | 0.0065 | 0.8958 | 0.9385 | **0.9129** |
| 0.3 s | 0.0101 | 0.0074 | 0.8958 | 0.9245 | **0.9073** |
Requests the replay table does not know (val task B, the probe) get the fake model's fixed answer; the local work is the same.

