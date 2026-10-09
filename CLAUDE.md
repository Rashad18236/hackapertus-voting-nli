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
- Model rule (`docs/official_contract.md`, with the team's additions of
  2026-10-08): only Apertus v1.5 (`swiss-ai/Apertus-v1.5-...`) may be called
  as the language model, and every remote model call must go through
  `BASE_URL`. Local parsing, OCR and embedding models are allowed. They must
  be open-weight, baked into the Docker image with no downloads at run time,
  run on CPU, and be described in the technical report, with instructions for
  running the project with them (organisers' template README). Apertus must make the
  entailment decision; a local model may only choose what Apertus reads.
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
- Public AI sometimes returns HTTP 504 after about 61 s (Cloudflare gives up on a
  model backend); `src/llm.py` retries once. Status per model:
  https://status.publicai.co ("Suppliers by Model"). When `apertus-v1.5-8b` is
  down, `swiss-ai/apertus-v1.5-8b-thinking` answered like it with json_schema
  (task A); select it with `LLM_NAME` in the environment, never in code.
  The 8B was down on 2026-10-08 from about 17:30 until at least 19:44 UTC
  (answering again at 20:20); E4 ran entirely on the thinking model.
- Public AI routes `swiss-ai/apertus-v1.5-8b` to more than one backend
  (2026-10-09: api.blablador.fz-juelich.de, fingerprint `vllm-0.23.1rc1…`, and
  api.featherless.ai, fingerprint `fp1-nst-nes`, deployment name
  `swiss-ai/Apertus-8B-Instruct-2509`), and its LiteLLM gateway answers a
  request identical to one of the last ~10 minutes from its cache. `src/llm.py`
  records both per call (raw answers, `endpoint`).
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
  booklet.py    booklet -> votes and parts (summary, detail, committee, parliament, council, law)
                from the contents lines, checked against page headings; boxes per voice; paragraphs
  claim_router.py  claim opening -> part (summary, council, committee, law, detail), de/fr/it, or None
  context.py    registry of task A context variants: names, prompt per variant, select()
  contexts/     one file per variant: full.py, vote_section.py, embed_e5_small.py (default until
                session 7; multilingual-e5-small, ONNX, local CPU), and since session 4
                vote_section_embed_e5_small(_k12).py, embed_granite_97m_r2.py,
                vote_section_embed_granite_97m_r2.py; shared code in retrieval.py; since
                session 6 section_route.py (default since session 7: the part the claim names,
                as numbered paragraphs; falls back to embed-e5-small)
  evidence.py   task A evidence settings: cited-pieces (default since session 6: 1,000-character pieces
                of the cited pages), cited (whole cited pages), cited-then-retrieved (off, not used)
examples/       cases.jsonl for make run (one task A, one task B request, from dev)
data/           raw dataset, dev/ and test/ splits, splits.json; val/ (session 7: 580 task A cases from
                rows in neither dev nor test, and a balanced 300-case sample)
docs/           official contract, reports, reviews
  runs/         one folder per run: run.json, NOTES.md and the run's files (see runs/README.md)
  decisions/    one file per stage or session: <YYYY-MM-DD-HHMM>_<person>_<topic>.md
  results.md, decisions.md   generated from runs/ and decisions/ by scripts/build_docs.py
scripts/        dataset profile, splits, self-checks, format check, offline re-parse,
                paired runs, retrieval check and grid, dev booklet download, build_docs.py,
                search_or_reading.py, pad_evidence.py, evidence_loss.py, evidence_forms.py,
                rescore_evidence.py, route_check.py, paired_analysis.py, make_val.py; since PR #12
                stub_llm.py (fake model), router_stress.py, unseen_booklets.py, speed_memory.py;
                session 8: prompt_snapshot.py (request hashes and replay, gates G1/G2),
                embed_equivalence.py, parse_equivalence.py, container_speed.sh; task B (PR #14):
                taskb_tokens.py, taskb_analysis.py (task B confirmation), canary_taskb.py,
                interleaved_analysis.py (task B arms of one run)
models/         local copies of the embedding models (git-ignored; the image downloads e5 at build time)
tests/          unit tests (evaluate, parser, CLI, context variants, generated docs)
```

Outside `track_2a/`: `CLAUDE.md` and `.github/pull_request_template.md`. The
organisers' template layout of `track_2a/` (`README.md`, `technical_report.md`,
`Makefile`, `src/`, `data/`, `docs/`) must stay as it is: never rename or move
those; new files go inside `src/` and `docs/`.

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
- Record every decision with a one-line reason in the stage's or session's
  file in `track_2a/docs/decisions/` (a new file for a new stage or session).

## How we work together (two people, one repository)

- **Branches:** one short branch per change, named `person/topic` (e.g.
  `kaan/embed-vote-query`), started from a freshly pulled `main`. Claude Code
  cloud sessions get an automatic `claude/...` name; that branch belongs to
  the person who runs the session.
- **Merge early:** into `main` through a pull request, at least once a day.
  When `main` moves while you work, merge `main` into your branch at once.
  Never rebase, amend or force-push a branch someone else may have pulled.
  After its pull request is merged, a branch is finished; start the next
  change from `main`.
- **Pull requests** follow `.github/pull_request_template.md`: summary, who
  built it, results, what changed, checks.
- **Context variants:** one file per variant in `src/contexts/`, plus one
  line in `src/context.py`. A variant's name never changes meaning; changed
  behaviour gets a new name (`embed-e5-small-v2`), like prompt versions.
- **Runs:** one folder per run in `docs/runs/`, named
  `YYYY-MM-DD_person_variant_cases`, with `run.json` and `NOTES.md` (fields
  in `docs/runs/README.md`).
- **Generated pages:** `docs/results.md` and `docs/decisions.md` are built by
  `python3 scripts/build_docs.py`; never edit them by hand. After a merge
  conflict in either, rerun the script and commit its output. The unit tests
  fail if they are out of date or a `run.json` disagrees with its run's files.
- **Milestones** are git tags on `main` (`v0.1-...`); `git checkout <tag> &&
  make build` rebuilds that version. The final submission gets the tag
  `submission`.

## Current stage: hardening without a model (session 8)

Session 8 (2026-10-09, branch `rashad/hardening` from `main` at `25ed5fa`,
report `track_2a/docs/session_8_report.md`, decisions
`docs/decisions/2026-10-09-1348_rashad_session-8.md`): five proposals of
`track_2a/docs/checks_no_model.md` applied, one commit each, **no model
calls**, every change behind two gates that compare it with a reference:

- **Reference** (`docs/runs/2026-10-09_rashad_prompt-snapshot_devAB-valA`):
  `scripts/prompt_snapshot.py` runs the real CLI on the 600 dev and 580 val
  cases against the fake model (`scripts/stub_llm.py`) and records the
  SHA-256 of every request body and every task A path; the fake model's
  replay mode returns E5's and E6's saved answers by request hash, which
  reproduces their scores exactly (dev 0.953 / 0.905, val 0.956 / 0.946).
- **G1** every request hash and path equal the reference; **G2** every label
  and evidence equal it (metrics ignored); plus `pytest`. Rerun after any
  change to `src/`: `scripts/prompt_snapshot.py run --replay ...` then
  `compare` (about 6 minutes).
- **A** `src/cli.py`: input decoded line by line (bad bytes, byte order
  mark), a duplicated id answered once, each response written and flushed at
  once (a killed run keeps its finished cases). **B** e5 embedding in
  length-sorted batches of 16: same vectors, section-route on 300 dev cases
  in the container 364.9 s → 228.5 s, slowest case 51.2 → 17.6 s, peak
  3.2 → 2.2 GiB. **C** router patterns of the stress test: 273 of 300 right,
  0 wrong part. **D** parser patterns for 2018–2019 booklets: 14 of 15
  unseen booklets, dev and val parse identical. **E** a repeated evidence text
  is left out (19 responses; evidence score unchanged).
- All five applied; G1 and G2 held for each (E changed only the evidence of
  the 19 responses that repeated a text). Not done: P5, P8, P11, P12.
- `main` with PR #13 (the same input fix as A) was merged in; our reader was
  kept because it also ends a line at a carriage return alone (`main`'s
  answered 0 cases of such a file). After the merge: G1 and G2 unchanged,
  136 tests, clean-machine workflow green (run 13).

Earlier stages: task B confirmation and cheap fixes (next section, PR #14) and task A
context with `section-route` as the default (history below).

## Task B: confirmation and cheap fixes (2026-10-09, 01:20 to 03:00 UTC, PR #14)

**Method (from 2026-10-09 02:00 UTC): versions are compared only inside one
interleaved run; scores from different runs are never compared.** The
endpoint changed what it answers twice in 13 hours, so a stored baseline
stops describing it without warning. In an interleaved run every case goes
to all versions back to back, in an order that rotates from case to case
(`scripts/paired_run.py`, two or more arms; balanced Latin square for four),
paced with `--min-interval 1.0` (HTTP 429 came at about 96 requests per
minute). Decisions: `docs/decisions/2026-10-09-0200_rashad_taskb-cheap-fixes-continued.md`.

- Every model call records the endpoint identity in the raw answers
  (`endpoint`: body `model`, `system_fingerprint`, identifying headers,
  Cloudflare data centre; nothing secret, no per-call ids), plus `attempts`
  and `http_429`.
- The canary (`scripts/canary_taskb.py`, 30 fixed dev cases, v3) no longer
  blocks runs: it runs immediately before and after each task B run and
  appends to `docs/canary_log.md` and `docs/canary_results.jsonl`. A run whose
  two checks differ is marked "endpoint changed during run" in
  `docs/results.md` (from `run.json`'s `canary` block).
- The run: all 300 dev task B cases, four arms. A v3-topic-first as it is
  (plain, max_tokens 32); B v3 + `--schema-b`, `--max-tokens-b 10`; C v5-min,
  schema, 10; D v5-ballot (v5-min plus "The first line of the reference text
  names the ballot it is about.", +14 tokens), schema, 10.
- Comparisons: B vs A (keep if Macro-F1 falls by at most 0.01, no unreadable
  answer, adds fewer than 30 tokens per case; if B fails, stop); C vs B (keep
  if Macro-F1 falls by at most 0.01 and no label's F1 by more than 0.03);
  D vs C (keep only if Macro-F1 rises by at least 0.01). Tokens = mean input
  plus output tokens per case.
- Recommend one arm to freeze; change no default. Never shorten the passage.
  Report: `track_2a/docs/taskb_cheap_fixes.md`.

Status (2026-10-09, 03:00 UTC): **run done; B fails its rule, so the
comparisons stopped; recommendation: freeze arm A (v3-topic-first as it is),
the current default; no default changed.** Run
`docs/runs/2026-10-09_rashad_taskb-4arm_devB300` (02:11 to 02:40 UTC, marked
"endpoint changed during run"): A 0.867, B 0.853 (−0.013, 0 unreadable,
−0.9 tokens per case), C 0.786 (27 unreadable), D 0.840 (22 unreadable;
C and D not judged). 0 failed calls, 0 HTTP 429.

- **Public AI served `swiss-ai/apertus-v1.5-8b` from two backends during the
  run** (blablador.fz-juelich.de 737 answers, featherless.ai 463 with the
  deployment name `swiss-ai/Apertus-8B-Instruct-2509`), switching within
  minutes. The backend changes answers: A and B are equal on the 250 cases
  where they met the same backend (0.877 both, 3 labels differ). Every Public
  AI number mixes backends; earlier runs recorded no identity.
- **The gateway answers identical requests from a cache for ~10 minutes**
  (`gateway_cache_hit` in the identity since this run). The confirmation
  stage's noise floor (0.0033) very likely measured this cache.
- Proposals, not done (Rashad decides): ask Public AI or use CSCS; judge on
  cases where all arms met the same backend; keep the canary off the cache.

Earlier in this stage (01:40 to 01:52 UTC, `docs/decisions/2026-10-09-0140_rashad_taskb-cheap-fixes.md`):
the old canary stopped the first run because the endpoint changed between
01:36 and 01:50 UTC (3 of 30 answers differ); run 2 (vote name) was skipped
because `vote` always names the passage's own ballot (886/886 non-test rows).
The thresholds of that stage's acceptance rule still hold, applied between
arms of one run.

Previous stage, task B confirmation (`track_2a/docs/taskb_confirmation.md`):
v3-topic-first 0.919 and 0.916 in two runs (session 2's 0.947 was the server
before 13:25 UTC on 2026-10-08). The 299 cases both runs answered have
identical answers, but run 2 very likely came from the gateway's cache, so
its "noise floor" of 0.0033 does not measure the model (corrected at 03:00). Errors: 17 of 24 are claims about another ballot called a
contradiction. Input tokens: passage 87 %, fixed instructions 203 tokens
(10 %), claim 2 %, endpoint 19 tokens (1 %).

Task A is settled for now: `section-route` is the default since session 7
(history below).

## Task A history (sessions 3 to 7)

Two lines of work from 2026-10-08 are merged (PR #5):

- **Session 3** (PR #4, `track_2a/docs/session_3_report.md`): task A answers
  are schema-constrained (`response_format: json_schema`, 0 unparseable), and
  the deterministic vote-section selector beat the full booklet in a paired
  run on all 300 dev cases: Macro-F1 0.732 against 0.669, 15.9k against
  39.2k input tokens per case, p95 13.5 s against 37.1 s, evidence 0.224
  against 0.284.
- **The `embedding` branch** (Kaan): `embed-e5-small` sends the top 8 chunks
  of at most 1,000 characters by `intfloat/multilingual-e5-small`. On all 300
  dev cases: Macro-F1 0.767, evidence 0.383, 1.9k input tokens per case. Not
  paired, about six hours after its reference, and without the json_schema
  answer (session 3 was not in that branch yet).

`--context-a` picks the task A context (all modes in `src/context.py`); the
default is `section-route` since session 7 (`embed-e5-small` from session 4
to 6). Every mode uses the json_schema
answer. `--evidence-a cited-then-retrieved` pads the evidence; it stays off
(team decision, session 5: evidence holds only pages Apertus cited).

E3 (paired, all 300 task A dev cases, both json_schema; details in
`track_2a/docs/runs/2026-10-08_rashad_embed-vs-section_devA300/NOTES.md`):
`embed-e5-small` 0.721 against `vote-section` 0.561 (below the 0.60 minimum),
evidence 0.383 against 0.095, 1.8k against 15.9k input tokens per case; p95
time 16.1 s against 9.3 s (each booklet is embedded on its first case).
Cases 181 to 300 ran on `apertus-v1.5-8b-thinking` because `apertus-v1.5-8b`
was down; with json_schema it answers like the 8B.

Public AI's `apertus-v1.5-8b` changed behaviour at about 13:25 UTC on
2026-10-08 (same prompts, temperature 0, different answers): E1 and E2's
first ~150 cases came from an earlier server. Only paired runs compare.

Session 4 (`track_2a/docs/session_4_report.md`, decisions in
`docs/decisions/2026-10-08-1857_rashad_session-4.md`):

- Of E3's 84 wrong embedding answers, 18 were search misses and 66 reading
  errors (mostly true statements called contradictions).
- A 72-setting offline search grid met no target set; its best setting under
  10 % of characters (`vote-section-embed-e5-small-k12`, hit 0.846 against
  0.741) lost the paired run E4 on `apertus-v1.5-8b-thinking`: Macro-F1 0.674
  against 0.711 for `embed-e5-small`.
- Padding evidence to five items (no penalty in the starter's scorer) lifted
  E3's evidence score from 0.383 to 0.522 without changing labels.
- The default is now `embed-e5-small`.

Session 5 (`track_2a/docs/session_5_report.md`, no model calls): task A
evidence contains **only pages Apertus cited** (fixed decision; the
`cited-then-retrieved` padding stays in the code, off). On E4's control
answers, of 201 gold cases: 75 hit, 23 gold page not sent, 20 predicted
neutral, 43 gold page sent but not cited, 40 cited but the text did not match
(mostly only the first or last page of a passage spanning pages). Whole-page
items stay best (0.373 against 0.368 and 0.358 for sent chunks). Realistic
maximum with cited pages only and today's search: 0.657.

Session 6 (`track_2a/docs/session_6_report.md`, decisions in
`docs/decisions/2026-10-08-2311_rashad_session-6.md`):

- Task A evidence default is now `cited-pieces`: the cited pages' pieces of
  at most 1,000 characters, one item each, in turn, at most five. On E4's
  answers: 0.542 against 0.373 (starter's scorer), labels unchanged.
- New context variant `section-route`: `src/claim_router.py` reads the part a
  claim's opening names (summary, council, committee, law, detail);
  `src/booklet.py` finds that part of the vote (all 44 dev booklets parse);
  Apertus gets it as numbered paragraphs (prompt `A-v4-section-route`, task
  B's rule) and cites paragraphs, which become the evidence. Falls back to
  `embed-e5-small` when it cannot route (1 of 300 dev cases).
- E5 (paired, all 300 dev task A cases, `apertus-v1.5-8b`): `section-route`
  Macro-F1 0.953 against 0.834 for `embed-e5-small`, evidence 0.905 against
  0.662, 1,210 against 1,868 input tokens, p95 3.9 s against 11.7 s.

Session 7 (`track_2a/docs/session_7_report.md`, decisions in
`docs/decisions/2026-10-09-0025_rashad_session-7.md`):

- An error while routing (parser, router, vote match, paragraph prompt) makes
  the case run as `embed-e5-small` and is counted in the run log; it never
  gives a neutral answer without a model call.
- Validation set `data/val/`: 580 task A cases from rows in neither dev nor
  test, minus the six rows used for router patterns in session 6. Offline:
  all 580 routed, the routed part holds the gold passage in 399 of 400.
  Never change router patterns or parser rules because of val results.
- E6 (paired, 300 balanced val cases, `apertus-v1.5-8b`): `section-route`
  0.956 against 0.865, evidence 0.946 against 0.588, 1,222 against 1,827
  input tokens, p95 3.0 s against 12.3 s.
- **`section-route` is the task A default** (commit `d69d820`).

Next, one change per comparison: a larger budget for long detail and law
parts, committee claims on votes without a committee, and the remaining
"called neutral" errors. Measure on dev, confirm on val.

Rules for this stage:

- Never run on `data/test/`; do not change the splits or the scorer.
- One change per comparison; every run gets a folder with `run.json` in
  `docs/runs/` and so a row in the generated `docs/results.md`.
- Comparisons are paired or interleaved (`scripts/paired_run.py`): all
  configurations run on the same case back to back, because the endpoint's
  output drifts. Scores from different runs are never compared.
- Measure offline first (`scripts/retrieval_check.py` for the embedding,
  selector recall for the vote section) before spending model calls.
- Cases run one at a time; one retry for HTTP 5xx and timeouts, up to two for
  HTTP 429.
- A change to `src/` that should not change answers is checked with G1 and G2
  against the session 8 reference (`scripts/prompt_snapshot.py`).
- Local models only under the model rule above. Ask before adding another one
  (each is a heavy dependency).

Earlier: session 2 (PR #3) set task B to 0.947 with `v3-topic-first`
(default, unchanged since) and measured the task A full-document baseline
(0.589, 37 % of answers not valid JSON).

## Open questions (do not assume the answers)

- Whether the evidence page is checked against the 1-based PDF page in the
  official run (the starter says pages are "not checked yet").
- Formula combining Macro-F1, tokens and time in the final score (the starter
  refers to "evaluation notes" we have not seen).
- Whether booklet parsing must use Apertus or may be local. Working
  assumption: local parsing is allowed (contract wording), until told otherwise.
- Where the dataset README's label definitions are (the README is still
  licence-only as of 2026-10-08).
- Which Apertus model and server the evaluation calls (8B or another v1.5
  variant; CSCS or Public AI), and on what hardware the image runs.
- Whether the official evaluation, like the starter, ignores extra evidence
  items, and whether evidence on a neutral answer counts.
