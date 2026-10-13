### Rankers without the endpoint: model S keeps the cited paragraph as often as e5 (session 12 step 1); R = S

**Model S** (`src/static_embed.py`): `sentence-transformers/static-similarity-mrl-multilingual-v1` (Apache-2.0, commit
`b68f412`), a table of token vectors averaged and normalised, computed with tokenizers and numpy; the table cut to its
first 256 dimensions (108 MB). Its vectors equal the reference library's on 50 dev claims at 256 and at 1,024
dimensions (largest difference 3e-8, the same order of all pairwise similarities; `static_equivalence.json`,
`scripts/static_equivalence.py`, sentence-transformers 5.1.1 in a separate environment on the development machine).

**Rankers** (`scripts/ranker_check.py`, `src/rankers.py`): e5 (today), S, S-1024 (all dimensions, for the cut
decision), BM25 (Kaan's, on the claim as it is), S+BM25 and e5+BM25 (reciprocal-rank fusion). Cases from the session 11
final runs (`2026-10-13_rashad_final-s11_*`): dev, val and probe pooled (each set separately in `ranker_check.json`).

- **Not cut** (599 routed task A cases answered correctly with label 0 or 2 whose part was sent whole; 197 same-language,
  402 cross-language; 219 with more than 8 paragraphs): is the first paragraph the answer cites among the ranker's 8
  (and 4) best?
- **Cut** (76 routed task A cases whose part was cut to 8; 44 of them gold entailment/contradiction with the gold
  passage in the part): paragraphs shared with e5's 8, and gold passage still among the 8.
- **Task B** (605 references over 3,000 characters with more than 4 paragraphs): paragraphs shared with selector T's 4
  (information only).

| Ranker | Not cut: at 8 / at 4, all | same language | cross-language | parts over 8 paragraphs | Cut: shared with e5's 8 | Cut: gold covered | Task B: shared with T's 4 |
|---|---|---|---|---|---|---|---|
| e5 | 0.987 / 0.937 | 1.000 / 0.980 | 0.980 / 0.915 | 0.964 / 0.895 | 8.00 | 44 of 44 | 3.10 |
| S | 0.993 / 0.935 | 0.995 / 0.959 | 0.993 / 0.923 | 0.982 / 0.881 | 3.51 | 44 of 44 | 2.11 |
| S-1024 | 0.995 / 0.937 | 0.995 / 0.965 | 0.995 / 0.923 | 0.986 / 0.886 | 3.75 | 44 of 44 | 2.11 |
| BM25 | 0.962 / 0.836 | 0.995 / 0.975 | 0.945 / 0.769 | 0.895 / 0.735 | 2.66 | 42 of 44 | 1.70 |
| S+BM25 | 0.988 / 0.913 | 0.995 / 0.970 | 0.985 / 0.886 | 0.968 / 0.854 | 3.26 | 44 of 44 | 1.84 |
| e5+BM25 | 0.983 / 0.926 | 1.000 / 0.980 | 0.975 / 0.900 | 0.954 / 0.877 | 4.72 | 44 of 44 | 2.27 |

**Selection of R** ("the best S-based ranker goes on if its cross-language share at 8 for task A is at most 3 points
below e5's"): S's cross-language share at 8 is 0.993 against e5's 0.980 (dev 0.984 = 0.984, val 0.996 vs 0.975, probe
1.000 = 1.000); S+BM25's 0.985. S is the best S-based ranker on every share at 8 and at 4 (S+BM25 loses at 4: 0.913
against 0.935). **R = S.** BM25 alone fails across languages (0.945 at 8, 0.769 at 4), as Kaan found.

**256 dimensions** ("unless that loses more than 1 point in b"): S-1024 is at most 0.5 points better on any share
(cross-language at 8: 0.995 vs 0.993; at 4 0.923 = 0.923; cut gold 44 = 44): **the 256-dimension table is kept.**

**Vote names by meaning with S** (`vote_margin_S.json`): session 10's test (264 vote names swapped into another
language) with S: S's largest margin of a wrong pick is 0.499, so its margin is 0.50 (`section_route.VOTE_MARGIN_S`):
71 placed right, none wrong (e5 at 0.04: 182). Only a vote name in another language than the booklet reaches this.
