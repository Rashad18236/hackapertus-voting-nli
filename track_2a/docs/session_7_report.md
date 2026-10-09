# Session 7 report: hardening, a validation set, and the task A default

2026-10-09, from 00:25 UTC, branch `claude/eager-cannon-08bx1h-val` (from the
branch of PR #10, which was merged into `main` at the start of the session).
Run by Rashad, with Claude Code, autonomously on Rashad's instructions. Every
number comes from an actual run, scored with the starter's `evaluate.py`
(commit `559b598`). The test split was never used. Decisions:
`docs/decisions/2026-10-09-0025_rashad_session-7.md`.

Fixed decision (Rashad): task A evidence contains only what Apertus cited.

<!-- SUMMARY -->

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

<!-- PART3 -->
