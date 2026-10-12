# How the organisers score a submission

Source: the organisers' Q&A slides of 8 October 2026, as passed on by Rashad (session 10). Written here in
our own words; where this page and the starter repository disagree, the notes say so. Our own estimate of
the score is `scripts/official_score.py` ("REF SCORE", below).

## The total

    Score = 0.4 × S_B + 0.6 × S_A

Task A (whole booklet) weighs more than task B (given passage).

    S_A = 0.50 × Macro-F1 + 0.20 × Evidence + 0.15 × T + 0.15 × K
    S_B = 0.70 × Macro-F1                   + 0.15 × T + 0.15 × K

- **Macro-F1:** from labels only, per task, as in the starter's `evaluate.py`.
- **Evidence (task A only):** the share of gold entailment and contradiction cases with a hit among the first
  five evidence items. An item is a hit if it lies inside the gold passage or contains it (the scorer's fuzzy
  match in either direction). Its position within the first five does not matter. Pages are not checked by
  the scorer yet, but they must be correct.
- **K, tokens:** best tokens per case ÷ our tokens per case. Tokens are counted by the organisers' proxy over
  every call of a case: retries and second calls count. Whether output tokens count is not said.
- **T, local time:** best local time per case ÷ our local time per case. **Local time** is the wall-clock time
  of the container run minus the time during which at least one model request is in flight. The model's
  latency does not count; start-up, reading and parsing the PDF, embedding, and every gap between two
  requests do. There is no floor: ten times the best time gives T = 0.1.
- **"Best"** is the lowest value among the teams whose Macro-F1 on that task is at least 0.65.

So 30 % of each task's score is cost (15 % tokens, 15 % local time), measured against the other teams.

## How it is run

- Task A and task B are run in **separate containers** (one input file each).
- The organisers **pull a published image** from the repository's container registry (ghcr.io) and run it
  with the documented command. Our image is published by `.github/workflows/publish-image.yml` (session 10,
  step 3).
- Local parsing, OCR, embeddings and BM25 are allowed and must be documented.

## Validity

- Minimum Macro-F1: **0.60 for task A and 0.75 for task B** (slides). The starter repository, at commit
  `5e695772`, later says 0.70 for task B. Below either minimum the whole submission is invalid. **We keep 0.75
  as our bar.**

## What it means for us

- Every millisecond of local work per case counts against T, while model latency does not: work done while a
  request is in flight is free; work done between requests is not.
- Every token counts against K, including a second call; a version that saves tokens can win even at equal
  Macro-F1.
- The evidence weight (0.20 of S_A) is large: a correct label without a hit loses a fifth of task A.

## REF SCORE (`scripts/official_score.py`)

We cannot know the other teams' best values. To compare our own versions on one fixed scale, the script uses
reference values fixed at the start of session 10, before any measurement, so that no later choice can move
them (ratios capped at 1):

| Reference "best" | Task A | Task B |
|---|---|---|
| Tokens per case | 600 | 800 |
| Local time per case | 0.05 s | 0.005 s |

Tokens per case are input plus output tokens (the proxy counts "tokens"; whether output counts is not said, so
we count both, which is the stricter reading). The script always reports the parts (Macro-F1, evidence, K, T)
next to S_A, S_B and the total. A REF SCORE is not the official score: it only ranks our own versions.
