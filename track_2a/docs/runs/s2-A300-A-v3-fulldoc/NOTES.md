### 2026-10-08, session 2: task A full-document baseline, all 300 dev cases (A-v3-fulldoc) — reference row

- The 60-case sample run plus a run on the other 240 task A dev cases (`s2-A240-A-v3-fulldoc`, 06:49 to 07:37 UTC), with the same image, prompt and settings, merged in `docs/runs/s2-A300-A-v3-fulldoc/` and scored once with the official scorer on all 300 task A dev cases (`output/devA/`, filtered by id from `data/dev/`). Format check: no errors.
- **This is the reference row for every later context-selection experiment:** 39,706 input tokens per case on average (the whole booklet), mean 11.5 s, p95 30.3 s.
- Below the 0.60 minimum, mostly because of unparseable answers: 110 of 300 (37 %). 84 of the 104 in the 240-case part were reasoning in prose that hit the 64-token answer limit before the JSON, 16 were a stray `<|inner_prefix|>` token, and 4 were page lists that were too long. All got the label-1 fallback, which is why 55 gold contradictions came out neutral. The 60-case sample had only 6 such answers (10 %), so its 0.767 was optimistic.
- Diagnostic only (not an official number): on the 187 cases with a parsed answer, Macro-F1 is 0.765.
- Confusion (rows gold E/N/C): E 57/33/12, N 3/87/9, C 8/55/36. Same-language 0.647, cross-lingual 0.560; by booklet language de 0.522, fr 0.588, it 0.656.
- Evidence: an upper bound measured on the 60-case sample shows that at least 35 of its 40 gold entailment/contradiction cases have a page that matches the gold passage under the official rule (0.875), against 15/40 actually cited. So the evidence gap is page choice, not page text.
- Task A runs used code identical to commit `4e90ddc` (prompt `A-v3-fulldoc`, retry active).
