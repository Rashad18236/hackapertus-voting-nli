### Task B selectors on dev (session 12 step 3): none passes TASK B RULE 2; T stays

**Arms** (interleaved, all 300 dev task B cases, 1 request per second, 11:19 to 11:47 UTC; every answer and every
translation call from one backend, blablador `vllm-0.23.1rc1`). All four keep T's rule: a reference over 3,000
characters becomes its first line plus 4 paragraphs (218 of 300 dev references are that long).

- **today**: selector T (e5 on each paragraph's first 300 characters), the default since session 11;
- **B-R**: R = model S (step 1) on each paragraph's whole text (`--context-b cut4-r --ranker S`);
- **H**: session 11's selector: L (character 4-grams and numbers) when claim and reference share a language, else T;
- **B-BM25**: Kaan's BM25 on the claim; when the claim is in another language than the reference, Apertus first
  translates the claim (`AP-translate-v1`; 125 calls, 0 failed, 127.6 + 42.0 tokens each, counted in the case).

| Arm | Macro-F1 | F1 ent / neu / con | Unreadable | Input + output tokens per case | Long references wrong (of 218) | of which neutral called contradiction (same / cross language) | Fixes / breaks vs today |
|---|---|---|---|---|---|---|---|
| today (T) | **0.987** | see run.json | 0 | **815 + 8.6** | 4 | 1 (1 / 0) | |
| B-R | 0.973 | | 1 | 923 + 8.7 | 8 | 6 (1 / 5) | 3 / 7 |
| H | **0.993** | | 0 | 923 + 8.6 (+13.1 %) | 2 | 0 | 2 / 0 |
| B-BM25 | 0.967 | | 0 | 1,039 + 26.2 | 10 | 6 (0 / 6) | 2 / 8 |

No error on references of 3,000 characters or less in any arm.

**TASK B RULE 2** (decisions file, set before the run: Macro-F1 at least T's + 0.005, no more unreadable answers,
input + output tokens at most T's + 10 %, local time at most + 0.005 s):

- **B-R fails** (Macro-F1 −0.014, one unreadable answer): S on the whole paragraph picks worse paragraphs across
  languages (5 cross-language neutral cases called contradiction). Model S stays task A's question (step 4).
- **H fails on tokens only**: Macro-F1 +0.0067 (2 fixes, 0 breaks), but 931.2 against 823.9 tokens per case
  (+13.0 %; the rule allows 10 %). By REF SCORE's token part this costs more than the 2 cases gain (S_B: +0.7 × 0.0067
  = +0.005 for Macro-F1, −0.15 × (800/824 − 800/931) = −0.017 for tokens, with the fixed reference of 800 tokens).
- **B-BM25 fails** (Macro-F1 −0.020): BM25 on Apertus's translation misses across languages (6 cross-language
  neutral cases called contradiction), and the translation call adds 170 tokens to each cross-language long case.

All three stay in the code, switched off; no val run is spent (val only confirms what passes on dev). On these 300
dev cases T itself makes 1 neutral → contradiction error on long references; on val (session 11) it made 9.
