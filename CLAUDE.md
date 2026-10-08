# HackApertus Track 2A: NLI over Swiss voting booklets

## What this project is

A hackathon submission for the OST challenge in Hack Apertus (Track 2A). Given an
official Swiss federal voting booklet and a claim in German, French or Italian,
the system decides whether the booklet entails (0), is neutral towards (1), or
contradicts (2) the claim, and returns the passage that justifies the decision.
The reference point is always the booklet, never outside knowledge: a true claim
the booklet does not cover is neutral.

Submission deadline: 16 October 2026, 12:00 CEST, no extension.

We are a team of two and both new to NLI evaluation. We have to explain every
part of this system in a technical report, so prefer simple, readable code over
clever code, and tell us briefly why you chose an approach.

Claude is a development tool here. It is not part of the solution and must never
be called by anything the pipeline runs.

## Constraints set by the organisers

- `track_2a/` is the project root. Do not rename it or move the files the
  template put there. Judges run `make run` from inside it, on a clean checkout,
  in Docker, with nothing pre-installed.
- Apertus v1.5 (8B and 70B) is the only language model allowed inside the
  pipeline. Whether a non-Apertus embedding model is allowed is unresolved, so
  do not add one without asking us.
- Model access comes from three environment variables: `LLM_NAME`,
  `LLM_BASE_URL`, `LLM_API_KEY`. Never hardcode, print, log or commit their
  values. `.env` is git-ignored; keep `.env.example` up to date with the names.
- `make run` has to work both when those variables are exported in the shell
  (how judges will probably run it) and when they sit in a local `.env`.
- `track_2a/data/` must stay under 100 MB.
- The repository will be public. Treat everything committed as published.

## The two tasks

Beginner task: compare the claim directly with a supplied reference text.

```json
{
  "id": "case-0043",
  "reference": { "text": "Der Bundesrat und der Nationalrat lehnen die Volksinitiative ab. ..." },
  "claim": { "text": "Le Conseil fédéral recommande d'accepter l'initiative." }
}
```

Advanced task: find the evidence inside the booklet PDF, then classify.

```json
{
  "id": "case-0042",
  "booklet": { "path": "booklets/2024_11_24_de.pdf" },
  "vote": "Étape d'aménagement 2023 des routes nationales",
  "claim": { "text": "La proposition entraînera une augmentation de la TVA." }
}
```

The claim and the reference or booklet can be in different languages. All nine
combinations of German, French and Italian must work.

Output for both tasks:

```json
{
  "id": "case-0042",
  "label": 0,
  "label_name": "entailment",
  "evidence": [ { "page": 7, "text": "...verbatim supporting passage..." } ],
  "metrics": { "input_tokens": 8431, "output_tokens": 112, "inference_time_ms": 1820 }
}
```

Evidence is required for entailment and contradiction and may be empty for
neutral. Evidence text must be verbatim from the source. `page` applies to the
advanced task.

## How submissions are scored

- Macro-F1 over the three labels on a held-out benchmark. This is the primary
  metric and is reported separately for the beginner and advanced tasks.
- Evidence: does the returned passage match the gold passage, and for the
  advanced task, does the PDF page match.
- Tokens: the sum of input tokens. The organisers count them with their own
  proxy and their count wins, so every model call matters, retries included.
- Speed: mean and p95 of `inference_time_ms`.
- Results are broken down by language and by same-language versus cross-lingual.

## Model endpoint (development)

- Provider: Public AI, OpenAI-compatible chat-completions API (confirmed by a
  real call on 2026-10-08; the response includes `usage` token counts).
- Model: `swiss-ai/apertus-v1.5-8b` (official Apertus v1.5, 262K context).
- Base URL: `https://api.publicai.co/v1`. Fallback if that gives not-found or
  connection errors: `https://platform.publicai.co/v1`. Both live only in
  `.env`, never in code.
- Public AI requires a `User-Agent` header on every request; `src/llm.py`
  sends `hackapertus-voting-nli/0.1`.
- The key is temporary and will be rotated; provider or model may change too.
  All three values live only in `track_2a/.env` (or the shell). Never copy the
  key anywhere else.
- Even a one-line message costs about 71 input tokens: the chat template adds
  text of its own to every call.
- In sandboxes where Docker containers cannot reach the internet directly,
  pass proxy flags with `make run DOCKER_RUN_FLAGS="--network host -e HTTPS_PROXY"`.

## Data

The public dataset is `OSTswiss/MNLIoverSwissVotingBooklets` on Hugging Face,
files `v1.1.parquet` and `v1.1.jsonl` (same data, somewhere between 1,000 and
10,000 rows). Inspected on 2026-10-07, v1.1 has 1,488 rows and these columns:
`claim`, `claim_language`, `reference_string`, `entailment_label`,
`baseline_score`, `reference_language`, `booklet_publish_date`,
`booklet_download_date`, `booklet_url`, `vote`. There is no `booklet_id` or
`booklet_language`. `entailment_label` uses the same encoding as our output
(0 entailment, 1 neutral, 2 contradiction), roughly 500 rows each; claim
languages are about 500 each of de, fr, it. Reference texts are 884 to 25,425
characters long. `data/sample_beginner.jsonl` holds rows 300 and 1281.

## Intended layout inside `track_2a/`

```
Makefile, Dockerfile, .env.example, requirements.txt
src/
  cli.py        reads cases from a file, writes predictions to a file
  llm.py        the only module that calls Apertus; records input tokens,
                output tokens and elapsed milliseconds for every call
  nli.py        prompt construction and label parsing
  parse.py      PDF to passages with page numbers            (later stage)
  context.py    context selection, starts as "return all"    (later stage)
  evaluate.py   Macro-F1, evidence match, per-language tables (later stage)
data/           sample cases, dev split, raw dataset
docs/           results log, diagrams
```

The CLI takes an input path and an output path as arguments, with defaults
pointing at a small sample file in `data/`, because we do not yet know how
judges will supply the held-out cases.

## How we work

- We build in stages with a gate at the end of each. Stay inside the current
  stage. In particular, no retrieval, embeddings, rerankers or chunking before
  the full-context baseline has measured numbers; the brief rewards measured
  trade-offs, and without a baseline nothing can be compared.
- Make small changes and say how to run and check each one.
- Never write a result that did not come from an actual run. If you cannot run
  something, for example because the session has no API key, say so plainly.
- Keep dependencies few and well known. Ask before adding a heavy one.
- When `evaluate.py` is written, include tests small enough to verify by hand.

## Current stage: beginner baseline

Setup is finished (walking skeleton, `make run` passes on a fresh clone).

Goal: a measured full-context baseline for the beginner task. One model call
per case with the whole reference text in the prompt, scored on a frozen dev
split, so every later change can be compared against real numbers.

Done when:

1. `docs/dataset_profile.md` profiles `data/raw/v1.1.parquet`.
2. Dev and test splits are frozen by booklet (voting date), seed 42, with
   inputs and gold answers in separate files; `data/README.md` explains how.
3. `src/evaluate.py` reports Macro-F1, per-label scores, confusion matrix,
   evidence metrics, tokens, time and per-language breakdowns, with tests in
   `tests/` that can be checked on paper.
4. `scripts/self_checks.py` passes (tests, sklearn agreement, dummy
   baselines, gold-vs-gold, no leakage).
5. Prompt `v1-json` in `src/nli.py` runs on `data/dev_inputs.jsonl` and the
   result is the first row of `docs/results.md`.
6. `docs/baseline_review.md` and `docs/decisions.md` are written.

Rules for this stage:

- Never run on `data/test_inputs.jsonl`. Test is for the final evaluation only.
- Every number in `docs/` comes from an actual run; record the commit.
- Parse failures are recorded as such, never replaced by a guessed label.

Out of scope: PDF parsing, the advanced task, retrieval, chunking,
embeddings, and prompt tuning beyond the first prompt.

## Open questions (do not assume the answers)

- How judges pass the held-out cases to `make run`, and where output should go.
- Whether booklet PDFs are supplied at judging time or must live in `data/`.
- Whether non-Apertus embedding models are allowed in the pipeline.
- How evidence matching is computed (exact string or overlap), and whether
  `page` means the PDF page index or the printed page number.
