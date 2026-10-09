# Session 7 report: hardening, a validation set, and the task A default

2026-10-09, from 00:25 UTC, branch `claude/eager-cannon-08bx1h-val` (from the
branch of PR #10, which was merged into `main` at the start of the session).
Run by Rashad, with Claude Code, autonomously on Rashad's instructions. Every
number comes from an actual run, scored with the starter's `evaluate.py`
(commit `559b598`). The test split was never used. Decisions:
`docs/decisions/2026-10-09-0025_rashad_session-7.md`.

Fixed decision (Rashad): task A evidence contains only what Apertus cited.

## 1. In short

- **Hardening (Part 1).** If the new parser or router fails on a booklet, the
  case now runs as `embed-e5-small` instead of getting a neutral answer
  without a model call.
- **Validation set (Part 2).** 580 task A cases from dataset rows that were
  in neither dev nor test and that nobody looked at while writing the router
  and the parser. The router reads all 580 claim openings, and the part it
  picks holds the gold passage in 399 of 400 cases with one.
- **Paired run on val (Part 3).** 300 balanced val cases, same model
  (`swiss-ai/apertus-v1.5-8b`), case by case. Session 6's dev result holds:

| | `section-route` val | `embed-e5-small` val | `section-route` dev | `embed-e5-small` dev |
|---|---|---|---|---|
| **Macro-F1** | **0.956** | 0.865 | 0.953 | 0.834 |
| **Evidence** | **0.946** | 0.588 | 0.905 | 0.662 |
| Input tokens per case | **1,222** | 1,827 | 1,210 | 1,868 |
| p95 time | **3.0 s** | 12.3 s | 3.9 s | 11.7 s |

- **Default (Part 4).** The rule was met (at least 0.90, and at least 0.05
  above `embed-e5-small`): **`section-route` is now the task A default**
  (commit `d69d820`, on its own). All 92 tests and 17 self-checks pass, and
  `make run` answers the example requests in the official format.

## 2. Part 1: a routing error never costs a case

Before: if the booklet parser, the claim router, the vote match or the
building of the paragraph prompt raised an error, `src/cli.py` answered the
case with the fallback label (neutral) without asking Apertus.

Now: any error in these steps makes the case run as `embed-e5-small`, exactly
as when the router finds no part. The case records the error (`route_error`
in the raw answers), each such case is logged as a warning, and the run log
ends with their count ("Routing failed and the case ran as the fallback
variant: n"). An error in `embed-e5-small`'s own selection (for example
missing model files) still gives the documented neutral fallback, as before.

New tests (`tests/test_section_route.py`): two broken booklets make the
parser raise, one with a page number missing inside a vote, one with `None`
as a page's text. For both, the case gets exactly one model call with
`embed-e5-small`'s prompt, keeps its answer and evidence, and is counted in
the log. 92 tests pass.

## 3. Part 2: a validation set

**Why.** Session 6's router and parser were written while looking at the
300 dev cases, and measured on the same cases. A set of cases nobody looked
at shows whether they carry over.

**What.** "val" (`data/val/`, built by `scripts/make_val.py`): the dataset
rows that are in neither dev nor test, without exact duplicates (586 rows),
minus the six rows whose claim openings were used in session 6 to add router
patterns (rows 323, 592, 756, 1068, 1078 and 1301): **580 task A cases**,
labels in a separate file. The cases are the starter's `prepare_cases.py`
lines, unchanged. All of them come from the 15 dev voting dates, so val tests
the router and the routed variant on new claims, not the parser on new
booklets (one booklet, the French 2025-02-09 one, had not been opened before).
Three new self-checks confirm that val has no label fields and shares no row
or booklet with test, and no row with dev.

**Result** (`docs/runs/2026-10-09_rashad_route-check_valA580/`, no model
calls; nothing was changed because of it):

- **All 45 booklets parse** (132 votes).
- **The router assigns a part to all 580 val claims.** 577 cases are routed.
- **3 fall back** to `embed-e5-small`: all three are committee claims on the
  OECD minimum-tax vote (2023-06-18), which has no committee; the same kind of
  case was the one dev fallback.
- **In 399 of the 400 routed cases with a gold passage, a sent paragraph lies
  inside it** (dev: 200 of 200). The one miss is a committee claim on the
  cash initiative (2026-03-08) whose gold passage is the parliamentary debate
  page, which the parser files under "parliament".

| Routed evidence cases | Val cases | Val: a paragraph inside the gold passage | Val characters sent | Dev cases | Dev | Dev characters sent |
|---|---|---|---|---|---|---|
| summary | 111 | 1.000 | 2,129 | 55 | 1.000 | 2,246 |
| council | 117 | 1.000 | 3,125 | 68 | 1.000 | 3,141 |
| committee | 63 | 0.984 | 3,071 | 26 | 1.000 | 3,102 |
| law | 63 | 1.000 | 3,325 | 25 | 1.000 | 3,482 |
| detail | 46 | 1.000 | 5,178 | 26 | 1.000 | 5,452 |
| same-language | 129 | 1.000 | 3,076 | 67 | 1.000 | 3,350 |
| cross-language | 271 | 0.996 | 3,123 | 133 | 1.000 | 3,173 |
| **all** | **400** | **0.998** | **3,108** | **200** | **1.000** | **3,233** |

## 4. Part 3: the paired run on val (E6)

`docs/runs/2026-10-09_rashad_section-route-vs-embed_valA300/` (both arms,
`NOTES.md`, `paired_analysis.json`).

**Setup.** 300 of the 580 val cases, balanced over label, claim language and
booklet language in the same way as dev (seed 42): 105 entailment, 96
neutral, 99 contradiction, 204 with a gold passage. For each case both
settings ran one after the other, the order alternating from case to case.
Model `swiss-ai/apertus-v1.5-8b` on Public AI for all 600 calls (it was up,
so the thinking model was not needed); 0 failed calls, 0 unparseable
answers. 00:38 to 01:04 UTC. Both arms as in session 6: `section-route`
(prompt `A-v4-section-route`, cited paragraphs as evidence; 299 cases routed,
1 fell back) against `embed-e5-small` (prompt `A-v3-excerpts`, evidence
`cited-pieces`).

**Labels**, val next to session 6's dev run (E5):

| | `section-route` val | `embed-e5-small` val | `section-route` dev | `embed-e5-small` dev |
|---|---|---|---|---|
| Macro-F1 | **0.956** | 0.865 | 0.953 | 0.834 |
| F1 entailment | 0.976 | 0.901 | 0.965 | 0.832 |
| F1 neutral | 0.955 | 0.883 | 0.947 | 0.850 |
| F1 contradiction | 0.936 | 0.811 | 0.947 | 0.819 |

Confusion matrices on val (rows: gold; columns: predicted entailment /
neutral / contradiction):

| gold | `section-route` | `embed-e5-small` |
|---|---|---|
| entailment (105) | 103 / 1 / 1 | 96 / 4 / 5 |
| neutral (96) | 0 / 96 / 0 | 0 / 87 / 9 |
| contradiction (99) | 3 / 8 / 88 | 12 / 10 / 77 |

As on dev, `section-route` never calls an unrelated claim entailed or
contradicted, and most of its few errors (9 of 13) call a supported or
refuted claim neutral.

**Evidence, tokens, time:**

| | `section-route` val | `embed-e5-small` val | `section-route` dev | `embed-e5-small` dev |
|---|---|---|---|---|
| Evidence score | **0.946** (193/204) | 0.588 (120/204) | 0.905 (182/201) | 0.662 (133/201) |
| Mean input tokens | **1,222** | 1,827 | 1,210 | 1,868 |
| Median time | 1.5 s | 1.8 s | 1.6 s | 1.9 s |
| p95 time | **3.0 s** | 12.3 s | 3.9 s | 11.7 s |

**By claim type** (Macro-F1; evidence found / gold cases on val):

| Claim type | Val cases | `section-route` val | `embed-e5-small` val | Evidence val | `section-route` dev | `embed-e5-small` dev |
|---|---|---|---|---|---|---|
| summary | 60 | 0.924 | 0.794 | 50/52 vs 20/52 | 0.929 | 0.789 |
| council | 88 | 0.974 | 0.938 | 54/57 vs 37/57 | 1.000 | 0.852 |
| committee | 53 | 0.942 | 0.853 | 28/30 vs 21/30 | 0.960 | 0.863 |
| law | 51 | 0.983 | 0.806 | 34/35 vs 23/35 | 0.944 | 0.668 |
| detail | 48 | 0.912 | 0.814 | 27/30 vs 19/30 | 0.817 | 0.818 |

**By language:** same-language 0.970 against 0.858 (dev 0.930 against
0.910), cross-language 0.949 against 0.867 (dev 0.965 against 0.796). By
booklet and claim language, `section-route` is better in 8 of the 9 pairs;
French booklet with German claim is about even (0.939 against 0.942). German with
German, the one pair it lost on dev, is a clear win on val (0.970 against
0.878).

**Where one was right and the other wrong** (300 cases): both right 255,
**only `section-route` right 32**, only `embed-e5-small` right 5, both wrong
8 (sign test on the 37 cases where they differ: p < 0.00001; dev: 45
against 9). `section-route` is alone right in 8 summary, 4 council, 5
committee, 10 law and 5 detail cases; `embed-e5-small` in one case of each
type.

**What differed from dev.** Very little. The gap in Macro-F1 is a bit
smaller on val (+0.091 against +0.119), because the control arm does better
on val (0.865 against 0.834). The two sets are different cases, so these
absolute numbers do not compare; only the arms of each run do. Detail, the
weak part on dev (0.817), is better on val (0.912).

## 5. Part 4: the default

Rashad's rule: if `section-route`'s Macro-F1 on val is at least 0.90 and at
least 0.05 above `embed-e5-small`'s, make it the default. It is 0.956, 0.091
above. So:

- **`section-route` is the task A default** (`Settings.context_a` in
  `src/cli.py`, commit `d69d820`, on its own).
- A case it cannot route, or whose routing raises an error, runs exactly as
  `embed-e5-small` with evidence `cited-pieces`; a routed case's evidence is
  the paragraphs Apertus cited.
- After the change: 92 tests pass; the 17 self-checks pass (including the new
  val checks); the Docker image was rebuilt and `make run` answered the two
  example requests in the official format (format check clean). The task A
  example took 4.1 s and 1,237 input tokens; its evidence is the cited
  paragraph, page 59.

## 6. What stays unverified

- **The organisers' held-out set.** Val shows the router works on claims it
  was not written for, but all val claims come from the same dataset and
  the same 15 booklets as dev. If the private set's claims open differently,
  more cases fall back to `embed-e5-small` (still answered, not better). If
  its booklets are laid out differently, the parser gives no parts and the
  case falls back too.
- **Booklets the parser has never seen.** Val opened one new language
  version (French, 2025-02-09), which parsed; the test booklets were not
  opened.
- **Docker on a clean machine.** The image was built here through a sandbox
  wrapper that adds this session's proxy certificate, and run with host
  networking. A plain `make build && make run` elsewhere was not tried.
- **The evaluation model and server.** Both paired runs used Public AI's
  `apertus-v1.5-8b` at night; which Apertus model and server the organisers
  use is unknown.
- **The official scorer.** Only the starter's `evaluate.py` was available.
  It does not check evidence pages; `section-route`'s pages are the pages
  the paragraphs come from (a recommendation box carries its summary page).
- **Committee claims on a vote without a committee** (3 val cases, 1 dev
  case) and **committee claims whose gold passage is the parliamentary
  debate** (1 val case) are not handled by the router; they fall back or
  miss. Not changed, as agreed: val is for measuring.
- **Long detail and law parts** are still cut to the 8 most similar
  paragraphs (31 of 400 routed val evidence cases).
