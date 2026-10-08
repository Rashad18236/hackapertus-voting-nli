# HackApertus Track 2A: NLI over Swiss voting booklets

## What this project is

A hackathon submission for the OST challenge in Hack Apertus (Track 2A). Given a
claim in German, French or Italian and a source from an official Swiss federal
voting booklet, the system decides whether the source entails (0), is neutral
towards (1), or contradicts (2) the claim. The reference point is always the
supplied source, never outside knowledge: supports = entailment; insufficient
information = neutral; refutes = contradiction. A true claim the source does
not cover is neutral.

Submission deadline: 16 October 2026, 12:00 CEST, no extension.

We are a team of two and both new to NLI evaluation. We have to explain every
part of this system in a technical report, so prefer simple, readable code over
clever code, and tell us briefly why you chose an approach.

Claude is a development tool here. It is not part of the solution and must never
be called by anything the pipeline runs.

## The official contract is the authority

`track_2a/docs/official_contract.md` is the organisers' Getting Started guide
(copied 2026-10-08). Wherever it conflicts with this file, it wins. The
organisers' starter repository is `https://gitlab.com/ifsoftware/hackapertus-starter`
(read at commit `559b598`). It has no licence file, so we do not copy its code
into this public repository; we clone it outside and run its `prepare_cases.py`
and `evaluate.py` unchanged.

## Notes from the official challenge page (added 2026-10-08)

- **The central experiment is "full document -> Apertus" versus "selected
  context -> Apertus".** Both must be measured and reported, with the same
  scorer and the same dev split.
- **Use the label definitions from the dataset's README in the NLI prompt.**
  Caveat: on 2026-10-08 the README (dataset commit `9ff08597`) contains only
  `license: mit`, no definitions. Until it has them, the prompt uses the
  official guide's wording (supports = entailment, insufficient information =
  neutral, refutes = contradiction). Check the README again before each prompt
  change and quote its definitions word for word once they appear.
- **The technical report must document how document context is prepared and
  supplied to the model** (parsing, page numbers, what is selected, what the
  prompt contains).
- **Outputs must not be presented as political advice and must be traceable
  to the source booklet.** State this in `track_2a/README.md` and in
  `track_2a/technical_report.md` (not done yet).
- **Booklet parsing is assumed to be allowed locally** (not with Apertus), per
  the contract's "local parsing, OCR, or embeddings may run locally", until
  the organisers say otherwise.

## Constraints set by the organisers

- `track_2a/` is the project root. Do not rename it or move the files the
  template put there. Judges run the Docker image; `make run` is our wrapper.
- Docker entrypoint: `<entrypoint> --input /data/cases.jsonl --output
  /output/predictions.jsonl`. One JSON line per input id, any order, exit 0.
  Missing or invalid responses count as wrong.
- Docker rules: `linux/amd64`, no GPU. `/data` is read-only; write only to
  `/output` and `/tmp`. All dependencies and any local model weights are baked
  into the image; nothing is downloaded at run time. No API keys or `.env` in
  the image.
- Only Apertus v1.5 models (`swiss-ai/Apertus-v1.5-...`). Every remote model
  call must go to `BASE_URL`. Local parsing, OCR or embeddings may run locally;
  whether a non-Apertus local embedding model is acceptable is still unclear,
  so do not add one without asking us.
- Variables: `BASE_URL` and `API_KEY`, environment first, then local
  configuration. At evaluation the organisers inject a token-counting proxy as
  `BASE_URL` and a team key as `API_KEY`. For local use we fall back to
  `LLM_BASE_URL` / `LLM_API_KEY`. The model name comes from `MODEL`, else
  `LLM_NAME`, else `swiss-ai/Apertus-v1.5-8B`. Never hardcode, print, log or
  commit their values. `.env` is git-ignored; keep `.env.example` current.
- **Minimum Macro-F1 for a valid submission: 0.75 on task B and 0.60 on
  task A** (starter's `evaluate.py`).
- `track_2a/data/` must stay under 100 MB.
- The repository is public. Treat everything committed as published.

## The two tasks

Every request has `id`, `vote` (vote name in the source language), `claim`
(`text`, `language`), and exactly one source:

- **Task A, document:** `booklet` with `path` (relative to `/data`, e.g.
  `booklets/2024_09_22_de.pdf`) and `language`. Find the relevant passage in
  the PDF, then decide. Use `vote` to find the right proposal in the booklet.
  Start with a full-document baseline before retrieval or compression.
- **Task B, reference:** `reference` with `text` and `language`. Decide against
  that passage.

Input files can mix both tasks. All nine source/claim language combinations of
de, fr and it must work.

Response:

```json
{
  "id": "v1.1-row-60-A",
  "label": 0,
  "label_name": "entailment",
  "evidence": [ { "page": 43, "text": "...verbatim quote in the source language..." } ],
  "metrics": { "input_tokens": 1304, "output_tokens": 46, "inference_time_ms": 776 }
}
```

- `label_name` must match `label`, or the response is invalid.
- `metrics`: total LLM input and output tokens (incl. reasoning) over all calls
  for the case, and the case's wall-clock time in ms.
- Task A, labels 0 and 2: at least one evidence item with a **1-based PDF page**
  and a verbatim quote in the source language (or the text of the page). Each
  item at most about 5,000 characters; only the first five count. Quote the
  detailed section on the vote, not the summary at the front; cite every place
  a fact appears as separate items, most relevant first.
- Task B: evidence is optional and not scored. We return `[]`; if we ever
  include it, `page` must be `null`.

## How submissions are scored

- Macro-F1 per task (A and B separately), from labels only. Missing, duplicated
  or invalid responses count as wrong. Thresholds above.
- Task A evidence score: share of gold entailment/contradiction cases where
  one of the first five evidence items fuzzy-matches the gold passage
  (`reference_string`; rapidfuzz partial ratio >= 90 after normalising case,
  whitespace and line-break hyphenation). Pages are not checked locally yet.
- Tokens and time: measured by the organisers' proxy, scored relative to other
  teams. Every model call counts, retries included.
- Final evaluation uses a held-out private set.

## Model endpoint (development)

- The guide's development endpoint is CSCS: `https://api.inference.cscs.ch/v1`.
- We currently develop on Public AI (OpenAI-compatible): model
  `swiss-ai/apertus-v1.5-8b`, base URL `https://api.publicai.co/v1` (fallback
  `https://platform.publicai.co/v1`). Public AI requires a `User-Agent` header;
  `src/llm.py` always sends `hackapertus-voting-nli/0.1`. These values live only
  in `track_2a/.env` as `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_NAME`.
- The key is temporary and will be rotated. Never copy it anywhere else.
- Public AI sometimes returns HTTP 504 after about 61 s; we do not retry.
- In sandboxes where Docker containers cannot reach the internet directly,
  pass proxy flags with `make run DOCKER_RUN_FLAGS="--network host -e HTTPS_PROXY"`.

## Data

The dataset is `OSTswiss/MNLIoverSwissVotingBooklets` v1.1 (commit
`9ff08597`, MIT): 1,488 rows, 335 of them exact duplicates. Columns: `claim`,
`claim_language`, `reference_string`, `entailment_label`, `baseline_score`,
`reference_language`, `booklet_publish_date`, `booklet_download_date`,
`booklet_url`, `vote`. Each row gives one task A and one task B case. Neutral
rows pair the claim with an unrelated passage, so they have no gold passage.
See `track_2a/docs/dataset_profile.md`.

Our cases are generated by the starter's `prepare_cases.py` and filtered to our
split (`track_2a/data/README.md`): split by voting date, seed 42, duplicates
excluded. `data/dev/` has 300 rows (600 cases), `data/test/` 267 rows (534
cases). `expected-labels.jsonl` files never go into the prediction container.

## Layout inside `track_2a/`

```
Makefile, Dockerfile, .dockerignore, .env.example, requirements.txt, requirements-dev.txt
src/
  cli.py        official entrypoint: --input/--output, tasks A and B, never drops a case
  llm.py        the only module that calls Apertus; records tokens and time per call
  nli.py        prompts and label parsing
  env.py        minimal .env reader (environment wins)
  evaluate.py   per-language breakdowns only; official scores come from the starter
  parse.py      booklet PDF -> text per page (pypdf, 1-based pages), cached in /tmp by SHA-256
  context.py    task A context selection: full booklet or the vote's section (default)
examples/       cases.jsonl for make run (one task A, one task B request, from dev)
data/           raw dataset, dev/ and test/ splits, splits.json
docs/           official contract, decisions, results, reviews, run artefacts
scripts/        dataset profile, splits, self-checks, format check, offline re-parse
tests/          unit tests (evaluate, parser, CLI)
```

## How we work

- We build in stages with a gate at the end of each. Stay inside the current
  stage. In particular, no retrieval, embeddings, rerankers or chunking before
  the full-context baseline has measured numbers; the brief rewards measured
  trade-offs, and without a baseline nothing can be compared.
- Make small changes and say how to run and check each one.
- Never write a result that did not come from an actual run. If you cannot run
  something, for example because the session has no API key, say so plainly.
- Keep dependencies few and well known. Ask before adding a heavy one.
- Score with the starter's `evaluate.py`; `scripts/self_checks.py` verifies
  that our `evaluate.py` gives the same Macro-F1.
- Never run on `data/test/`. Test is for the final evaluation only.
- Record every decision in `track_2a/docs/decisions.md` with a one-line reason.

## Current stage: task A answer format and selected context

Session 2 (merged as PR #3): task B dev Macro-F1 0.947 with `v3-topic-first`
(default); task A full-document baseline `A-v3-fulldoc` 0.589 on all 300 dev
cases (0.608 with the prose-label parser), evidence 0.209, about 40k input
tokens and 11.5 s per case. 37 % of task A answers were not valid JSON.

Goal, step 1 (approach 1a): reliable task A answers through schema-constrained
output (`response_format: json_schema` with `pages` and `label`).
Goal, step 2 (approach 2a): the central experiment. Give the model only the
vote's section of the booklet, found deterministically from the `vote` title
(no embeddings), and compare it with the full document on the same cases:
Macro-F1, evidence score, input tokens, mean and p95 time.

Rules for this stage:

- Never run on `data/test/`; do not change the splits or the scorer.
- One change per comparison; every run is a row in `docs/results.md`.
- Comparisons are paired: both configurations run on the same case back to
  back, because the endpoint's output drifted during session 2.
- Measure the section selector offline first (does the selected context contain
  the gold page, and how large is it) before spending model calls.
- Cases run one at a time; one retry for HTTP 5xx and timeouts only.
- Still no embeddings or non-Apertus models.

Status at the end of session 3 (details: `track_2a/docs/session_3_report.md`):
task A answers are schema-constrained (0 unparseable) and task A sends only
the vote's section (`src/context.py`). E2, 300 dev cases, paired: section
Macro-F1 0.732 against 0.669 for the full booklet, 15.9k against 39.2k input
tokens per case, p95 13.5 s against 37.1 s; evidence 0.224 against 0.284.
Task B unchanged at 0.947.

## Open questions (do not assume the answers)

- Whether a non-Apertus local embedding model is acceptable (the guide allows
  local embeddings but also says "only Apertus v1.5 models").
- Whether the evidence page is checked against the 1-based PDF page in the
  official run (the starter says pages are "not checked yet").
- Formula combining Macro-F1, tokens and time in the final score (the starter
  refers to "evaluation notes" we have not seen).
- Whether booklet parsing must use Apertus or may be local. Working
  assumption: local parsing is allowed (contract wording), until told otherwise.
- Where the dataset README's label definitions are (the README is still
  licence-only as of 2026-10-08).
