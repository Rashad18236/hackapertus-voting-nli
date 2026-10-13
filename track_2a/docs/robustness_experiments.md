# Robustness experiments: tournament, negation, decomposition, retrievers

2026-10-12, Kaan with Claude Code, branch `kaan/robustness-experiments` (from `main` at `42b2a3c`). Every
number below comes from a run in `docs/runs/` and is scored with the starter's `evaluate.py` (`559b598`). The
test split was never used. Decisions: `docs/decisions/2026-10-12-1230_kaan_robustness.md`. No default was changed.

## 1. In short

| Idea | What it does | Dev result | Verdict |
|---|---|---|---|
| **Cross-language tournament** (`--strategy-a/-b xlang`) | Claim translated into the source language, source translated into the claim language (local MT); both judged; agreement decides, else a tie-break call | A 0.980 (−0.003), B 0.970 (+0.003); +70 % tokens, +2 s local time per case | **No.** The two sides agree in 97 % of translated cases, so it mostly re-confirms one call |
| **Negation check** (`negation`) | Apertus negates the claim; the negation is judged too; a neutral answer takes the label the negation implies | A 0.987 (+0.003), B 0.960 (−0.007); 3 calls, +110 % tokens | **No as a rule**, but its consistency is an excellent **error detector** (§3) |
| **Claim decomposition** (`decompose`) | Claims ≥ 180 chars split by Apertus into ≤ 4 one-fact claims, each judged | A 0.963 (−0.020), B 0.937 (−0.030); 0 fixed, 15 broken | **No.** Splitting loses the claim's meaning |
| **Retrievers** (`--context-a bm25 / bm25-mt / hybrid / vote-section-hybrid`) | Other rankings of the same chunks for cases routing cannot handle | Routing off: e5 0.900 → **bm25-mt 0.963**, hybrid 0.936; **val: 0.871 → 0.923 / 0.926** | **Yes.** Confirmed on val (p < 0.001); candidate new fallback `section-route-bm25-mt` |

What it means for the submission: today's routed path is already at 0.98 (A) and 0.97 (B) on dev, and the
remaining errors are reading errors that more calls on the same 8B model do not fix. Extra calls cost tokens and
the organisers score tokens (K, 15 %); by our estimate with the official formula every strategy lowers the total
(0.984 → 0.77 to 0.86). The retrievers are the useful outcome: the fallback is what a case gets when the router
or parser fails on the private set, and that path improves by about 0.05 Macro-F1 and 0.12 evidence on val.

## 2. Runs

| Run | Cases | Arms |
|---|---|---|
| `2026-10-12_kaan_retrieval-check_devA201` | 201 dev task A cases with a gold passage, no model | 5 retrievers offline |
| `2026-10-12_kaan_strategies_dev600` | all 600 dev cases (300 A, 300 B) | base, xlang, negation, decompose |
| `2026-10-12_kaan_retrievers_devA300` | 300 dev task A, routing off | embed-e5-small, bm25, bm25-mt, hybrid, vote-section-hybrid |
| `2026-10-12_kaan_retrievers_valA580` | 580 val task A, routing off | embed-e5-small, bm25-mt, hybrid |

All model runs: `swiss-ai/apertus-v1.5-8b` on Public AI, interleaved (every case goes to every arm back to back,
rotating order), one request every 2 s, 0 HTTP 429. One failed connection in about 7,700 calls (xlang, row 980 A),
answered the normal way as designed.

## 3. The strategies (dev, 600 cases)

| | base | xlang | negation | decompose |
|---|---|---|---|---|
| Task A Macro-F1 (right of 300) | 0.983 (295) | 0.980 (294) | **0.987** (296) | 0.963 (289) |
| Task A evidence | 0.985 | 0.980 | **0.990** | 0.965 |
| Task B Macro-F1 (right of 300) | 0.967 (290) | **0.970** (291) | 0.960 (288) | 0.937 (281) |
| Calls per case (A / B) | 1 / 1 | 1.70 / 1.76 | 2.99 / 3.0 | 1.72 / 1.73 |
| Mean input tokens (A / B) | 1,238 / 1,231 | 2,060 / 2,106 | 2,642 / 2,636 | 1,861 / 1,842 |
| Mean local time (A / B, ms) | 39 / 2 | 2,205 / 2,080 | 58 / 6 | 25 / 51 |
| Flips vs base, A (fixed / broken) | – | 0 / 1 | 1 / 0 | 0 / 6 |
| Flips vs base, B (fixed / broken) | – | 2 / 1 | 0 / 2 | 0 / 9 |
| Estimated official score (base = best team) | 0.984 | 0.774 | 0.833 | 0.858 |

Local time = case time minus the model's own time, which is what the organisers' T counts.

**Tournament.** The two sides agreed in 185 of 198 task A and 173 of 200 task B translated cases, and an agreed
answer was right 182/185 and 169/173 times. It fixed two task B claims about an unrelated passage that one call had
called a contradiction (rows 580, 875: both translated sides said neutral), which is task B's main weakness. It
broke task A row 1468 because the translation garbled the claim ("Der Bundesrat bedarf im Abstimmungstext den
Kosten …"). Offline, "agree else neutral" (0.937 / 0.915) and either side alone (0.954 to 0.960) are worse than the
tie-break that ran. The local translation (m2m100 418M, CPU) costs about 3.1 s per translated case.

**Negation.** The rewrites are good ("…für eine Annahme…", "…keine Auswirkungen…"). The rule fixed row 1016 A (a
refuted claim the first call called neutral: the negation was entailed). It broke rows 515 B and 623 B: for an
unrelated claim, the model calls the negated version a contradiction ("missing information" read as refutation),
so the neutral answer was replaced. Offline, "consistent else neutral" is much worse (0.932 / 0.946).

The useful finding is the **consistency of the two answers** (claim entailed and negation contradicted, or the
reverse, or both neutral):

| | Consistent | Inconsistent |
|---|---|---|
| Task A: base right / wrong | 279 / 1 | 15 / 4 |
| Task B: base right / wrong | 275 / **0** | 13 / **10** |

Every one of task B's 10 errors, and 4 of task A's 5, sit in the small inconsistent group (about 7 % of cases).
The check finds errors very well; it just does not say what the right answer is.

**Decomposition.** 72 task A and 73 task B claims were split (A: 27 into 2 parts, 22 into 3, 23 into 4). No case was fixed and 15
broke, for three reasons seen in the parts: the source opening is dropped ("Das Komitee vertritt die Ansicht, der
Gegenentwurf sei wirkungslos" → "Der Gegenentwurf verpflichtet … lediglich …", then judged as a fact and
contradicted); a list the booklet states as a whole is split into items judged one by one (row 85 B: hospitals,
homes, home care); some parts come back in English ("According to the claim, …", row 109 A). "Majority of parts"
offline (0.980 / 0.960) is better than "any part contradicted" but still below base.

## 4. The retrievers

Context: routing sends the gold passage in 200 of 200 routed dev cases, so a retriever only matters when routing
fails: an unknown claim opening, a vote name that does not match, a booklet the parser cannot split. On the private
set this is the main risk (router stress test: 131 of 300 reworded openings routed before session 8's fixes, 273
after). Each arm here is a retriever alone, as such a case would get it.

**Offline (no model), gold passage among the 8 chunks sent, 201 dev cases:**

| Retriever | Hit | Same language | Cross-language | Evidence ceiling |
|---|---|---|---|---|
| embed-e5-small (today's fallback) | 0.741 | 0.851 | 0.687 | 0.612 |
| bm25 | 0.547 | 0.821 | 0.410 | 0.443 |
| bm25-mt | 0.851 | 0.821 | 0.866 | 0.682 |
| hybrid | 0.866 | 0.866 | 0.866 | 0.672 |
| vote-section-hybrid | 0.876 | 0.866 | 0.881 | 0.682 |

**With the model, routing off:**

| | dev Macro-F1 (right of 300) | dev evidence | val Macro-F1 (right of 580) | val evidence | input tokens |
|---|---|---|---|---|---|
| embed-e5-small | 0.900 (270) | 0.682 | 0.871 (505) | 0.589 | ~1,860 |
| bm25 | 0.827 (248) | 0.507 | – | – | 2,396 |
| **bm25-mt** | **0.963 (289)** | **0.771** | 0.923 (535) | 0.706 | ~2,510 |
| **hybrid** | 0.936 (281) | 0.766 | **0.926 (537)** | **0.713** | ~2,370 |
| vote-section-hybrid | 0.920 (276) | 0.741 | – | – | 2,362 |

Paired against embed-e5-small: bm25-mt 25 vs 6 cases (dev, p = 0.0009) and 51 vs 21 (val, p = 0.0005); hybrid 17
vs 6 (dev, p = 0.035) and 48 vs 16 (val, p = 0.0001). bm25-mt vs hybrid: 13 vs 5 on dev (p = 0.096), 19 vs 21 on
val (no difference).

Why it works:
- **Plain BM25 fails across languages** (0.410 hit): a German claim shares few words with a French booklet.
  Translating only the claim (a short sentence, ~0.3 s locally) fixes that and is the largest single gain.
- **Exact words help neutral claims.** With e5, an unrelated claim still pulls chunks that sound related, and the
  model then reads them as support or contradiction. With bm25-mt nothing matches well and the model says neutral
  (dev gold neutral right: e5 86/99, bm25-mt 95/99; val 160/179 vs 167/179).
- **Numbers, article numbers and names** are matched exactly (law claims on dev: 30/39 → 37/39).
- A higher offline hit rate did not mean better labels (hybrid 0.866 > bm25-mt 0.851 offline, but fewer right on
  dev): the hit rate only asks whether the gold passage is among the 8 chunks, not what else is in them.

## 5. What to do next

1. **Make `section-route-bm25-mt` the task A default** (new variant, already registered and tested: routed cases
   send exactly today's requests; only the fallback changes). Confirmed on val. Costs: the MT model (476 MB) and
   `ctranslate2` + `sentencepiece` in the image (`requirements-experiments.txt` → `requirements.txt`, Dockerfile
   download step like e5's), about 2 s to load the MT model on the first fallback case, and ~650 more input tokens
   per fallback case. It also removes the slowest local step of today's fallback (embedding the whole booklet, up to
   26 s cold). Before adopting: run the router stress claims and the unseen booklets through it, measure cold
   start in the image, and decide with Rashad (session 10 owns timing).
2. **Try bm25-mt in task B's cut** (`taskb_context.cut_text` ranks long references with e5 today). Task B's main
   error is an unrelated passage called a contradiction; on task A, bm25-mt's biggest gain was exactly on neutral
   claims. One interleaved run on dev B, no new code beyond a ranking switch.
3. **Use negation inconsistency as a trigger, not as a rule.** It finds 14 of 15 errors in 7 % of cases. Two open
   problems: a cheaper trigger (the check itself costs two calls on every case), and what to do once triggered (a
   different prompt, more context, or a larger Apertus v1.5 model if the organisers allow it). Worth one offline
   study on the saved answers first: which signals (e5 similarity, answer length, claim type) predict
   inconsistency without the extra calls.
4. **Drop decomposition and the tournament** in their current form. If decomposition is revisited: keep the
   source opening on every part, force the claim's language, split only at "and/und/et/e", and combine by majority.
