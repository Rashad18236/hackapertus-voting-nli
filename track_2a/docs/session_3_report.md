# Session 3 report: reliable task A answers and selected context

2026-10-08, from 11:44 UTC, branch `claude/eager-cannon-08bx1h`. All numbers
come from actual runs on the dev split, scored with the starter's official
`evaluate.py`; the test split was never run. Model: `swiss-ai/apertus-v1.5-8b`
on Public AI. Every comparison is **paired**: both configurations run on the
same case back to back, alternating which goes first, because the endpoint's
output drifted over time in session 2. Decisions with reasons are in
`docs/decisions.md` ("Session 3"); every run is a row in `docs/results.md`.

## 1. Headline

- **Task A answers are now always valid JSON.** Schema-constrained output
  (`json_schema`) removed every unparseable answer (E1: 0 against 3 of 60) and
  is the new default.
- **The central experiment: the vote's section beats the whole booklet**
  (E2, all 300 task A dev cases, paired):
  - Macro-F1 **0.732 against 0.669**, both above the 0.60 minimum;
  - **60 % fewer input tokens** (15.9k against 39.2k per case);
  - p95 time **13.5 s against 37.1 s**.
- **One cost: the evidence score drops** (0.224 against 0.284). The model
  cites the front summary pages more often in the shorter context.
- **New task A defaults:** json_schema answers and `vote-section` context.
  Task B is unchanged (0.947 with `v3-topic-first`).

## 2. Step 1 (approach 1a): schema-constrained answers

In session 2, 37 % of task A answers were prose instead of JSON and fell back
to neutral. Now the endpoint is asked for a strict JSON Schema
(`{"pages": up to 5 integers, "label": 0, 1 or 2}`), so it can only produce a
valid answer.

| E1, 60 dev cases, paired | Answer format by prompt (old) | json_schema (new default) |
|---|---|---|
| Macro-F1 (official) | 0.817 | **0.850** |
| Unparseable answers | 3 | **0** |
| Failed calls (HTTP 504 after the retry) | 2 | 1 |
| Evidence score | 0.350 | 0.325 |
| Mean / p95 time | 10.2 s / 18.7 s | **7.0 s** / 18.0 s |
| Mean input tokens | 39,077 | 39,834 |

On the 58 cases where both arms got an answer: 0.846 against 0.863. The
control produced far fewer prose answers today than in session 2 (3 of 60
instead of 43 %), the drift that made pairing necessary.

## 3. Step 2 (approach 2a): the vote's section instead of the whole booklet

### How the context is selected (`src/context.py`; since the restructuring later on 2026-10-08, `src/contexts/vote_section.py`)

A voting booklet covers several ballots. Every page of a ballot's part starts
with a running header naming it ("Deuxième objet : loi sur la chasse",
"Erste Vorlage: Bargeld-Initiative", "Primo oggetto: Sublocazione"), in the
booklet's language, like the `vote` field. The selector, with no model call
and no embeddings:

1. keeps every page that contains the full vote title (fuzzy match);
2. keeps every page whose header shares enough distinctive words with the
   vote title (words weighted by how rare they are among the booklet's
   headers; the threshold comes from the running-header pages);
3. adds the facing page of each kept page;
4. fills gaps of up to 10 pages between kept pages (pages such as "Arguments
   of the Federal Council" inside a section do not repeat the ballot's name);
5. falls back to the whole booklet if nothing matches.

It was designed and measured **offline** first, against the pages that match
the gold passage under the official rule (169 of the 201 gold
entailment/contradiction dev cases have such a page):

| Selector variant | Gold page inside the selection | Share of the booklet's text sent |
|---|---|---|
| header score only | 0.72 | 24 % |
| + gap filling (8 pages) | 0.959 | 34 % |
| gap 10 | 0.988 | 37 % |
| **chosen: threshold from running-header pages, gap 10** | **0.988** | **47 %** |

The chosen rule is less greedy than the 37 % variant on dev, but it does not
drop a section when the full title is far from the running headers (a unit
test with a small two-ballot booklet showed that failure). Recall is stable
across booklet dates (0.980 / 1.000 on two halves) and languages (de 0.983,
fr 0.981, it 1.000).

### E2: the central comparison (all 300 task A dev cases, paired, both with json_schema)

| | Full booklet | Vote section |
|---|---|---|
| **Macro-F1 (official)** | 0.669 | **0.732** |
| F1 entailment / neutral / contradiction | 0.700 / 0.723 / 0.583 | 0.845 / 0.674 / 0.676 |
| Macro-F1 on the 292 cases both arms answered | 0.674 | **0.741** |
| **Evidence score (official)** | **0.284** (57/201) | 0.224 (45/201) |
| Failed calls / unparseable answers | 7 / 0 | 6 / 0 |
| **Mean input tokens per case** | 39,206 | **15,868** (−60 %) |
| Total input tokens (300 cases) | 11.76M | **4.76M** |
| **Mean / p95 time** | 12.7 s / 37.1 s | **8.2 s / 13.5 s** |
| Booklet pages sent (mean share) | 100 % | 55 % |
| Same-language / cross-lingual Macro-F1 | 0.725 / 0.640 | 0.737 / 0.727 |
| By booklet language (de / fr / it) | 0.681 / 0.624 / 0.699 | 0.723 / 0.702 / 0.768 |

Notes:
- **Where the arms disagree** (92 of 292 cases), the section is right 49
  times and the full booklet 30 times. The biggest gains are on entailment
  and contradiction, and on cross-lingual cases (0.640 → 0.727).
- **Neutral gets worse:** 34 gold-neutral cases called contradiction,
  against 20 with the full booklet. In a shorter context an unrelated claim
  looks more like a conflict.
- **Why evidence drops:** with the section, the model's first cited page is
  more often on the front summary pages (65 of 145 cases against 50 of 147).
  Those pages cannot simply be removed: for 47 of the 169 gold cases with a
  gold page, the gold page is *only* on the front summary. Removing the
  first 15 % of pages would drop the selector's recall from 0.988 to 0.710.
- **Outage:** Public AI had an outage during E2 (12:37 to 13:03 UTC). The
  run was paused and resumed (`--resume`), and nothing was re-run. 13 calls
  failed in total, spread evenly over both arms.

## 4. What we kept

- **json_schema answers for task A** (default since E1).
- **`vote-section` context for task A** (default since E2). It wins on the
  primary metric, tokens and time. The evidence score drops, as recorded
  above.
- **The tools behind the experiments:** `src/context.py` (the selector, now in `src/contexts/vote_section.py`, with
  tests), `scripts/paired_run.py` (paired runs with `--resume`), and
  `rapidfuzz` as a pipeline dependency.

## 5. What could not be verified

- **Paired runs ran on the host, not in Docker.** They use the same code as
  the entrypoint (`cli.predict`); the image was rebuilt with `rapidfuzz` and
  checked, and `make run` was run at the end.
- **Booklet parsing time is outside the comparison** (warm cache in both
  arms). A real run pays it once per booklet.
- **The selector's parameters were tuned on the same dev cases** used in E2.
  Recall is stable across halves and languages, but the held-out test split
  is the real check.
- **Token counts are self-reported** by the endpoint. The organisers' proxy
  count wins.

## 6. Recommended next steps

1. **Win back the evidence score without losing the label gains.** The claims
   often say where their content comes from ("Laut der Zusammenfassung", "Le
   résumé…", "Il testo in votazione…", "Le comité…"). Two cheap options:
   - let the citation follow that hint;
   - fill the free evidence slots (up to five) with the matching page from
     both the summary and the detailed section.

   The second can be tested offline first, by re-deriving evidence from the
   saved E2 answers without new calls.
2. **Tighten the selection at the edges.** The cover, table of contents and
   back cover list every ballot's title, so they match every vote, and gap
   filling then pulls in neighbouring pages, including other ballots'
   summaries. In the `make run` example (paternity leave), the selection
   held the right section (pages 58 to 72) but also pages 1 to 12 and 73 to
   88, and the model cited page 4 (another ballot) before the right pages.
   Ignoring title matches on the first 3 and last 2 pages should cut tokens
   and wrong citations. Measure it offline first (recall, size), then run a
   paired comparison.
3. **Neutral in the short context.** Gold-neutral claims called
   contradiction rose from 20 to 34. Try task B's lesson in task A's prompt:
   say explicitly that a claim about another ballot is neutral even when the
   section is about a related topic.
4. **Final check before submission.** Run the default pipeline once on all
   600 dev cases through `make run`, then the held-out **test** split once
   (never used so far) for an unbiased estimate. Then write the README
   statement and the technical report around the full-booklet vs. section
   table above.

## 7. Final checks (14:25 UTC)

- **Tests and self-checks:** all 45 unit tests and all 14 self-checks pass.
  Our scorer gives the official Macro-F1 exactly on both E2 arms.
- **`make run`** with the new defaults (json_schema, vote section): exit 0,
  no failures, two responses in the official format (format check clean).
  - The task B example: entailment.
  - The task A example: entailment, with evidence pages 4, 58, 59, 60, 61.
    Page 4 belongs to another ballot; see next step 2.
- **Secrets:** no key and no `.env` in any commit; the dev booklet PDFs stay
  local.
