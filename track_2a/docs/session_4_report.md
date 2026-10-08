# Session 4 report: why the embedding was wrong, a search grid, and the new default

2026-10-08, from 18:57 UTC, branch `claude/eager-cannon-08bx1h-search` (stacked on PR #7).
Run by Rashad, with Claude Code. All numbers come from actual runs on the dev
split, scored with the starter's `evaluate.py`; the test split was never run.
Every run has a folder in `docs/runs/` (`run.json` and `NOTES.md`); every
decision is in `docs/decisions/2026-10-08-1857_rashad_session-4.md`.

## 1. In short

- **Most wrong answers are reading errors, not search misses.** Of the 84
  wrong answers of the embedding in E3, the search missed the gold passage
  only 18 times; in 66 the passage was sent (or the claim was neutral) and
  Apertus still answered wrongly, most often calling a true statement a
  contradiction.
- **A wider search finds more but does not answer better.** The offline grid
  found a setting that puts the gold passage in front of the model far more
  often (84.6 % instead of 74.1 % of cases), but in the paired run Apertus
  scored lower with it (Macro-F1 0.674 against 0.711).
- **The evidence score can rise without new model calls.** Filling the free
  evidence slots with the next most likely pages lifted E3's evidence score
  from 0.383 to 0.522. The starter's scorer does not penalise extra items.
- **New default for task A: `embed-e5-small`** (was `vote-section`, which
  scores 0.561 on the current server, below the 0.60 minimum).

## 2. Every task A variant measured so far

"Paired" rows ran both settings on each case back to back (the only fair
comparison, because the endpoint drifts). "Server" says which Apertus
answered:

- *before 13:25*: Public AI's `apertus-v1.5-8b` before about 13:25 UTC. At
  that time it answered differently: E2's first half was shown to differ.
  The session 2 runs and E1 ran before that time, but were not checked
  against later runs.
- *current 8B*: the same model name after about 13:25 UTC.
- *8B thinking*: `apertus-v1.5-8b-thinking`, used when the 8B was down. With
  the json_schema answer it answers like the current 8B.

| When (UTC) | Run (`docs/runs/`) | Context variant | Answer format | Cases | Paired | Server | Macro-F1 | Evidence | Input tokens | p95 time |
|---|---|---|---|---|---|---|---|---|---|---|
| 06:39 | `s2-A60-A-v3-fulldoc` | full | JSON by prompt, 64 tokens | 60 | no | before 13:25 | 0.767 | 0.375 | 41,124 | 23.3 s |
| 06:39 | `s2-A300-A-v3-fulldoc` | full | JSON by prompt, 64 tokens | 300 | no | before 13:25 | 0.589 | 0.209 | 39,706 | 30.3 s |
| 06:39 | `s2-A300-A-v3-fulldoc-reparsed` | full | same answers, prose-label parser | 300 | no | before 13:25 | 0.608 | 0.209 | 39,706 | 30.3 s |
| 07:38 | `s2-A60-A-v3-fulldoc-max256` | full | JSON by prompt, 256 tokens | 60 | no | before 13:25 | 0.398 | 0.150 | 41,124 | 31.7 s |
| 07:53 | `s2-A60-A-v3-fulldoc-jsonmode_attempt1` | full | JSON mode (27 % failed calls) | 60 | no | before 13:25 | 0.378 | 0.125 | 21,041 | 58.3 s |
| 11:47 | `s3-E1-A60/fulldoc-prompt` | full | JSON by prompt, 64 tokens | 60 | yes (E1) | before 13:25 | 0.817 | 0.350 | 39,077 | 18.7 s |
| 11:47 | `s3-E1-A60/fulldoc-schema` | full | json_schema, 128 tokens | 60 | yes (E1) | before 13:25 | 0.850 | 0.325 | 39,834 | 18.0 s |
| 12:06 | `s3-E2-A300/fulldoc-schema` | full | json_schema | 300 | yes (E2) | mixed: cases 1 to ~150 before 13:25, rest current 8B | 0.669 | 0.284 | 39,206 | 37.1 s |
| 12:06 | `s3-E2-A300/section-schema` | vote-section | json_schema | 300 | yes (E2) | mixed, as above | 0.732 | 0.224 | 15,868 | 13.5 s |
| 13:46 | `s3-A300-embed-e5-small` (Kaan) | embed-e5-small | JSON by prompt, 64 tokens | 300 | no | current 8B | 0.767 | 0.383 | 1,868 | 14.4 s |
| 17:01 | `…_embed-vs-section_devA300/vote-section` | vote-section | json_schema | 300 | yes (E3) | current 8B (cases 1 to 180), 8B thinking (181 to 300) | 0.561 | 0.095 | 15,863 | 9.3 s |
| 17:01 | `…_embed-vs-section_devA300/embed-e5-small` | embed-e5-small | json_schema | 300 | yes (E3) | as above | 0.721 | 0.383 | 1,831 | 16.1 s |
| 17:01 | `…_evidence-padding-e3_devA300/vote-section` | vote-section | E3's answers, evidence padded | 300 | re-score | as E3 | 0.561 | 0.264 | 15,863 | 9.3 s |
| 17:01 | `…_evidence-padding-e3_devA300/embed-e5-small` | embed-e5-small | E3's answers, evidence padded | 300 | re-score | as E3 | 0.721 | 0.522 | 1,831 | 16.1 s |
| 18:18 | `…_thinking-equivalence_devA20` (2 arms) | vote-section, embed-e5-small | json_schema | 20 | yes (check) | 8B thinking | 0.379 / 0.520 | 0.077 / 0.385 | 14,729 / 1,832 | 5.1 / 15.5 s |
| 19:47 | `…_section-k12-vs-embed-thinking_devA300/embed-e5-small` | embed-e5-small | json_schema | 300 | yes (E4) | 8B thinking | **0.711** | 0.373 | **1,868** | 11.4 s |
| 19:47 | `…_section-k12-vs-embed-thinking_devA300/vote-section-embed-e5-small-k12` | vote-section-embed-e5-small-k12 | json_schema | 300 | yes (E4) | 8B thinking | 0.674 | **0.403** | 2,777 | **5.8 s** |

Rows from different runs, and especially from different servers, should not
be compared with each other; only the arms of one paired run compare. The
20-case check's Macro-F1 is not meaningful on its own (it checks agreement).
Offline measurements (no model calls) are in `docs/results.md`: the
retrieval checks and the 72-setting search grid
(`2026-10-08_rashad_search-grid_devA201`).

## 3. What was done, in plain words

**Part 1: why the embedding was wrong** (`2026-10-08_rashad_e3-embed-errors_devA300`).
For every wrong answer of the embedding in E3, we rebuilt exactly the text
pieces Apertus had seen and checked whether the gold passage was among them.

| Wrong answers | Search miss (passage not sent) | Reading error (passage sent) |
|---|---|---|
| true statement (entailment) | 7 | 27 |
| contradicting statement | 11 | 12 |
| unrelated claim (neutral; nothing to find) | – | 27 |
| same-language / cross-language | 2 / 16 | 26 / 40 |

The search fails mostly when claim and booklet are in different languages;
Apertus fails mostly by calling a true statement a contradiction (21 times
with the passage in front of it).

**Part 2: offline search grid** (`2026-10-08_rashad_search-grid_devA201`). 72
ways of choosing booklet text, with two local embedding models (e5-small and
IBM's Granite, whose output we first checked against its model card), from
the whole booklet or only the vote's section, with 4, 8 or 12 pieces, with or
without the neighbouring pieces, and three rules for cross-language claims.
No setting met all targets: the pages sent contain the gold passage often
enough (evidence ceiling 0.80) only when at least 28 % of the booklet is
sent, far above the 10 % limit. Under the limit, the best was e5 on the vote
section with 12 pieces (hit rate 0.846 instead of 0.741, 9.6 % of the
booklet), registered as `vote-section-embed-e5-small-k12`. Granite is not
better under the limit and stays out of the Docker image.

**Part 3: evidence padding** (`2026-10-08_rashad_evidence-padding-e3_devA300`).
The starter's scorer counts a case as found when any of the first five
evidence items matches, and gives no penalty for extra items. Re-scoring E3's
saved answers with the free slots filled by the next most similar pages
raised the evidence score from 0.383 to 0.522 (embedding) and from 0.095 to
0.264 (vote section), with every label unchanged. It is now a setting
(`--evidence-a cited-then-retrieved`), off by default.

**Part 4: paired run** (E4,
`2026-10-08_rashad_section-k12-vs-embed-thinking_devA300`). The grid's choice
against `embed-e5-small`, all 300 cases, on the 8B thinking model (the 8B was
down; Rashad asked to run on the thinking model straight away), 0 failed
calls. The new setting lost: Macro-F1 0.674 against 0.711 (more than the
allowed 0.02 lower), although its evidence was better (0.403 against 0.373)
and its p95 time lower (5.8 s against 11.4 s, all from embedding whole
booklets on first cases). With more text Apertus answers "contradiction"
more often.

**Part 5: default.** `embed-e5-small` is now the default (`src/cli.py`, its
own commit). All 70 tests pass and `make run` exits 0 with the two example
requests in the official format.

## 4. Recommendation

Use `embed-e5-small` with json_schema answers as the task A default, because
it is the only variant that was measured paired against both alternatives
on the current server and won both times (0.721 against 0.561, 0.711 against
0.674) while sending under 2,000 input tokens per case. Switch on the padded
evidence (`cited-then-retrieved`) as soon as the organisers confirm that
extra evidence items are not penalised, because it raised the evidence score
from 0.383 to 0.522 without changing a single label. Put the next effort into
how Apertus reads the passages (true statements called contradictions), not
into search, because 66 of 84 wrong answers were reading errors.

## 5. What could not be verified in this sandbox

- **Docker as the judges run it.** The image was built here only through a
  sandbox wrapper that adds this session's proxy certificate
  (`sandbox_build.sh`, not in the repository), and run with host networking.
  A plain `make build` and `make run` on a clean machine was not tried. The
  image is 2 GB (the e5 model is inside).
- **The judges' hardware.** All times come from this 4-core host, and the
  paired runs ran on the host, not in Docker. The one-off embedding of a
  booklet (8.6 s on a first case here) depends on the CPU.
- **The evaluation model and server.** E4 ran on `apertus-v1.5-8b-thinking`
  because the 8B was down from about 17:30 until at least 19:44 UTC (it
  answered again at 20:20). Public AI also changed what it serves as the 8B
  at about 13:25. Which model and server the organisers use is unknown, so
  absolute scores may differ there.
- **The official scorer.** Only the starter's `evaluate.py` was available;
  whether the official evaluation penalises extra evidence, or checks pages,
  is unknown.
- **Token counts** are as reported by Public AI; the organisers' proxy counts
  its own.
- **Overfitting.** The grid and the vote-section selector were tuned on the
  same 300 dev cases they were measured on; only the test split (never run)
  would show how well they carry over.
- **Granite's ONNX file** matched its model card's example within 0.0016,
  but was not compared with the original PyTorch weights.
- **The dataset README** was not checked again this session for label
  definitions.

## 6. Open questions for the organisers

1. Which Apertus model and server does the evaluation call: `apertus-v1.5-8b`
   or another v1.5 variant, on CSCS or Public AI? Is `MODEL` set for us?
2. Does the official evaluation, like the starter, count a case when any of
   the first five evidence items matches, without penalising extra items?
   Does evidence on a neutral answer count?
3. Is the evidence page checked against the 1-based PDF page?
4. How are Macro-F1, tokens and time combined into one score, and does the
   time include local work such as embedding the booklet?
5. On what hardware (CPU cores, memory) and with which time limits does the
   Docker image run? Is a 2 GB image acceptable?
6. Where are the dataset's label definitions (the README holds only the
   licence)?
