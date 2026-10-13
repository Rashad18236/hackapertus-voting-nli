### Evidence under three page rules, and the page hedge H (session 13, step 3, no model calls): H passes its rule

**What is measured** (`scripts/evidence_pages.py`, `evidence_pages.json`). On session 12's final answers
(`2026-10-13_rashad_final-s12_{dev600,val1160,probe188}`, task A), for every gold entailment or contradiction case:
a **text hit** when one of the first five items matches the gold passage (the starter's rule); then, for the hit items,
three page rules the organisers have not settled (`docs/organiser_questions.md`, question 1): **rule 1** the item's
text lies on the page it names; **rule 2** its page is a gold page; **rule 3** its page is the first gold page (gold
pages as in `scripts/evidence_loss.py`). A case passes a rule when one hit item does. Counts of all gold 0/2 cases.

**H** (`--evidence-hedge-a`, `src/evidence.py` hedge): today's items first; if the first cited paragraph opens its
page and the part continues from an earlier page, the part's paragraph before it (with its page); if slots remain,
the cited page's whole text (at most 5,000 characters); at most five items; a repeated text left out. Rebuilt from the
same answers by preparing each case again as the CLI does: every routed case was rebuilt exactly (dev 198, val 385,
probe 61; the others are not routed or have no evidence and keep today's items).

| Set | Items | Gold 0/2 cases | Text hit | Rule 1 (quote's page) | Rule 2 (any gold page) | Rule 3 (first gold page) |
|---|---|---|---|---|---|---|
| dev | today | 201 | 197 (0.980) | 197 (0.980) | 192 (0.955) | 116 (0.577) |
| dev | **H** | 201 | **198 (0.985)** | **198 (0.985)** | **193 (0.960)** | **119 (0.592)** |
| val | today | 401 | 385 (0.960) | 385 (0.960) | 379 (0.945) | 223 (0.556) |
| val | **H** | 401 | 385 (0.960) | 385 (0.960) | 379 (0.945) | **236 (0.589)** |
| probe | today | 65 | 63 (0.969) | 63 (0.969) | 63 (0.969) | 44 (0.677) |
| probe | **H** | 65 | 63 (0.969) | 63 (0.969) | 63 (0.969) | **46 (0.708)** |

Rules 1 and 2 cost little today (every hit lies on its page; 5 + 6 + 0 hits lie on a page outside the gold pages), but
**rule 3 would cost about 40 % of the evidence score**: the passage often starts on the page before the paragraph
Apertus cites. H adds 18 first-page hits (3 + 13 + 2) and one text hit on dev (the whole page holds the passage).

**G1/G2 with H on** (`g1g2_H_on_compare.log`, replay of the 1,180 dev and val requests): G1 identical (0 requests or
paths differ), 0 labels differ, evidence differs in 414 cases (dev 138, val 276: exactly the cases the offline
rebuild changed). Starter's scorer on the replay: dev evidence 0.9801 → 0.9851, val 0.9601 → 0.9601, Macro-F1
unchanged.

**H RULE** (decisions file, set before the scoring): at least as good as today under every rule on each set, better
under rule 3 over the three sets, labels identical, G1 identical and G2 only in evidence: **passes**. H joins the
combination (FINISH order: prompt A → A6 → prompt B → H → S).
