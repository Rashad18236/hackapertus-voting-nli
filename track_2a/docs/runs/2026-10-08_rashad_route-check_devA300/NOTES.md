### 2026-10-08, session 6, Part 2: section-route measured offline (parser, router, what the routed part holds; no model calls)

- Command (from `track_2a/`): `EMBED_MODEL_DIR=models/multilingual-e5-small python3 scripts/route_check.py --out <folder>`, 23:36 to about 23:44 UTC, code as committed in `02ecd5d`. Output: `summary.json`, `per_case.jsonl`.
- An earlier run of the same script (23:24, vote-match threshold 85, without the coverage column) gave the same booklet and router numbers but sent 2 cases to the fallback because the dataset's vote name "Modifica del diritto di locazione (Diritto di locazione: sublocazione)" scores 81 against the booklet title "Modifica del Codice delle obbligazioni (Diritto di locazione: sublocazione)"; the threshold is now 80 with a 5-point lead (decision file).

**1. Booklets.** All 44 dev booklets parse completely: 131 of 131 votes pass every check (contents entry complete, page numbers in order, a heading on every start page, a council sub-section, sub-sections that start where the arguments start). No problem was reported.

| Booklet language | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|
| de | 2/2 | 3/3 | 1/1 | 1/1 | 4/4 | 2/2 | 2/2 |
| fr | 2/2 | 3/3 | 1/1 | 1/1 | 4/4 | 1/1 | 2/2 |
| it | 2/2 | 3/3 | 1/1 | 1/1 | 4/4 | 2/2 | 2/2 |

(booklets parsed completely / dev booklets of that year; 2025 French: the 2025-02-09 French booklet is not used by any dev case and was not downloaded)

**2. Claims.** The router assigns a part to all 300 dev claims; no claim is unrouted. Routes: detail 43, council 102, committee 49, law 39, summary 67.
299 of 300 cases are routed; 1 falls back to embed-e5-small: a committee claim on the OECD minimum-tax vote (2023-06-18), which has no committee (its "no" side is a parliamentary minority).

**3. The 201 cases with a gold passage** (200 routed). *Hit*: at least one sent paragraph matches the gold passage under the starter's evidence rule (the paragraph lies inside the passage); this is session 4's hit rate, and since the cited paragraphs are the evidence, also the evidence ceiling. *Coverage*: share of the gold passage's 200-character windows that are in the sent text, among those found anywhere in the booklet. *Pages*: the part's pages hold every page where the gold passage was located. *Inside*: share of sent paragraphs that lie inside the gold passage.

| Routed evidence cases | Cases | Hit | Coverage (mean) | Coverage >= 0.9 | Pages hold gold | Paragraphs inside | Characters sent | Trimmed to 8 |
|---|---|---|---|---|---|---|---|---|
| summary | 55 | 1.000 | 0.921 | 0.418 | 0.873 | 0.458 | 2,246 | 0 |
| council | 68 | 1.000 | 0.945 | 0.882 | 0.765 | 0.964 | 3,141 | 0 |
| committee | 26 | 1.000 | 0.962 | 0.846 | 0.692 | 0.812 | 3,102 | 0 |
| law | 25 | 1.000 | 0.610 | 0.080 | 1.000 | 1.000 | 3,482 | 4 |
| detail | 26 | 1.000 | 0.791 | 0.615 | 0.962 | 0.753 | 5,452 | 8 |
| same-language | 67 | 1.000 | 0.889 | 0.672 | 0.866 | 0.768 | 3,350 | 4 |
| cross-language | 133 | 1.000 | 0.874 | 0.586 | 0.827 | 0.789 | 3,173 | 8 |
| booklet de | 66 | 1.000 | 0.881 | 0.606 | 0.864 | 0.754 | 3,067 | 4 |
| booklet fr | 67 | 1.000 | 0.877 | 0.642 | 0.836 | 0.800 | 3,130 | 4 |
| booklet it | 67 | 1.000 | 0.878 | 0.597 | 0.821 | 0.792 | 3,499 | 4 |
| **all routed** | 200 | 1.000 | 0.879 | 0.615 | 0.840 | 0.782 | 3,233 | 12 |
| embed-e5-small (session 4, for reference) | 201 | 0.741 | – | – | – | – | 5,386 | – |

- **Gate (Rashad): at least 90 % of dev booklets parse (44/44 = 100 %) and the routed part holds the gold passage in at least 0.90 of routed evidence cases (hit 1.000, 200/200). Passed; Part 3 runs.**
- "Pages hold gold" is stricter and lower (0.840): the gold passage starts with the vote's title, whose 200-character window also matches the title page, the law page or the summary next to the part, so a neighbouring page counts as a gold page. Of the 32 cases where it fails, in 31 the part holds some of the gold pages and the others lie within five pages of it (contents, title, summary or law pages that carry the vote's title); in 1 (row 347) the locator placed a detail passage on another vote's page, and a sent paragraph still matches the gold passage.
- Law claims have the lowest coverage (0.610): the four longest law texts (Covid-19 law, 19,000 to 21,000 characters) are cut to the 8 most similar paragraphs, which are short legal clauses (1,300 to 1,900 characters sent), and lines under 40 characters ("Art. 2", "3 Aufgehoben") are dropped by the paragraph splitter. Summary claims get the whole summary spread, of which the gold passage is usually the left page (paragraphs inside 0.458).
- Characters sent: 3,233 on average for routed evidence cases, 3,274 over all 299 routed cases (embed-e5-small: 5,386).
