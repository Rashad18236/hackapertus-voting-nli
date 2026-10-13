### Task A reading: CS and SL against today, on dev, the on-topic neutral set and val (session 10, step 6)

**Endpoint check** (`schema_check.json`, `scripts/schema_check.py`, 5 real calls): Public AI enforces a schema
with `anyOf`. The coupled schema (a neutral answer cites no paragraph; an entailment or contradiction cites one to
three) was accepted, and three requests that told the model to answer a forbidden combination all came back
schema-conformant (asked `{"paragraphs": [], "label": 0}`, got `{"paragraphs": [0], "label": 0}`). So CS was run.

**Versions** (all off by default, in `src/cli.py` / `src/nli.py`):

- **CS:** today's prompt with the coupled schema (`nli.ANSWER_SCHEMA_A_COUPLED`).
- **SL:** when Apertus answers neutral but cites paragraphs, one more call with only the cited paragraphs and the
  claim (prompt `A-v4-second-look-cited`: `A-v4-second-look` with its first sentence adapted; all three labels
  allowed). An entailment or contradiction in the second answer replaces the neutral one; it is Apertus's label.

**The on-topic neutral set** (`data/ontopic_neutral/`, `scripts/make_ontopic.py`, indicative only): 46 routed dev
cases with gold 0 or 2 whose gold passage lies in the routed part; every paragraph that overlaps the gold passage
(rapidfuzz partial ratio ≥ 90 either way, or a 60-character window of it inside the passage) is removed before any
length cut, and a case is kept if at least three paragraphs remain. The right answer is then neutral: the model
reads the part the claim names, without the passage the claim came from. Run with the test-only option
`scripts/paired_run.py --exclude-paragraphs`; `src/` is unchanged.

**Dev run** (this folder): all 300 dev task A cases and the 46 on-topic cases, three arms interleaved, one request
per second (SL's second calls paced too); all 1,038 answers from one backend (blablador); 0 failed calls.

| arm | dev Macro-F1 | dev evidence | dev neutral recall | input + output tokens (dev) | fixes / breaks (dev) | on-topic: answered neutral |
|---|---|---|---|---|---|---|
| today | 0.983 | 0.985 | 1.000 | 1,237.8 + 14.5 | | 31 of 46 (0.674) |
| CS | 0.983 | 0.990 | 0.990 | 1,237.8 + 14.5 | 1 / 1 | 28 of 46 (0.609) |
| SL | **0.987** | 0.990 | 1.000 | 1,241.1 + 14.6 | 1 / 0 | 31 of 46 (0.674) |

SL made 5 second calls (2 on dev, 3 on the on-topic set); one turned a neutral into a right contradiction. CS
changed one wrong label to right and one right to wrong on dev, and turned 3 on-topic neutral answers into
contradictions: it fails rule (d) (on-topic share 0.065 below today's, limit 0.05). SL goes to val.

**Val run** (`2026-10-12_rashad_reading-A_valA580`): all 580 val task A cases, today and SL; all answers from
one backend.

| arm | val Macro-F1 | evidence | neutral recall | input + output tokens | fixes / breaks |
|---|---|---|---|---|---|
| today | 0.959 | 0.958 | 1.000 | 1,205.8 + 14.5 | |
| SL | 0.962 | 0.960 | 1.000 | 1,215.0 + 14.8 | 2 / 0 |

SL made 11 second calls on val: 2 became right (an entailment, a contradiction), 9 stayed neutral.

**PAIRED RULE for SL:** (a) val Macro-F1 +0.005: **+0.0034, fails**; (b) dev at most 0.004 lower: +0.0034, holds;
(c) over dev and val more fixes than breaks with the exact two-sided sign test p ≤ 0.10: 3 fixes, 0 breaks,
**p = 0.25, fails**; (d) input tokens +0.3 % (dev) and +0.8 % (val), at most +3 %: holds; neutral recall 1.000:
holds; on-topic share unchanged: holds. **SL stays off; CS stays off.** Nothing changes in step 6.

**The Python rule "neutral with a citation → contradiction", scored offline from today's saved answers only**
(`python_rule_offline.json`; never in `src/`): dev 0.9833 → 0.9834 (2 changes: 1 right, 1 wrong); on-topic
neutral set 31 → 28 of 46 answered neutral (3 changes, all wrong); val 0.9589 → 0.9728 (13 changes: 10 right, 2
wrong, 1 wrong either way; neutral recall 1.000 → 0.989). On val the rule would gain more than SL, because
Apertus, asked again, keeps 9 of its 11 neutral answers; on the on-topic set it is wrong every time it acts.
