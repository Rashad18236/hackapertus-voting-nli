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

## Data

The public dataset is `OSTswiss/MNLIoverSwissVotingBooklets` on Hugging Face,
files `v1.1.parquet` and `v1.1.jsonl` (same data, somewhere between 1,000 and
10,000 rows). An older preview showed these columns: `claim`, `claim_language`,
`reference_string`, `entailment_label`, `booklet_id`, `booklet_language`,
`booklet_publish_date`, `booklet_download_date`, `booklet_url`. Version 1.1 may
differ, so inspect the file before relying on any column name.

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

## Current stage: setup

Goal: a walking skeleton. On a fresh clone, `make run` builds a Docker image,
runs the CLI on two sample beginner cases, calls Apertus once per case with a
simple hardcoded prompt, and writes predictions in the output format above.

Done when:

1. `.env.example` lists the three variable names with placeholder values.
2. `src/llm.py` makes one successful Apertus call using only those variables.
3. `src/cli.py` reads the sample file and writes a valid predictions file.
4. `Dockerfile` and `Makefile` make `make run` do step 3 in a container.
5. `make run` passes in a second, freshly cloned copy of the repository.

Out of scope for this stage: PDF parsing, the advanced task, prompt tuning,
evaluation code, and anything to do with retrieval.

## Open questions (do not assume the answers)

- How judges pass the held-out cases to `make run`, and where output should go.
- Whether booklet PDFs are supplied at judging time or must live in `data/`.
- Whether `LLM_BASE_URL` is the token-counting proxy. The endpoint is probably
  OpenAI-compatible; confirm that with the first call.
- Whether non-Apertus embedding models are allowed in the pipeline.
- How evidence matching is computed (exact string or overlap), and whether
  `page` means the PDF page index or the printed page number.
