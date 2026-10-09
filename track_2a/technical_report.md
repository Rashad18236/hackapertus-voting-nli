# Technical report — NLI over Swiss federal voting booklets with Apertus

A deeper write-up than the README: what we built, how it works, and what the
numbers say. Every number below comes from a recorded run in `docs/runs/`
(folder named in brackets) on the **dev split**; the test split has not been
run. Gaps are marked **TODO**.

- **Track:** `Track 2A — OST: Multilingual Natural Language Inference over Swiss Official Voting Booklets`
- **Event:** Online
- **Team:** TODO team name — Rashad, Kaan (TODO full names)
- **Demo:** TODO (no demo link yet)

## 1. Summary

Given a claim in German, French or Italian and a source from an official Swiss
federal voting booklet, the system decides whether the source supports
(entailment, 0), does not settle (neutral, 1) or refutes (contradiction, 2) the
claim. The source is either a passage (task B) or a whole booklet PDF (task A).
**Apertus v1.5 makes every decision**, in one call per case. Everything else is
local, deterministic and runs on CPU inside the Docker image: PDF parsing,
choosing what part of the booklet Apertus reads, and turning the paragraphs or
pages Apertus cites into evidence quoted verbatim from the booklet with their
1-based PDF page.

Headline dev results (official starter scorer):

- **Task B:** the prompt `v3-topic-first` (the default, unchanged since
  session 2) on all 300 dev task B cases, one row per recorded run. The prompt
  and the requested model name were the same in every run; what Public AI
  served under that name was not (section 6):

  | Date, start (UTC) | Run folder | Macro-F1 | Input tokens / case | Mean / p95 time |
  |---|---|---|---|---|
  | 2026-10-08 06:10, before the endpoint changed (about 13:25) | `s2-A-v3-topic-first` | 0.947 | 1,968 | 2.7 s / 2.9 s |
  | 2026-10-09 01:25, confirmation run 1 | `2026-10-09_rashad_v3-topic-first_devB300-run1` | 0.919 | 1,994 | 1.6 s / 2.8 s |
  | 2026-10-09 01:33, confirmation run 2 | `2026-10-09_rashad_v3-topic-first_devB300-run2` | 0.916 | 1,992 | 0.6 s / 0.8 s |
  | 2026-10-09 02:11, four-arm run, arm A | `2026-10-09_rashad_taskb-4arm_devB300/A-v3-plain` | 0.867 | 1,994 | 1.4 s / 2.3 s |

  Run 2 sent run 1's requests again 3 to 8 minutes later; its answers equal
  run 1's in all 299 cases both answered, and its speed very likely comes from
  the gateway's cache of identical requests, not the model (run notes). Arm A
  was answered by two backends (section 6) and includes 12 answers from that
  cache.
- **Task A, central experiment (full document against selected context):** with
  the same prompt and answer schema, sending only the vote's pages instead of
  the whole booklet raised Macro-F1 from 0.669 to 0.732 and cut input tokens
  from 39,206 to 15,868 per case [`s3-E2-A300`, paired].
- **Task A, the default since session 7:** `section-route` (send the part of
  the vote the claim names, as numbered paragraphs) reached Macro-F1 **0.953**
  and evidence **0.905** with 1,210 input tokens per case and a p95 time of
  3.9 s, against 0.834 / 0.662 / 1,868 / 11.7 s for `embed-e5-small`
  [`2026-10-08_rashad_section-route-vs-embed_devA300`, paired], and held on
  300 validation cases nobody looked at while building it: **0.956** /
  **0.946** / 1,222 / 3.0 s against 0.865 / 0.588 / 1,827 / 12.3 s
  [`2026-10-09_rashad_section-route-vs-embed_valA300`, paired].

Both tasks are above the starter's minimum for a valid submission (task B
0.75, task A 0.60) on dev. The private test set may differ (section 6).

## 2. Architecture

```
cases.jsonl ──► src/cli.py ──┬─ task B: reference text + claim ──────────────► src/nli.py prompt ─┐
 (one request per line)      │                                                                   │
                             └─ task A: booklet PDF ─► src/parse.py (pypdf, text per page,      │
                                                       1-based pages, cache in /tmp)             │
                                  │                                                              ▼
                                  ├─ section-route: src/claim_router.py (part named by the   src/llm.py ──► BASE_URL
                                  │   claim's opening) + src/booklet.py (votes and parts)     (the only     (Apertus v1.5,
                                  │   ─► numbered paragraphs of that part                     remote call)   OpenAI-compatible)
                                  └─ fallback / default embed-e5-small: src/contexts/              │
                                      embed_e5_small.py (top 8 chunks, multilingual-e5-small)      ▼
                                                                                 label + cited paragraphs/pages
                                                       src/evidence.py, section_route.evidence_items ─► evidence
                                                                                           ▼
                                                                           predictions.jsonl (one line per id)
```

- `src/cli.py`: the official entrypoint (`--input`, `--output`). Reads every
  line, answers every request that has an id, never stops on one bad case
  (fallback answer: neutral with empty evidence), exit code 0.
- `src/llm.py`: the only module that calls a model. One OpenAI-style
  `chat/completions` request per case to `BASE_URL` with `API_KEY`
  (environment first; `LLM_BASE_URL`/`LLM_API_KEY` as local fallback), model
  from `MODEL`. Temperature 0. One retry for HTTP 5xx and timeouts; for
  HTTP 429 (rate limit) up to two retries, each after the server's
  `Retry-After` time (else 2 s, then 4 s; at most 10 s). Tokens of every
  attempt are summed into the case's metrics, and the waits count in its
  time.
- `src/nli.py`: prompts (versioned by name) and answer parsing.
- `src/context.py` and `src/contexts/`: the task A context variants (one file
  each; a variant's name never changes meaning).
- `src/booklet.py`, `src/claim_router.py`: the parser and router behind
  `section-route`.
- `src/evidence.py`: task A evidence settings for page-based variants.

Everything runs in one Docker container (`linux/amd64`, CPU only, no GPU);
the only network traffic is the model call to `BASE_URL`.

### 2.1 How document context is prepared and supplied to the model

This section answers the challenge's request to document parsing, page
numbers, selection and prompt contents.

**Parsing.** `src/parse.py` reads the PDF with pypdf (BSD licence) and keeps
the text of each page with its 1-based PDF page number (page *n* is the *n*-th
page of the file, not the number printed on it). Parsing runs locally; no
model is involved. The page texts are cached as JSON in `/tmp` under the
file's SHA-256, so a result never depends on which case asked first.

**Selection.** Which text Apertus reads is chosen by the task A context
variant (`--context-a`):

| Variant | What Apertus reads | Prompt |
|---|---|---|
| `full` | every page, each after a line `=== PAGE n ===` (the full-document baseline) | `A-v3-fulldoc` |
| `vote-section` | only the pages about the vote named in `vote`, found from page headers | `A-v3-fulldoc` |
| `embed-e5-small` (the default until session 7; `section-route`'s fallback) | the 8 chunks (at most 1,000 characters, cut at whitespace) most similar to the claim by cosine similarity of multilingual-e5-small embeddings (`query:`/`passage:` prefixes), in page order, each after `=== PAGE n ===` | `A-v3-excerpts` |
| `section-route` (**default** since session 7) | the part of the vote that the claim's opening names, as numbered paragraphs (below); runs as `embed-e5-small` when it cannot route or routing fails | `A-v4-section-route` |

**`section-route` in detail.**

1. *Router* (`src/claim_router.py`): the dataset's claims open with a formula
   that names their source, e.g. "Laut der Zusammenfassung …" (summary),
   "Le Conseil fédéral estime …" (the Federal Council's arguments), "Il
   comitato afferma …" (the committee's arguments), "Laut dem
   Abstimmungstext …" (the text put to the vote), "Si le vote est accepté …"
   (the detailed explanation). Regular expressions on the normalised opening
   map it to one of five parts, or to nothing.
2. *Parser* (`src/booklet.py`): reads the table of contents ("In Kürze 4 – 5 /
   Im Detail 8 / Argumente 14 / Abstimmungstext 18" and the French and
   Italian equivalents) into one entry per vote, checks every start page
   against the heading printed on that page, splits the arguments into the
   committee's, a parliamentary debate where there is one, and the Federal
   Council's, and splits the summary pages' recommendation boxes per voice.
   A vote that fails a check gets no parts, so the case falls back instead of
   guessing.
3. *Vote match*: the case's `vote` is matched to a contents title by fuzzy
   partial ratio (at least 80, and at least 5 points ahead of the next vote).
4. *Paragraphs*: the part's pages are split into paragraphs that keep the page
   text's lines; running headers, page numbers and fragments under 40
   characters are dropped. Each paragraph keeps its page. The committee's and
   the council's parts also get their recommendation boxes. If the part has
   more than 8,000 characters, only the 8 paragraphs most similar to the claim
   (multilingual-e5-small) are sent, in page order.

**What the prompt contains.** System message: the instruction and decision
rule (for `A-v4-section-route`, task B's `v3-topic-first` rule word for word,
full text in `src/nli.py`):

> Decide in this order: 1. Does the reference text deal with the subject of
> the claim at all? If not, the label is 1 (neutral). 2. If it does: 0
> (entailment) if the reference text supports the claim; 2 (contradiction)
> only if the reference text states something that cannot be true together
> with the claim; otherwise 1 (neutral: insufficient information). Missing
> information is never a contradiction. […]

User message: `PART: <which part and whose voice>`, `REFERENCE TEXT:` with the
numbered paragraphs `[1] … [n]`, `VOTE: <vote name>`, `CLAIM: <claim>`. Claims
and booklet text are never translated. The answer is forced by
`response_format: json_schema` to `{"paragraphs": [at most 3 numbers],
"label": 0|1|2}` (page variants: `{"pages": [at most 5], "label": …}`).
Task B sends `REFERENCE TEXT:` and `CLAIM:`; its answer format,
`{"label": …}`, is requested in the prompt only: task B sends no
`response_format`.

**Evidence.** Only what Apertus cited, quoted from the booklet with its page
(team decision, session 5): for `section-route` the cited paragraphs
(at most 3); for page variants the cited pages cut into pieces of at most
1,000 characters (`cited-pieces`, at most 5 items). Neutral answers and task B
answers carry no evidence.

## 3. Use of Apertus

- **Model:** Apertus v1.5, named by `MODEL` (default
  `swiss-ai/Apertus-v1.5-8B`). Dev runs used `swiss-ai/apertus-v1.5-8b` on
  Public AI; when it was down, `swiss-ai/apertus-v1.5-8b-thinking` (all of
  E4, cases 181–300 of E3). **TODO:** which Apertus model and server the
  evaluation uses is not known to us.
- **How it is used:** inference only, zero-shot, one call per case,
  temperature 0, answer budget 128 tokens (task A) and 32 tokens (task B).
  Task A's answer is schema-constrained (`response_format: json_schema`);
  task B's answer format is requested in the prompt only (no
  `response_format`). The option `--schema-b` forces `{"label": 0|1|2}` by
  json_schema; it is off, because in the four-arm run it scored 0.853
  against 0.867 without it, all of the gap in cases where the two arms met
  different backends (section 6). No fine-tuning.
- **Where it runs:** a hosted OpenAI-compatible endpoint reached only through
  `BASE_URL` (at evaluation, the organisers' token-counting proxy). No key or
  `.env` is in the image.
- **Apertus makes every entailment decision.** The local embedding model
  (multilingual-e5-small, MIT licence, open weights, ONNX, pinned commit
  `614241f6`, baked into the image at build time, CPU via onnxruntime) only
  chooses which chunks or paragraphs Apertus reads.
- **Label definitions:** the dataset README (commit `9ff08597`) held only its
  licence when the prompts were written, so the prompts use the official
  guide's wording (supports = entailment, insufficient information = neutral,
  refutes = contradiction). **TODO:** check the README again and quote its
  definitions once they appear.
- **Development tools:** Claude Code was used to write code and run
  experiments. It is not part of the solution and is never called by the
  pipeline.

## 4. Data

- **Dataset:** `OSTswiss/MNLIoverSwissVotingBooklets` v1.1, commit
  `9ff08597`, MIT licence: 1,488 rows, 335 of them exact duplicates
  (`docs/dataset_profile.md`). Each row gives one task A and one task B case.
- **Splits** (`data/README.md`): by voting date, seed 42, duplicates removed.
  Test: 5 booklet dates, 267 rows (534 cases), **never run**. Dev: 300 rows
  (600 cases) from the other 15 dates, balanced over labels and the nine
  language pairs (labels 102 / 99 / 99). Validation (session 7,
  `data/val/`): the 580 deduplicated rows in neither dev nor test (minus six
  whose openings were used to write router patterns), task A only, with a
  balanced sample of 300 for paired runs; same voting dates as dev, new
  claims.
- **Booklets:** the Federal Chancellery's PDFs, downloaded from the dataset's
  `booklet_url` by `scripts/fetch_dev_booklets.py` and not committed (one
  example booklet in `examples/booklets/` for `make run`). **TODO:** the
  booklets' terms of use were not checked.
- **Personal data:** none; official public documents. `data/` is 9.6 MB
  (limit 100 MB).

## 5. Evaluation

**Metric.** The starter's `evaluate.py` (commit `559b598`), run unchanged:
Macro-F1 per task from labels only (missing, duplicated or invalid responses
count as wrong), and for task A the evidence score (share of gold
entailment/contradiction cases where one of the first five evidence items
fuzzy-matches the gold passage, partial ratio ≥ 90). Tokens and time are the
pipeline's own metrics per case. Because the endpoint's answers drifted
during the day (same prompt, temperature 0, different answers), **only the
two arms of one paired run compare**: both settings run on the same case back
to back.

| Setup (run folder) | Model | Macro-F1 | Evidence | Input tokens / case | Mean / p95 time |
|---|---|---|---|---|---|
| **Task B** | | | | | |
| `v2-label-only`, 2026-10-08 05:29 [`contract-v2-dev`] | 8b | 0.541 | – | 1,963 | 1.9 s / 2.8 s |
| `v3-topic-first` (default), 2026-10-08 06:10 [`s2-A-v3-topic-first`] | 8b | 0.947 | – | 1,968 | 2.7 s / 2.9 s |
| `v4-topic-first-examples`, 2026-10-08 06:24 [`s2-C-v4-topic-first-examples`] | 8b | 0.933 | – | 2,162 | 1.8 s / 3.0 s |
| `v3-topic-first`, 2026-10-09 01:25 [`2026-10-09_rashad_v3-topic-first_devB300-run1`] | 8b | 0.919 | – | 1,994 | 1.6 s / 2.8 s |
| `v3-topic-first`, 2026-10-09 01:33 [`2026-10-09_rashad_v3-topic-first_devB300-run2`] | 8b | 0.916 | – | 1,992 | 0.6 s / 0.8 s |
| `v3-topic-first`, 2026-10-09 02:11, arm A [`2026-10-09_rashad_taskb-4arm_devB300/A-v3-plain`] | 8b, two backends | 0.867 | – | 1,994 | 1.4 s / 2.3 s |
| **Task A: full-document baseline** | | | | | |
| `full`, answer format by prompt [`s2-A300-A-v3-fulldoc`] | 8b | 0.589 | 0.209 | 39,706 | 11.5 s / 30.3 s |
| **Task A, E2 (paired): full document against selected context** | | | | | |
| `full` + json_schema [`s3-E2-A300/fulldoc-schema`] | 8b | 0.669 | 0.284 | 39,206 | 12.7 s / 37.1 s |
| `vote-section` + json_schema [`s3-E2-A300/section-schema`] | 8b | **0.732** | 0.224 | 15,868 | 8.2 s / 13.5 s |
| **Task A, E3 (paired)** [`2026-10-08_rashad_embed-vs-section_devA300`] | 8b, then thinking | | | | |
| `embed-e5-small` | | **0.721** | 0.383 | 1,831 | 6.9 s / 16.1 s |
| `vote-section` | | 0.561 | 0.095 | 15,863 | 6.0 s / 9.3 s |
| **Task A, E4 (paired)** [`2026-10-08_rashad_section-k12-vs-embed-thinking_devA300`] | thinking | | | | |
| `embed-e5-small` | | **0.711** | 0.373 | 1,868 | 3.0 s / 11.4 s |
| `vote-section-embed-e5-small-k12` | | 0.674 | 0.403 | 2,777 | 2.9 s / 5.8 s |
| **Task A, E5 (paired)** [`2026-10-08_rashad_section-route-vs-embed_devA300`] | 8b | | | | |
| `section-route` | | **0.953** | **0.905** | 1,210 | 2.0 s / 3.9 s |
| `embed-e5-small` | | 0.834 | 0.662 | 1,868 | 3.2 s / 11.7 s |
| **Task A, validation set (paired)** [`2026-10-09_rashad_section-route-vs-embed_valA300`] | 8b | | | | |
| `section-route` | | **0.956** | **0.946** | 1,222 | 1.8 s / 3.0 s |
| `embed-e5-small` | | 0.865 | 0.588 | 1,827 | 3.2 s / 12.3 s |

"8b" = `swiss-ai/apertus-v1.5-8b`, "thinking" = `swiss-ai/apertus-v1.5-8b-thinking`,
both on Public AI. Times are wall-clock per case as the pipeline records them.
The three task B runs of 2026-10-08 ran before Public AI changed what it
serves as `apertus-v1.5-8b` (about 13:25 UTC); the three of 2026-10-09 after
it. Only the four-arm run recorded which backend answered (section 6).

Further measured steps:

- **Unreadable answers (task A):** asking for JSON in the prompt left 110 of
  300 full-document answers unparseable [`s2-A300-A-v3-fulldoc`]; with
  `response_format: json_schema` no task A answer has been unparseable since
  (E2 to E5).
- **Evidence form** (E4's answers re-scored, labels unchanged): pieces of the
  cited pages 0.542 against whole cited pages 0.373
  [`2026-10-08_rashad_evidence-cited-pieces-e4_devA300`,
  `2026-10-08_rashad_evidence-forms-e4_devA300`].
- **Offline selection checks** (no model calls): the embedding's top 8
  chunks hold the gold passage in 0.741 of the 201 evidence cases (same
  language 0.851, cross-language 0.687)
  [`2026-10-08_kaan_retrieval-check_embed-e5-small`]; the routed part holds it
  in 200 of 200 routed evidence cases, and all 44 dev booklets parse (131 of
  131 votes) [`2026-10-08_rashad_route-check_devA300`]; on the validation
  set, 577 of 580 cases are routed and the routed part holds the gold passage
  in 399 of 400 [`2026-10-09_rashad_route-check_valA580`].
- **E5 in detail:** `section-route` was right where the embedding was wrong
  in 45 cases and the reverse in 9 (sign test on the 54 discordant cases: p = 7e-7); 11 of its 14
  wrong answers call a supported or refuted claim neutral. In all 14, a
  paragraph sent to Apertus lies inside the gold passage, so they are reading
  errors, not selection misses (`docs/remaining_errors.md`).

**Checks without a model** (2026-10-09, `docs/checks_no_model.md`):

- Contract tests against a fake model (`scripts/stub_llm.py`,
  `tests/test_contract.py`): every request with a readable id gets exactly one
  valid response and exit code 0, with mixed tasks, malformed lines, missing
  fields, missing or broken booklets, empty claims, unknown languages, failed
  and garbage model answers; the same cases in three orders give identical
  labels and evidence; only `/output` and `/tmp` are written. Three gaps in
  `src/cli.py` (a repeated id, a UTF-8 byte order mark, a byte that is not
  UTF-8) were expected failures until branch `rashad/input-hardening`, which
  reads the input as bytes split on line feeds only, answers each id once and
  writes each response as soon as it is ready.
- Evidence of both E5 arms [`2026-10-09_rashad_evidence-check_devA300`]: no
  item over 5,000 characters, no response with more than five items, no
  evidence on a neutral answer, every page exists. Every `embed-e5-small`
  item is verbatim on its page; 12 of 284 `section-route` items are not one
  contiguous piece of their page, because the parser drops stray `-` lines or
  a page number inside the paragraph (partial ratio against the page ≥ 99.0).
- Booklets outside dev and test [`2026-10-09_rashad_unseen-booklets_15`]:
  the 2026-09-27 booklet (after the dataset) parses completely in all three
  languages; the 2018–2019 booklets find their votes but no parts, because
  their arguments are titled "Argumente Bundesrat" without "und Parlament".
- Router stress test [`2026-10-09_rashad_router-stress_300`]: of 300 reworded
  claim openings written for the test, 131 are routed to the intended part,
  4 to a wrong part, and the rest fall back to `embed-e5-small`.
- Speed and memory without the model [`2026-10-09_rashad_speed-memory_dev44`],
  all 300 dev task A cases end to end in the image limited to 2 CPUs and
  4 GB: `embed-e5-small` p95 19.3 s, worst 44.4 s per case (the first case
  on a large booklet embeds the whole booklet), peak 1.8 GiB;
  `section-route` p95 3.7 s, worst 31.9 s (four long law texts whose
  paragraphs are all embedded), peak 2.7 GiB. Cold start with one task A
  case: 26–27 s with `embed-e5-small`, 3 s with `section-route`.

## 6. Limitations

- **Tuned on the 300 dev cases.** Prompts, the router's patterns, the
  parser's checks and the vote-match threshold were written with the dev data
  in view. The validation set (new claims, same booklets) confirms the result
  (0.956); new booklets were checked only offline (section 5); the test split
  and the private set have not been run.
- **`section-route` depends on the claims' openings.** Claims that name their
  source in another way fall back to `embed-e5-small` (still answered, not
  better); the stress test above shows which wordings do. A source named
  after the subject ("Der Bundesrat ist laut Zusammenfassung …") is routed to
  the wrong part.
- **The parser depends on the 2020–2026 booklet layout.** Older booklets parse
  to votes without parts, and such cases fall back. Some pages hold no
  extractable text.
- **Endpoint drift and the evaluation model.** Public AI's
  `apertus-v1.5-8b` changed its answers during 2026-10-08 (about 13:25 UTC)
  and again on 2026-10-09 between confirmation run 1 (from 01:25 UTC) and
  01:50 UTC (3 of the 30 task B canary answers differ, `docs/canary_log.md`;
  run 2 cannot narrow it, as its answers very likely came from the gateway's
  cache). Results from different runs do not compare, and the evaluation's
  model and server are unknown. Task B shows the size of it: the same prompt
  scored 0.947, 0.919, 0.916 and 0.867 in four runs (section 1).
- **Public AI served two backends under one model name.** In the four-arm
  task B run of 2026-10-09 [`2026-10-09_rashad_taskb-4arm_devB300`], every
  request named `swiss-ai/apertus-v1.5-8b` and every response body gave the
  same name back as `model`. Public AI's gateway (LiteLLM) sent each request
  to one of two deployments, and the response headers name the deployment
  and the model name it was set up with (`x-litellm-model-name`):

  | Backend (`x-litellm-model-api-base`) | Its model name | `system_fingerprint` | Answers of 1,200 |
  |---|---|---|---|
  | `https://api.blablador.fz-juelich.de/v1` | `openai/alias-apertus` | `vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840` | 737 |
  | `https://api.featherless.ai/v1` | `openai/swiss-ai/Apertus-8B-Instruct-2509` | `fp1-nst-nes` | 463 |

  The first name is an alias with no version. The second is the September
  2025 Apertus release (v1), not v1.5. Which weights either backend serves is
  not visible from outside. The backend changes the answers: arms A and B
  send the same prompt, and their labels differ in 3 of the 250 cases where
  both met the same backend but in 19 of the 50 where they met different
  ones. Arm A's 0.867 therefore mixes two backends (189 and 111 of its 300
  answers). The earlier runs recorded no backend, so which one answered
  them is unknown.
  `src/llm.py` records these fields for every call (`endpoint` in the raw
  answers) since the four-arm run's code (`75171d7`).
- **Evidence pages:** the starter's scorer does not check pages; whether the
  official one does is unknown. Our pages are the 1-based PDF pages the cited
  text comes from.
- **Input robustness:** a repeated id is answered once (its first line); a
  line that is not valid JSON or has no id gets no response, since there is no
  id to answer (the official input is expected to be valid JSON lines).
- **Not political advice.** The system checks a claim against the booklet's
  text only. Its answers are not voting recommendations and must not be read
  as such. Every task A label 0 or 2 comes with the booklet page and the
  verbatim text it rests on, so it can be traced to the source booklet.

## 7. Reproducibility

- **Run:** `make run` (from `track_2a/`) builds the image (`linux/amd64`) and
  answers `examples/cases.jsonl`; `BASE_URL`, `API_KEY` and optionally `MODEL`
  come from the environment (or a local `.env`, never in the image). For the
  dev split: `make run CASES=data/dev/cases.jsonl BOOKLETS=output/booklets_dev
  OUTPUT_DIR=output/dev` after `python3 scripts/fetch_dev_booklets.py`; score
  with the starter's `evaluate.py`.
- **Hardware:** CPU only. The image is 1.29 GB uncompressed (681 MB
  compressed); `make build` took 17–25 s on a fresh GitHub runner, and the
  cold run on the two examples 3 s (`docs/checks_no_model.md`). TODO: the
  organisers' evaluation hardware is unknown.
- **Determinism:** temperature 0, local steps deterministic, booklet cache
  keyed by content; split seed 42. The endpoint's own drift is outside our
  control (section 6).
- **Exact commits:** E5 ran at commit `02ecd5d`; every run folder names its
  code. TODO: the final submission's commit and tag (`submission`).
- **Clean machine:** `.github/workflows/clean-machine.yml` builds the image
  with `make build` on a fresh runner and runs it on the examples with no
  internet access, a read-only root filesystem and read-only `/data`, against
  the fake model; it passed on GitHub (build 17–25 s; the cold run on the
  two examples takes 3 s with the `section-route` default, 18–19 s when the
  default was `embed-e5-small`).
- **Speed and memory:** without model latency, a task A case takes
  milliseconds once its booklet is prepared; the first case on a booklet pays
  for parsing (up to 3.5 s) and, with `embed-e5-small`, for embedding the
  whole booklet (up to 44.8 s on 2 CPUs). Peak memory is at most 2.8 GiB
  [`2026-10-09_rashad_speed-memory_dev44`].

## 8. Next steps

- Tag the submission (`section-route` is the default since session 7).
- One change per paired comparison: a larger character budget for long detail
  and law parts instead of the 8 most similar paragraphs; the remaining
  "called neutral" errors (all 14 are reading errors).
- Router and parser: the patterns proposed in `docs/checks_no_model.md`
  (measured offline: 273 of 300 reworded openings routed right, no change on
  the dataset's own claims; 14 of 15 older booklets parsed fully, no change on
  dev).

## License

Creative Commons Attribution 4.0 (CC-BY-4.0). All HackApertus projects are
open-sourced. TODO: the repository's `LICENSE` file is Apache-2.0; the team
should make the two agree.

## References

- Dataset: OSTswiss/MNLIoverSwissVotingBooklets, v1.1, Hugging Face (MIT).
- Organisers' starter: `https://gitlab.com/ifsoftware/hackapertus-starter`, commit `559b598`.
- Apertus v1.5 models, Swiss AI Initiative (`swiss-ai/Apertus-v1.5-...`).
- Wang, L. et al. (2024). *Multilingual E5 Text Embeddings: A Technical Report.* arXiv:2402.05672.
  Model: `intfloat/multilingual-e5-small` (MIT).
- pypdf (BSD-3-Clause), rapidfuzz (MIT), onnxruntime (MIT), tokenizers (Apache-2.0).
