### AP-structure with the Python parser switched off (dev): +0.084 Macro-F1 and +0.269 evidence over VW, but not adoptable (session 11 step 3, run 3)

**What it tests.** Whether Apertus's reading of the contents can replace the Python parser where the parser fails.
A test-only force in `scripts/paired_run.py` ("no parser") keeps the case's vote and its contents entry but makes
every part fail its checks, as if the parser had failed for that vote. All 300 dev task A cases, interleaved, 1 request
per second also between a case's own calls, 23:52 to 00:38 UTC; all 944 requests (900 answers and 44 contents calls)
answered by one backend (blablador `vllm-0.23.1rc1`).

- **today-noparser**: the defaults; no valid part, so embed-e5-small;
- **VW**: the vote-wide fallback; with no valid part it shows the vote's pages as paragraphs without part names;
- **AP-structure** (`--ap-structure-a after-parser`): when the parser gives no valid part, Apertus reads the
  contents pages (one call per booklet, cached); its entries go through the parser's own heading checks
  (`booklet._parse_vote`); a vote placed this way is routed by the rules' part as usual; otherwise VW.

| Arm | Macro-F1 | Evidence (of 201) | F1 ent / neu / con | Input + output tokens per case | of which contents calls |
|---|---|---|---|---|---|
| today-noparser | 0.900 | 0.672 (135) | 0.941 / 0.873 / 0.884 | 1,868 + 15.8 | 0 |
| VW | 0.886 | 0.687 (138) | 0.929 / 0.880 / 0.849 | 1,055 + 14.5 | 0 |
| **AP-structure** | **0.970** | **0.955** (192) | 0.971 / 0.985 / 0.953 | 1,478 + 43.1 | 268 + 28.5 |

Fixes / breaks against today-noparser: VW 19 / 23, AP-structure 25 / 4. 0 failed calls, 0 unreadable answers.
Apertus's contents placed the vote with parts that passed the heading checks for 277 of 300 cases (paths: council 93,
summary 62, committee 44, detail 36, law 35; vote-wide 30). For comparison, the routed defaults scored 0.977 / 0.980 on
the same cases (`2026-10-12_rashad_ap-all_devA300`, arm today): with the parser off, Apertus's reading of the contents
plus the parser's checks recovers most of the routed quality.

**HYBRID RULE, AP-structure** ("becomes the step after the parser if run 3's Macro-F1 is ≥ +0.02 or its evidence
≥ +0.05 above VW's, on dev and on val, and in a. ≥ 95 % of its votes equal the Python parser's where that passes"):
dev passes (+0.084, +0.269), but part a fails (78.7 %, `2026-10-12_rashad_ap-structure_booklets93`), so **AP-structure
is not adopted** whatever val shows, and no val run was spent on it. It stays in the code, off
(`--ap-structure-a after-parser`). On the 93 booklets the parser now fails 5 votes, all with usable parts, so the
situation it would cover is rare in the booklets we know.
