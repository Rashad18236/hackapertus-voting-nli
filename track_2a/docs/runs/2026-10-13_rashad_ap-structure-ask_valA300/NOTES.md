### AP-structure asked after the parser, parser forced off (val sample): 0.939 / 0.917 against 0.872 / 0.593, passes the STRUCTURE RULE (session 12 step 6)

**Arms** (interleaved, the 300 balanced val task A cases of `data/val/sample300`, 1 request per second, 13:56 to 14:28
UTC; all 645 requests (600 answers, 45 contents calls) from one backend, blablador `vllm-0.23.1rc1`), both with the
test force "no parser", as on dev (`2026-10-13_rashad_ap-structure-ask_devA300`):

| Arm | Macro-F1 | Evidence (of 204) | Neutral recall | Input + output tokens per case | Fixes / breaks |
|---|---|---|---|---|---|
| today-noparser (embed-e5-small) | 0.872 | 0.593 (121) | 0.917 | 1,827 + 15.6 | |
| **AP-ask-noparser** | **0.939** | **0.917** (187) | 0.990 | 1,622 + 43.4 | 25 / 5 (sign test p < 0.001) |

Apertus's contents placed the vote for 281 of 300 cases (45 contents calls, 1,823 + 192 tokens each, 0 failed);
paths: council 74, summary 52, committee 45, law 44, detail 43, fallback 42.

**STRUCTURE RULE** (Macro-F1 at least 0.02 above today's forced handling, evidence not lower, on dev and val; no
unforced dev or val case reaches it): dev +0.050 / +0.254, val **+0.068 / +0.324**; G1/G2 with it on change only the
four cases the new bm25-ap fallback changes (no case asks for the contents): **passes; AP-structure asked after the
parser becomes a default.** It acts only when the rules name a part and the parser gives no valid part for the vote.
