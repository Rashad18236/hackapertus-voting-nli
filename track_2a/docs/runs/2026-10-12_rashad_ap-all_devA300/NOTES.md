### AP-all against today on dev: Apertus in both parsing roles costs 0.017 Macro-F1, 0.090 evidence and 34 % more input tokens (session 11 step 3, run 1)

**Arms** (interleaved, all 300 dev task A cases, 1 request per second also between a case's own calls, 22:33 to
23:07 UTC; all 944 requests answered by one backend, blablador `vllm-0.23.1rc1`):

- **today**: the defaults (section-route; fallback embed-e5-small).
- **AP-all**: Apertus in both parsing roles (`--ap-part-a all --ap-structure-a all --fallback-a vw+bw`).
  AP-claim: one call per case names the part the claim's opening refers to (or "none") and restates the claim
  without its opening in the booklet's language. AP-structure: one call per booklet reads the contents pages
  (44 calls); its entries pass the parser's heading checks before any part is used. A case whose vote Apertus's
  contents do not place goes to BW, a part "none" or a part that failed its checks to VW. The Python parser and
  router are not used. All parsing calls count in the case's tokens (a booklet's contents call in its first case).

| Arm | Macro-F1 | Evidence (of 201) | F1 ent / neu / con | Input + output tokens per case | of which parsing calls | p95 time |
|---|---|---|---|---|---|---|
| today | **0.977** | **0.980** (197) | 0.976 / 0.990 / 0.964 | **1,238 + 14.5** | 0 | 2.5 s |
| AP-all | 0.960 | 0.891 (179) | 0.955 / 0.961 / 0.964 | 1,655 + 90.9 | 502 + 76.5 | 13.6 s |

Fixes / breaks of AP-all against today: 1 / 6. 0 failed calls, 0 unreadable answers (parsing calls included).

**What Apertus did** (`AP-all/ap_summary.json`, `scripts/ap_summary.py`):

- **Part (AP-claim):** equal to the rules' part for 267 of 300 claims (89.0 %). Differences: detail → council 12,
  detail → none 7, law → summary 4, law → council 4, law → none 3, detail → law 2, detail → committee 1; "none" 10 times
  in all. The rules route all 300 dev claims, so on dev Apertus can only lose here.
- **Structure (AP-structure):** the case's vote placed and checked for 279 of 300 cases (93.0 %); the other 21 went
  booklet-wide. Paths: council 103, summary 65, committee 46, law 27, detail 17, vote-wide 21, booklet-wide 21
  (today: 299 routed, 1 to embed-e5-small).
- **Tokens:** 502 input + 76.5 output tokens of parsing per case (one claim call per case, ~1,800 + 180 per booklet
  for the contents), +34 % input tokens and +527 % output tokens in all.

AP-all never becomes the default (the step's rule). **Its local time** (`AP-all/local_time_d0.3.json`): the image
with the step 4 defaults, 2 CPUs, a fake model replaying these very answers after 0.3 s (`scripts/ap_replay_table.py`
builds the table; 644 requests, 0 replay misses): **0.822 s per case**, against 0.101 s for today's defaults in the
same setting. With Apertus asked while a case is prepared, the CLI prepares and completes each case in turn, so no
local work hides behind a request. The probe run is `2026-10-12_rashad_ap-all_probeA94`.
