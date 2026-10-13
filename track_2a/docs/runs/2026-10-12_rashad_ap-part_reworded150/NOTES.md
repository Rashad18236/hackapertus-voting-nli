### AP-part on reworded openings (dev): +0.073 Macro-F1 over VW, passes the HYBRID RULE on dev (session 11 step 3, run 2)

**Cases.** 150 balanced dev task A cases (50 per label) whose opening formula was replaced by other words for the
same source ("Die Landesregierung" for the Federal Council, "Kommt die Vorlage durch" for "Wird die Abstimmung
angenommen", …; `scripts/make_reworded.py`, `output/devA_reworded150/rewording.json`), so the label cannot change
and the rules (`src/claim_router.py`) find no part in any of them. This is the situation of a claim whose opening the
rules do not know (no dev, val or probe claim in the dataset; a reworded or new opening would be).

**Arms** (interleaved, 1 request per second also between a case's own calls, 23:18 to 23:53 UTC; all 600 requests
answered by one backend, blablador `vllm-0.23.1rc1`):

- **today**: the defaults; no part, so embed-e5-small (8 chunks of the whole booklet);
- **VW**: the vote-wide fallback (step 2);
- **AP-part**: when the rules find no part, one call asks Apertus which part the opening names
  (`src/ap_parse.py`, `AP-claim-v1`), then section-route routes to that part as for a rule match; "none", or a part
  the parser did not validate, goes to VW.

| Arm | Macro-F1 | Evidence (of 100) | F1 ent / neu / con | Input + output tokens per case | of which the part call |
|---|---|---|---|---|---|
| today | 0.906 | 0.700 (70) | 0.931 / 0.902 / 0.887 | 1,699 + 15.6 | 0 |
| VW | 0.894 | 0.670 (67) | 0.947 / 0.877 / 0.857 | 1,045 + 14.5 | 0 |
| **AP-part** | **0.967** | **0.880** (88) | 0.958 / 0.990 / 0.951 | 1,383 + 63.4 | 236 + 49.0 |

Fixes / breaks against today: VW 9 / 11, AP-part 13 / 4. 0 failed calls, 0 unreadable answers.

**Apertus's part against the part the original opening named:** 118 of 150 equal (78.7 %): council 47/48,
summary 35/37, committee 23/23, law 9/17, detail 4/25 ("detail" openings such as "Kommt die Vorlage durch" were read
as the council 10 times and as no part 9 times). 15 answers "none" (to VW). Paths: council 58, summary 39,
committee 22, law 11, detail 4, vote-wide 16.

**HYBRID RULE, AP-part** ("becomes the step after the rules if run 2's Macro-F1 is ≥ 0.02 above VW's"): 0.967 against
0.894, **+0.073: passes on dev**; confirmed on the reworded val sample next (`2026-10-12_rashad_ap-part_valA-reworded150`
or the next day's folder). A case the rules route is never touched (the call is made only when they find no part).
