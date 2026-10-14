### Where session 12's val errors come from, and what kind Apertus says they are (session 13, step 4; offline analysis)

`scripts/error_types.py` on the final session 12 val answers (`2026-10-13_rashad_final-s12_val1160`): 23 task A and 18
task B errors. **Never part of the pipeline.** 21:39 to 21:40 UTC, 31 calls (13 + 18), 1 per second, one backend.

**Routing or reading (no model call).** A task A error with gold 0 or 2 is a *routing error* when its gold passage is
not in the text Apertus read (rapidfuzz partial ratio < 90 after the starter's normalisation; the case prepared again
exactly as the CLI prepares it); every other error is a *reading error* (a gold neutral has no passage to find).
Task B has no routing.

| | Errors | Routing | Reading |
|---|---|---|---|
| Task A | 23 (gold → given: 2→1 13, 2→0 6, 0→1 2, 0→2 2) | **10** (law 5, detail 3, committee 1, fallback 1) | **13** |
| Task B | 18 (1→2 8, 2→0 4, 2→1 3, 0→1 2, 0→2 1) | — | **18** |

Of the 15 task A errors answered neutral, 9 are reading errors and 6 routing errors (the long law and detail parts are
cut to 8 paragraphs, and the passage was not among them).

**Kind of each reading error, named by Apertus** (prompt ERR-type-v1 in the script, `json_schema` enum, one call per
error, the gold label given; 36,026 input and 291 output tokens in all):

| Kind | Task A (13) | Task B (18) |
|---|---|---|
| direction_or_negation | 6 (all gold 2 answered 1) | 1 |
| scope | 5 | 4 |
| number_or_date | 2 | 6 |
| other_ballot_or_topic | 0 | 6 (all gold 1 answered 2) |
| other | 0 | 1 |

These are Apertus's own explanations of known errors, not checked by hand: they describe where the reading fails
(task A: a contradiction by direction or scope read as "not settled"; task B: a passage about another ballot read as
a contradiction), and they decide nothing in the pipeline.
