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
  template put there. The organisers pull our published image from the
  repository's container registry (ghcr.io) and run it with the documented
  command; `make run` is our local wrapper. Task A and task B are run in
  separate containers.
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
- **Minimum Macro-F1 for a valid submission: 0.60 on task A and 0.75 on
  task B** (Q&A slides of 8 October; the starter repository, commit
  `5e695772`, later says 0.70 for task B). Below either, the whole submission
  is invalid. Our bar stays 0.75.
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

Official formula (organisers' Q&A slides, 8 October; details in
`track_2a/docs/official_scoring.md`):

- **Score = 0.4 × S_B + 0.6 × S_A**, with
  S_A = 0.50 Macro-F1 + 0.20 evidence + 0.15 T + 0.15 K and
  S_B = 0.70 Macro-F1 + 0.15 T + 0.15 K.
- Macro-F1 per task (A and B separately), from labels only. Missing, duplicated
  or invalid responses count as wrong. Thresholds above.
- Task A evidence: share of gold entailment/contradiction cases with a hit in
  the first five items. An item is a hit if it lies inside the gold passage or
  contains it (`reference_string`; rapidfuzz partial ratio >= 90 after
  normalising case, whitespace and line-break hyphenation); its position
  within the five does not matter. Pages are not checked by the scorer yet but
  must be correct.
- **K** = best tokens per case / our tokens per case, counted by the
  organisers' proxy over all calls (retries and second calls included; whether
  output tokens count is not said).
- **T** = best local time per case / our local time per case. Local time =
  wall-clock time of the container run minus the time during which at least
  one model request is in flight: model latency does not count; start-up,
  parsing, embedding and every gap between requests do. No floor (ten times
  the best time gives 0.1).
- "Best" = the lowest value among teams with Macro-F1 >= 0.65 on that task.
- Our own estimate with fixed reference "best" values is
  `track_2a/scripts/official_score.py` (REF SCORE).
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
  cli.py        official entrypoint: --input/--output, tasks A and B, never drops a case; since session 10
                each case is prepare() (local work) + complete() (model call); --workers 0 = sequential
  pipeline.py   session 10: two forked worker processes ("lanes", each owning whole booklets) prepare cases
                while the main process sends them, one request at a time
  memo.py       session 10: compute-once caches safe with threads
  ap_parse.py   session 11: Apertus in the parsing roles (AP-part: the claim's part; AP-structure: the contents);
                session 12: AP-translate (a claim into the booklet's language, for the BM25 fallback)
  rankers.py, static_embed.py  session 12: the ranker switch (e5, model S, BM25, fusions, none) and the memory
                guard; model S (static-similarity-mrl-multilingual-v1, tokenizers + numpy, 256 dimensions)
  timing.py, deferral.py  session 11: phase timing (PROFILE_PHASES=1); light-first deferral of e5 cases in a lane
  llm.py        the only module that calls Apertus; records tokens and time per call; one kept connection
  nli.py        prompts and label parsing
  env.py        minimal .env reader (environment wins)
  evaluate.py   per-language breakdowns only; official scores come from the starter
  parse.py      booklet PDF -> text per page (pypdf, 1-based pages); session 11: pages read when first asked for
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
                of the cited pages), cited (whole cited pages), cited-then-retrieved (off, not used); session 13: hedge()
                (H, default: the paragraph before the first cited one and the cited page's whole text)
examples/       cases.jsonl for make run (one task A, one task B request, from dev)
data/           raw dataset, dev/ and test/ splits, splits.json; val/ (session 7: 580 task A cases from
                rows in neither dev nor test, and a balanced 300-case sample); session 10: probe/ (the test
                rows of 2021-03-07 and 2025-09-28, copies) and ontopic_neutral/ (46 dev cases, gold passage
                removed, expected neutral)
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
                interleaved_analysis.py (task B arms of one run); session 10: official_score.py (REF SCORE),
                local_time.py (local time the organisers' way), connection_time.py, make_probe.py,
                make_ontopic.py, rule_check.py (TOKEN RULE, fixes/breaks), schema_check.py,
                python_rule_offline.py, vote_language_check.py; session 12: ranker_check.py (rankers without the
                endpoint), static_equivalence.py (model S against sentence-transformers, development machine only),
                taskb_long_errors.py (task B errors on long references); session 13: arm_table.py (PAIRED RULE
                numbers per arm), taskb_b3_picks.py, evidence_pages.py (three page rules, hedge H), error_types.py (routing or
                reading errors; Apertus's offline labels), apertus_roles.py (calls and tokens per Apertus role)
models/         local copies of the embedding models (git-ignored; the image downloads e5 and model S at build time)
tests/          unit tests (evaluate, parser, CLI, context variants, generated docs)
```

Outside `track_2a/`: `CLAUDE.md`, `.github/pull_request_template.md` and `.github/workflows/`
(`clean-machine.yml`; since session 10 `publish-image.yml`, which publishes the image to
`ghcr.io/rashad18236/hackapertus-voting-nli`: `latest` from `main` only, `session-10` from the session 10
branch, and the commit hash). The
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

## Current stage: session 13 (2026-10-13 19:56 UTC to 2026-10-14 09:00 UTC)

Branch `rashad/session-13` from `main` at `c85a119` (PR #20 merged first; draft PR, never merged, no tag); status
`track_2a/docs/session_13_status.md`, decisions `docs/decisions/2026-10-13-1956_rashad_session-13.md`, report
`track_2a/docs/session_13_report.md`. Experiments stop on 14 October at 08:00 UTC, everything pushed by 09:00 UTC; steps
in the order given, what is not reached is written down as not done. Rules as in session 12, plus: Python may decide
WHEN to ask Apertus again, never WHAT the label is (mapping a word or enum Apertus chose to 0/1/2 is allowed); evidence
only text Apertus cited or text next to it on its real page; no new local models; every comparison one interleaved run
with an arm "today" (session 12's defaults), input and output tokens separately; PAIRED RULE (val +0.005, dev not
below −0.004, sign test p ≤ 0.10 on dev+val, input tokens ≤ +4 %, no more unreadable answers, local time ≤ +0.002 s,
on-topic neutral share ≥ today's − 0.05); G1/G2 against `docs/runs/2026-10-13_rashad_prompt-snapshot-final-s12_devAB-valA`.

- **Step 0:** PR #20 merged into `main` as `c85a119` (merge commit; it was a draft, so it was marked ready first);
  PR #19 (`kaan/robustness-experiments`, an ancestor of `main`) closed; publish-image on `main` green (`latest`,
  `sha-c85a119b409a`).
- **Step 1 (nothing adopted):** task A prompts A1–A5 (`--prompt-a A-v6-says|residual|mismatch|opposite|words`) and
  A6, a second look after a neutral answer that cites paragraphs (`--second-look-a6`, `A-v6-second-look`; the
  flag `--second-look-a` already names L2). Dev: today 0.983, A1 0.902, A2 0.973, A3 0.980, A4 0.964, A5 0.983,
  today+A6 0.987; on-topic neutral 32 of 46 today, 13–30 for the arms. All fail on dev (A5 and A6 the on-topic
  condition; A6 by one case: 2 neutrals flipped, at most 1 allowed). Val (report only): today 0.959, A5 0.971, A3 0.970,
  A6 0.973 (9 fixes, 1 break); they fix 7, 9 and 8 of session 12's 15 val errors answered neutral.
- **Step 2 (nothing adopted):** B1 (`v7-same-ballot`) void after the format check (an answer cut at the schema's
  80-character limit, then whitespace: unreadable); B3 (`--context-b cut4-tf`, 71 % of long references change a pick)
  and B4 (`v7-claim-first`, 5 unreadable) fail on dev; **B2 (`v7-unrelated`)** val 0.974 vs 0.968, fixes 8 of the 9 val
  errors answered contradiction, but fails (c) (9 / 6, p = 0.30) and (e) (2 unreadable vs 1).
- **Step 3 (adopted): evidence page hedge H** (`--evidence-hedge-a`, default): routed evidence adds the paragraph
  before the first cited one when that one opens its page, then the cited page's whole text. Rule 3 (first gold page)
  dev 116 → 119, val 223 → 236, probe 44 → 46 of 201 / 401 / 65; nothing worse; labels and requests unchanged.
- **Step 4:** technical report section 4 "How Apertus is used" (roles, ablation, errors, negative results);
  `scripts/error_types.py`: session 12's 23 val task A errors = 10 routing + 13 reading; Apertus (offline, 31 calls)
  names the reading errors' kinds. **Step 5:** `docs/organiser_questions.md`.
- **Step 6 (adopted): model S is the default ranker** (val task A 0.961 → 0.969, REF SCORE at 1.0 / 0.3 s 0.924 /
  0.917 → 0.927 / 0.919; `--ranker e5` for the earlier model); e5 stays for task B's selector T. Combination H+S 0.969
  vs 0.959 (val task A): kept. Task A peak memory 2,287 → 206 MiB; image size unchanged.
- **Final defaults through the published image** (`ghcr.io/rashad18236/hackapertus-voting-nli:sha-54032b4a7970`, tag
  `session-13`; `docs/runs/2026-10-14_rashad_final-s13_*`): dev task A 0.973 (evidence 0.985), task B 0.987; val 0.969
  (0.965), 0.968; probe 0.981 (0.985), 0.977. Tokens per case (dev, input + output): A 1,251 + 14.8, B 815 + 8.8.
  REF_SCORE_LINE Python wrote 1 of 2,128 labels.
- **New replay reference for G1/G2:** `docs/runs/2026-10-14_rashad_prompt-snapshot-final-s13_devAB-valA` (also
  `scripts/local_time.py`'s default table).

## Previous stage: session 12 (2026-10-13 10:35 UTC to 2026-10-13 17:05 UTC, merged as PR #20)

Branch `rashad/session-12` from `main` at `37904b3` (PR #20, merged into `main` on 2026-10-13 as `c85a119`, no tag); status
`track_2a/docs/session_12_status.md`, decisions `docs/decisions/2026-10-13-1035_rashad_session-12.md`, report
`track_2a/docs/session_12_report.md`. The last experimental session: every remaining idea with a real chance, in order
of value. The instruction arrived cut off in step 3; the readings of steps 3 (third version) to 8 are in the decisions
file, written before they ran. Rules as in session 11, plus: local models in the image are embedding models only (no
translation model, no ctranslate2 or sentencepiece in the image or `requirements.txt`; translation is done by
Apertus), input and output tokens reported separately in every run.

- **Step 0:** `kaan/robustness-experiments` merged whole (BM25 / bm25-mt / hybrid retrievers, strategies, local
  translation module; all off; `requirements-experiments.txt` not read by the image). Dataset README unchanged
  (`fc2b276`): field table, no label definitions beyond the names.
- **Step 1, model S** (`src/static_embed.py`): `sentence-transformers/static-similarity-mrl-multilingual-v1`
  (Apache-2.0, commit `b68f412`), token vectors averaged and normalised with tokenizers and numpy, table cut to 256
  dimensions at image build time (108 MB); equal to sentence-transformers on 50 claims (3e-8). Rankers without the
  endpoint (`scripts/ranker_check.py`, `src/rankers.py`): first cited paragraph among the 8 best, cross-language, e5
  0.980, S 0.993, S+BM25 0.985, BM25 0.945 → R = S. Through the image: task A local time at 1.0 / 0.3 / 0.1 s per
  request e5 0.017 / 0.144 / 0.365, S 0.016 / 0.018 / 0.043 s per case; peak memory 2,286 → 200 MiB.
- **Step 2, memory guard (default):** an embedding model whose need (`rankers.MIN_MEMORY`: e5 1.5 GiB, S 0.5 GiB) is
  above the container's limit, or whose files are missing or fail to load, is not used for the run: a long part sends
  its first 8 paragraphs, the fallback ranks by BM25, task B sends long references whole; counted (`ranker_guard`).
  Both tasks write every response at 4g … 512m with 2 and 1 CPUs (`docs/runs/2026-10-13_rashad_memory-guard_grid48`).
- **Step 3, task B selectors:** B-R (S) 0.973, H 0.993 (+13 % tokens), B-BM25 (Apertus translates) 0.967 against T's
  0.987 on dev: none passes TASK B RULE 2; T stays.
- **Step 4, S in task A:** dev 0.973 / 0.970 against 0.980 / 0.980 (2 breaks, 0 fixes): fails S RULE (a) by one case;
  off (`--ranker S`). Step 8 (image without e5) therefore not done.
- **Step 5, bm25-ap fallback (default):** BM25 on the claim, translated by Apertus (`AP-translate-v1`) when claim and
  booklet differ in language; forced fallback dev 0.956 / 0.736 vs 0.900 / 0.672, val 0.957 / 0.755 vs 0.875 / 0.588.
- **Step 6, AP-structure asked after the parser (default, `--ap-structure-a ask-after-parser`):** when the rules name a
  part and the parser gives no valid part, the main process asks Apertus to read the contents (one call per booklet);
  parser forced off: dev 0.946 / 0.925 vs 0.896 / 0.672, val 0.939 / 0.917 vs 0.872 / 0.593.
- **Final defaults through the published image** (`ghcr.io/rashad18236/hackapertus-voting-nli:sha-828429cab766`;
  `docs/runs/2026-10-13_rashad_final-s12_*`): dev task A 0.977 (evidence 0.980), task B 0.987; val 0.961 (0.960),
  0.969; probe 0.971 (0.969), 0.977. Tokens per case (dev, input + output): A 1,240 + 14.7, B 815 + 8.7. Local time per
  case (dev, 1.0 / 0.3 / 0.1 s per request): A 0.017 / 0.160 (repeat 0.113) / 0.364 s, B 0.012 / 0.010 / 0.161 s; probe
  task A at 0.3 s 0.237 → 0.028 s (its fallbacks no longer embed whole booklets). REF SCORE dev 0.903 / 0.845, val
  0.913 / 0.907, probe 0.897 / 0.896 (1.0 / 0.3 s). Memory: both tasks write every response at 4g, 2g, 1.5g, 1g, 768m and 512m with 2 CPUs and with 1 (below 1.5 GiB without e5:
  23 dev task A cases send their long part's first 8 paragraphs, 190 task B references go whole; peak 90 / 51 MiB). Python wrote 1 of 2,128 labels; the 8 fallback
  cases (1 dev, 3 val, 4 probe) all went through bm25-ap. `cli.main()` resets the ranker state at its start and end
  (test isolation under unittest; G1/G2 pass).
- **New replay reference for G1/G2:** `docs/runs/2026-10-13_rashad_prompt-snapshot-final-s12_devAB-valA` (also
  `scripts/local_time.py`'s default table).

## Earlier stage: session 11 (2026-10-12 20:10 UTC to 2026-10-13 10:30 UTC)

Branch `rashad/session-11` from `main` at `014f691` (PR #18, merged into `main` on 2026-10-13 as `37904b3`); status
`track_2a/docs/session_11_status.md`, decisions `docs/decisions/2026-10-12-2010_rashad_session-11.md`,
report `track_2a/docs/session_11_report.md`. Goal: unseen booklets, Apertus as parser, a fast server, memory,
task B tokens. Rules as in session 10 (sealed dates, who sets the label, the 8B on Public AI at one request per
second, one model run at a time, interleaved runs with an arm "today"), plus: no booklet-specific code (every parser
or router change states a general cause and has a unit test on a synthetic page); booklet PDFs and text never
committed; every Apertus call counts as tokens (a booklet's call in its first case); G1/G2 after every code change.

- **Parser coverage (step 1):** every federal booklet 2016–2026 in de/fr/it (93 PDFs, kept outside the repository,
  `scripts/fetch_unseen_booklets.py`; sealed dates never downloaded), checked by `scripts/parser_coverage.py`
  (cross-language: same votes, parts and start pages per date). Fixes: the contents layout used until mid-2018,
  unreadable font descriptors, a lost arguments heading, per-part validity (`Vote.valid`). Complete booklets
  64 → 88 of 93, votes passing 178 → 244 of 249, probe routed 83 → 90 of 94.
- **Fallbacks (step 2):** VW (vote-wide) and BW (booklet-wide) fail the FALLBACK RULE (val); off. Today's fallback
  (embed-e5-small) stays. The forced test is `scripts/paired_run.py`'s arm field `force` ("no part", "no vote",
  "no parser").
- **Apertus as parser (step 3, `src/ap_parse.py`):** **AP-part after the rules is a default**: when the rules find no
  part, the lane prepares every valid part and the fallback, the main process asks Apertus which part the opening
  names (one call, its tokens in the case's metrics) and sends that part's request; "none" goes to the fallback
  (HYBRID RULE: +0.073 dev, +0.051 val over VW on 150 reworded openings each; no dev, val or probe case needs it in the
  final runs: there the rules name a part for every claim). AP-structure (contents read by Apertus, checked by the parser) agrees with the parser on 78.7 % of
  votes (needs 95 %): off. AP-all is reported only (dev 0.960 vs 0.977, local time 0.822 vs 0.101 s at 0.3 s).
  Page images: accepted by the endpoint, heading not read.
- **Fast server (step 4), adopted by the SAME-ANSWER RULE:** light-first lanes (`pipeline.LIGHT_FIRST`), lazy page
  reading (`parse.LAZY_PAGES`, one open reader per process, cache key = the PDF's SHA-256), onnxruntime threads
  shared between lanes (`pipeline.SHARE_CPUS`). Task A local time at 0.3 s per request 0.202 → 0.101 s per case.
- **Memory (step 5):** one lane under a 2.5 GiB limit (`pipeline.MEMORY_FOR_TWO_LANES`): task A answers every case at
  2 GiB and 1.5 GiB with 2 CPUs (before: 3 GiB); 1 GiB fails (e5's load peak 1.16 GiB). Task B needs < 0.1 GB.
- **Task B (step 6):** **selector T is the default** (`context_b = "cut4-t"`: a reference over 3,000 characters is
  cut to its first line and the 4 paragraphs whose first 300 characters are most similar to the claim, e5):
  TASK B RULE on dev and val (0.987 / 0.968 vs 0.967 / 0.954, −59 % / −58 % input tokens, local time +0.002 s).
  E (B-cut4) and Q (8-bit e5) fail on local time at 0.3 s; H and L stay in the code.
- **Measurement setup:** model runs pinned to CPUs 0–1, timing to CPUs 2–3 (`scripts/local_time.py --cpuset`); step 4
  variants in alternating rounds. New scripts: `parser_coverage.py`, `ap_structure_check.py`, `ap_claim_search.py`,
  `ap_summary.py`, `ap_replay_table.py`, `make_reworded.py`, `fallback_local_time.py`, `taskb_selectors.py`,
  `image_check.py`; `src/timing.py` (PROFILE_PHASES=1), `src/deferral.py`.
- **Final defaults through the published image** (`ghcr.io/rashad18236/hackapertus-voting-nli:sha-bb2d08fea0f1`,
  the `session-11` tag; `docs/runs/2026-10-13_rashad_final-s11_*`): dev task A 0.980 (evidence 0.985), task B 0.987;
  val 0.959 (0.955), 0.968; probe 0.971 (0.954), 0.977. Tokens per case (dev, input + output): A 1,238 + 14.5,
  B 815 + 8.7. Local time per case (dev, 1.0 / 0.3 / 0.1 s per request): A 0.018 / 0.155 (repeat 0.108) / 0.316 s,
  B 0.010 / 0.009 / 0.130 s. REF SCORE dev 0.909 / 0.851, val 0.908 / 0.906, probe 0.897 / 0.825 (1.0 / 0.3 s).
  Memory: both tasks answer every case at 1.5 GiB; 1 GiB fails. Python wrote 1 of 2,128 labels.
- **New replay reference for G1/G2:** `docs/runs/2026-10-13_rashad_prompt-snapshot-final-s11_devAB-valA` (also
  `scripts/local_time.py`'s default table); `scripts/prompt_snapshot.py` pairs a case's parsing calls
  (`ap_request_sha256`) and G1 compares them.

## Earlier stage: session 10 (2026-10-12 11:42 UTC; ended early, merged before session 11)

Branch `rashad/session-10` from `main` at `42b2a3c` (PR #17, merged into `main` on 2026-10-12 as `014f691`); status
`track_2a/docs/session_10_status.md`, decisions `docs/decisions/2026-10-12-1142_rashad_session-10.md`,
report at the end `track_2a/docs/session_10_report.md`. Goal: score what the organisers score
(`track_2a/docs/official_scoring.md`): tokens and local time per case now count, not only Macro-F1.

- **Sealed:** the test rows dated 2020-02-09, 2022-02-13 and 2022-05-15 are never run, parsed or opened.
  The test rows dated 2021-03-07 and 2025-09-28 are copied to `data/probe/` and may be used like dev from
  step 4 on. `data/test/`, the splits file and the scorer stay unchanged.
- **Who sets the label:** every label comes from an answer of Apertus. Python never changes a label Apertus
  gave and never decides one in its place; the only label Python writes is the neutral fallback when a call
  fails or its answer cannot be read, counted in every run.
- **Model:** only the 8B named in `.env` on Public AI (no 70B, no thinking variant); at most one request per
  second; one model run at a time. Every comparison is one interleaved run with an arm "today" (the defaults
  at that moment); dev for exploring, val only for confirming.
- **REF SCORE** (`scripts/official_score.py`): fixed reference "best" values, tokens per case 600 (A) and
  800 (B), local time per case 0.05 s (A) and 0.005 s (B); always reported with its parts.
- **Defaults changed in session 10, each by its rule:** cases are prepared in two forked worker processes
  ("lanes", `src/pipeline.py`; each owns whole booklets) while the main process sends requests over one kept
  connection; each booklet parsed once; ONNX threads = the CPU limit; `src/` compiled in the image (same
  answers, G1/G2; local time per case on dev, model at 1.0 / 0.3 s per request: task A 0.803 / 0.742 s → 0.017 / 0.154 s,
  task B 0.985 / 0.939 s → 0.010 / 0.007 s). Task B sends the whole reference again (no B-cut: e5's local time costs
  more REF SCORE than its tokens save). A vote name the title match cannot place is placed by meaning (e5,
  lead ≥ 0.04; G1/G2 unchanged).
- **Tried, not adopted:** P-short, P-short+K4, BP-short, BP-short+B-cut4 (fail on dev); K4 (fails on val);
  B-cut4 (passes the TOKEN RULE, −55 % task B tokens, but lowers REF SCORE through e5 local time); CS, SL (step
  6, fail their rules); B-U (adds output tokens). Without `response_format` 0 of 100 answers unreadable.
- **Final defaults through the published image** (`ghcr.io/rashad18236/hackapertus-voting-nli:sha-421d8c804677`,
  task A and B in separate containers; `docs/runs/2026-10-12_rashad_final-defaults_*`): dev task A 0.983
  (evidence 0.980), task B 0.967; val 0.959 (0.955), 0.961; probe 0.960 (0.908), 0.971. Tokens per case (dev,
  input + output): A 1,238 + 14.5, B 1,994 + 8.4. REF SCORE dev 0.870 / 0.824, val 0.873 / 0.888, probe 0.850 / 0.777 (1.0 / 0.3 s
  per request). Python wrote 6 of 2,128 labels (neutral fallbacks for unreadable task B answers).
- **Probe:** 5 of 6 booklets parse; `2025_09_28_fr`'s first vote is not found (8 fallbacks), reported, not fixed.
- **The Python rule "neutral with a citation → contradiction"** was scored offline only (val +0.014, on-topic
  neutral set 3 of 3 changes wrong); it is not in `src/`.
- **New replay reference for G1/G2:** `docs/runs/2026-10-12_rashad_prompt-snapshot-final-s10_devAB-valA` (the
  final runs' 1,180 dev and val answers; also `scripts/local_time.py`'s default table).
- **The published image:** `.github/workflows/publish-image.yml` (tags: commit, `session-10`, `latest` from
  `main`); after a merge into `main`, check that `latest` pulls without logging in.

## Earlier stage: session 9 (2026-10-09 17:07 UTC to 2026-10-10 13:00 UTC)

Branch `rashad/until-1600` from `main` at `418ebfa` (PR #16, merged into `main` on 2026-10-10 as `42b2a3c`); report
`track_2a/docs/session_9_report.md`, status log `track_2a/docs/session_9_status.md`, decisions
`docs/decisions/2026-10-09-1707_rashad_session-9.md`. Model runs on Public AI's `apertus-v1.5-8b`, at most
one request per second (`LLM_MIN_INTERVAL=1` for `make run`), one run at a time; every comparison is one
interleaved run, reported on all cases and on cases where all versions met the same backend (all of
session 9's answers came from one backend, blablador).

- **Defaults changed in session 9, each by a fixed rule:** task A evidence adds halves of the cited
  paragraphs up to five items (A2; replayed answers: evidence dev 0.906 → 0.925, val 0.946 → 0.956, labels
  unchanged); task B cuts references over 8,000 characters to the first line plus the 8 paragraphs most
  similar to the claim (`--context-b cut`; dev 0.967 = 0.967, val 0.961 vs 0.957, −37 to −38 % input
  tokens); task A's routed prompt adds one sentence on contradictions (`A-v4-section-route-L1`,
  `label_rule_a`; dev 0.980 vs 0.966, val 0.961 vs 0.950, neutral recall 1.000).
- **Kept off:** B-para (task B as numbered paragraphs, 0.963), L2 (a second look at neutral answers:
  +0.010 dev, +0.003 val, below its +0.015 bar), `closed-book` and `--section-top-k-a` (phase E,
  information only).
- `src/llm.py` falls back when the endpoint refuses `response_format` (resend without it) or the model name
  (reads `BASE_URL/models`, picks the Apertus v1.5 8B id), at most three extra requests per run.
- Offline analyses (`docs/analysis_offline.md`): all of E6's routed val errors are reading errors; task B
  references over 8,000 characters are 99 of 105 times neutral on dev (a dataset artefact, never used).
- **New replay reference for G1/G2:** `docs/runs/2026-10-09_rashad_prompt-snapshot-final_devAB-valA`
  (final defaults; all 1,180 dev and val requests answered from saved real answers: the final dev run and
  the val L1 arm; replay reproduces dev A 0.980 / 0.980, B 0.967, val A 0.961 / 0.958). It replaces the
  session 8 reference.
- **Final defaults on all 600 dev cases through the image** (`2026-10-09_rashad_final-defaults_dev600`):
  task A 0.980 (evidence 0.980, 1,238 input tokens), task B 0.967 (1,231 input tokens).
- **Stability** (the image from before session 9's default changes, same settings, all 600 dev cases, at
  17:28, 01:56 and 09:56 UTC): task A 0.966 / 0.966 / 0.966, task B 0.967 / 0.967 / 0.963; two of 600 labels
  ever changed; one backend throughout.

## Earlier stage: hardening without a model (session 8)

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
- Requests go out one at a time (cases are prepared in two worker processes
  since session 10); one retry for HTTP 5xx, timeouts and a lost connection,
  up to two for HTTP 429.
- A change to `src/` that should not change answers is checked with G1 and G2
  against the session 10 reference (`scripts/prompt_snapshot.py`,
  `docs/runs/2026-10-12_rashad_prompt-snapshot-final-s10_devAB-valA`).
- Local models only under the model rule above. Ask before adding another one
  (each is a heavy dependency).

Earlier: session 2 (PR #3) set task B to 0.947 with `v3-topic-first`
(default, unchanged since) and measured the task A full-document baseline
(0.589, 37 % of answers not valid JSON).

## Open questions (do not assume the answers)

- Whether the evidence page is checked against the 1-based PDF page in the
  official run (the starter says pages are "not checked yet").
- Whether booklet parsing must use Apertus or may be local. Working
  assumption: local parsing is allowed (contract wording), until told otherwise.
- Where the dataset README's label definitions are (the README is still
  licence-only as of 2026-10-08).
- Which Apertus model and server the evaluation calls (8B or another v1.5
  variant; CSCS or Public AI), and on what hardware the image runs.
- Whether the official evaluation, like the starter, ignores extra evidence
  items, and whether evidence on a neutral answer counts.
