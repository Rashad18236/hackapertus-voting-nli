### AP-structure: Apertus reads the booklet's contents, against the Python parser (session 11 step 3a)

**What it is.** One call per booklet (`src/ap_parse.py`, `structure()`): the first six pages (the pages the parser
reads for the contents), each with a page marker, and a JSON schema asking for every vote in the contents with its
title and the start pages of its summary, detailed explanation, arguments and text put to the vote (null if the
contents give none). The answer is cached per booklet, so its tokens count once per booklet and are spread over
that booklet's cases. Before any part is used, Apertus's entries go through the parser's own checks
(`booklet_from_entries` → `booklet._parse_vote`: every start page must carry its heading, pages in order, the
arguments' sub-sections must agree).

**Set.** The 93 booklets of step 1 (every federal booklet 2016–2026 in de, fr and it, sealed dates excluded),
22:18 to 22:33 UTC, all 93 answers from one backend (blablador `vllm-0.23.1rc1`), 0 failed calls, 0 unreadable
answers. Votes are matched by their order (Apertus's entries sorted by summary page). The JSON holds numbers and
field names only (no titles).

| Measure | Result |
|---|---|
| Current layout (2018 on), votes that pass the parser on a date without a cross-language disagreement | 178 |
| … all four start pages equal to the parser's | **78.7 %** (de 53/60, fr 43/59, it 44/59) |
| … per field: summary / detail / arguments / law | 83.7 % / 78.7 % / 80.3 % / 79.2 % |
| … booklets with every vote equal | 54 of 66 |
| Older layout (2016 to mid-2018, no per-part contents entries): law page equal | 30.3 % of 66 votes |
| Booklets where Apertus lists as many votes as the parser | 94.6 % |
| Votes the parser fails (5): Apertus's entry passes every check | 1 (`2025_09_28_fr` vote 1, the probe's cause, which step 1 already fixed); it adds no valid part the parser lacks |
| Tokens per booklet, input + output | **1,796 + 176** (about 265 + 26 per case on dev, 6.8 cases per booklet) |

By year, all pages equal: 2018 17/17, 2019 9/9, 2020 11/21, 2021 26/39, 2022 6/9, 2023 8/9, 2024 35/36, 2025 11/14,
2026 17/24. Misses spread over all four fields (detail 38, law 37, arguments 35, summary 29 of 178 votes); a wrong
summary page also shifts the order matching, so one reading error can count against several votes.

**HYBRID RULE, part a.** AP-structure would need ≥ 95 % of its votes equal to the parser's where the parser passes;
it reaches 78.7 %. So AP-structure **cannot become the step after the parser**, whatever run 3 shows; run 3 is
still run, to report its effect on Macro-F1 and evidence when the parser is off. How many of the wrong pages the
heading checks reject is not measured here (Apertus's entries are not stored); run 3 shows what reaches the model.
