### E3, Apertus as the router (information only)

Session 9, phase E3. Would Apertus route a claim to the right part of the vote better than
`src/claim_router.py`'s regular expressions, and at what cost? Nothing in the pipeline changed: the rules
stay the router.

**Command** (from `track_2a/`, code `50cb320`): `LLM_MIN_INTERVAL=1 python3 scripts/llm_router_check.py --out
docs/runs/2026-10-09_rashad_llm-router_dev300-stress300`; 21:09:40 to 21:22:40 UTC, 600 calls, model
`swiss-ai/apertus-v1.5-8b` on Public AI. One call per claim: the prompt (`ROUTER_PROMPT` in the script) lists
the five parts and "none", the answer is forced to `{"part": ...}` by json_schema. Per claim:
`per_claim.jsonl`; totals: `summary.json`.

**Dev claims (300, no intended part recorded):** Apertus agrees with the rules on **278**. Of the 22
disagreements, 16 are claims the rules send to the text put to the vote and Apertus to the Federal Council's
part; 14 of them open like "Laut dem Abstimmungstext empfiehlt die Bundesversammlung …" / "Selon le texte
soumis au vote, l'Assemblée fédérale recommande …" (the text put to the vote holds that recommendation).
Apertus calls 2 more law claims detail, routes 3 nowhere (2 law, 1 detail) and calls 1 summary claim council.

**Stress openings (300, each with the intended part or none):**

| | Apertus | Rules |
|---|---|---|
| Right (intended part, or none when none is intended) | 283 | 285 |
| Routed to a wrong part (Apertus would read the wrong passage) | **17** | **0** |
| Fell back where a part was intended (runs as embed-e5-small, still answered) | 0 | 15 |

Apertus routes every opening the rules miss (15 of 15), but it also picks a part for 9 of the 12 openings that
name no source, and a wrong part for 8 that do (for example "Der Bundesrat ist laut Zusammenfassung …" →
council). A wrong part is worse than a fallback: the case is answered from the wrong text.

**Cost:** 220 input and 8 output tokens per call on dev claims, 1.3 s per call; per case that is about +18 %
input tokens over the default's 1,238 and one more model call. All 600 calls answered, none failed.

**Reading:** on the dataset's own claims the rules and Apertus nearly agree, and where they differ the rules
are right in the cases we looked at (the law text does contain the Federal Assembly's recommendation). On
reworded openings Apertus is more willing to route but makes wrong-part errors the rules do not. An Apertus
router would cost a call and tokens per case for no measured gain; a fallback-only use (ask Apertus only when
the rules give none) would fix the 15 stress fallbacks, which this check did not measure end to end.
