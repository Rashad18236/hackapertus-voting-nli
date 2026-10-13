### Parser coverage on every booklet from 2016 to 2026, before and after the session 11 fixes (step 1, no model)

**Booklets.** Every federal voting booklet in the Federal Chancellery's collection from 2016-02-28 to 2026-06-14, plus
2026-09-27 (on admin.ch, not yet in the collection), in German, French and Italian: 31 voting dates, 93 PDFs
(`scripts/fetch_unseen_booklets.py --since 2016 --out <folder outside the repository>`). The three sealed test dates
(2020-02-09, 2022-02-13, 2022-05-15) are dropped from the list before any request: never downloaded, parsed or
opened. The dev, val and probe booklets are among the 93. The PDFs and their text are not committed; the JSON files
here hold only numbers, part names and the parser's own problem messages (`scripts/parser_coverage.py`).

**Cross-language check (without labels).** The de, fr and it booklets of one date print the same votes and parts,
so they must agree on the number of votes, the parts each vote has and each part's start page (within one page).
A disagreement is a parser gap in at least one language.

**Before** (`main` at `014f691`, `coverage_before.json`): 64 of 93 booklets complete; 180 votes found, 178 pass.
**After** (this branch, `coverage_after.json`): **88 of 93 complete; 249 votes found, 244 pass every check, all 249
have at least one usable part; 0 dates with a cross-language disagreement.** Booklets complete (all votes pass)
by year and language:

| Year | de before → after | fr before → after | it before → after | votes passing (after) |
|---|---|---|---|---|
| 2016 | 0/4 → 4/4 | 0/4 → 4/4 | 0/4 → 4/4 | 39/39 |
| 2017 | 0/3 → 2/3 | 0/3 → 2/3 | 0/3 → 2/3 | 15/18 |
| 2018 | 2/4 → 4/4 | 2/4 → 4/4 | 1/4 → 3/4 | 29/30 |
| 2019 | 2/2 → 2/2 | 2/2 → 2/2 | 2/2 → 2/2 | 9/9 |
| 2020 | 2/2 → 2/2 | 2/2 → 2/2 | 2/2 → 2/2 | 21/21 |
| 2021 | 4/4 → 4/4 | 4/4 → 4/4 | 4/4 → 4/4 | 39/39 |
| 2022 | 1/1 → 1/1 | 1/1 → 1/1 | 1/1 → 1/1 | 9/9 |
| 2023 | 1/1 → 1/1 | 1/1 → 1/1 | 1/1 → 1/1 | 9/9 |
| 2024 | 4/4 → 4/4 | 4/4 → 4/4 | 4/4 → 4/4 | 36/36 |
| 2025 | 3/3 → 3/3 | 2/3 → 2/3 | 3/3 → 3/3 | 14/15 |
| 2026 | 3/3 → 3/3 | 3/3 → 3/3 | 3/3 → 3/3 | 24/24 |

(2020 has two dates here: 2020-02-09 is sealed. The votes column counts the votes found after; before, the 27
booklets of 2016 to mid-2018 gave no votes at all.)

**Distinct causes before, most frequent first, and the fix** (each a general cause with a unit test on a synthetic
page or PDF; no booklet-specific code):

| Cause | Booklets before | Fix | After |
|---|---|---|---|
| No contents entry found: the older layout (until 2018-06-10) lists one entry per vote ("Informationen zur Vorlage Seiten 4–11", "Explications pages …", "Spiegazioni pagine …") and its legal text, not the four part entries | 20 | `_parse_old_layout`: that contents grammar; inside the vote's pages each part starts on a page whose heading names it (a whole line, anywhere on the page); wordings incl. "Argumente von Bundesrat und Parlament"; stray spaces inside words ("Sei ten") tolerated; a legal text belongs to the vote whose pages hold it, else to the entry before it | 0 |
| PDF text not readable: a font descriptor names two embedded programs of one font (/FontFile and /FontFile3); pypdf 6 refuses the page, and so the whole booklet | 7 (2016-09-25, 2018-03-04, 2018-06-10 de) | `parse.extract_pages`: keep one program per descriptor in the reader's copy and read the page again; a page that still fails gets empty text instead of failing the booklet | 0 (the 7 now parse in the older layout) |
| No arguments heading on the contents' arguments page (the text layer lost the heading) | 1 (2018_09_23_it) | the arguments' start also counts as confirmed when the detail page's list of sub-sections names the same page; the problem stays listed | vote not "ok", all its parts valid |
| Contents entry without arguments (the text layer dropped the line) | 1 (2025_09_28_fr, the probe) | **per-part validity** (step 1e): a vote keeps every part that passes its own checks; without the arguments entry, the arguments start at the earliest sub-section the detail page's list and the headings give, if that page carries an arguments heading | vote not "ok", all its parts valid |

**Per-part validity (1e).** `Vote.valid` holds the parts that passed their own checks (all parts when `Vote.ok`);
section-route routes a claim to its part when the part is valid (before: only when the whole vote passed). For the
178 votes that passed before, every part's pages are unchanged (checked: 178 of 178).

**Remaining causes after** (`coverage_after.json`): 2017-09-24 vote 2 (two linked pension votes in one block; no
"Vorlage im Detail" heading in de, fr or it: 3 booklets; its summary, arguments and law are valid); 2018_09_23_it
and 2025_09_28_fr as above (all parts valid, the problem listed).

**Effect on cases.** G1 and G2 against `2026-10-12_rashad_prompt-snapshot-final-s10_devAB-valA` pass
(`gates_g1_g2.json`): all 1,180 dev and val requests, labels and evidence unchanged (their 4 fallbacks are not
structure failures). On the probe (`route_check_probe_after.json`, `scripts/route_check.py`): **90 of 94 task A cases
routed, 83 before**; 7 cases move from the fallback to the routed path: rows 1058 (summary), 1123, 1220, 1420, 584
(council), 1247 (law), 208 (summary), all in `2025_09_28_fr`; the 8th case of that vote is a committee claim on a vote
without a committee (still a fallback, as are 3 such claims elsewhere). Every routed probe case with a gold passage
has it among the paragraphs sent (63 of 63).
