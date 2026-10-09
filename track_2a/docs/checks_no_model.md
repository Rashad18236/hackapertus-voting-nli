# Checks without a model (2026-10-09)

Nine checks of the submission that need no model call, asked by Rashad and run
autonomously on branch `checks-no-model` (from `main` at `de27e4c`), PR
[#12](https://github.com/Rashad18236/hackapertus-voting-nli/pull/12).

Ground rules kept: **no model calls**, `.env` never loaded, no API key used;
the **test split was never used** and no test booklet was opened;
`src/cli.py`, `src/booklet.py`, `src/claim_router.py`, `src/contexts/` and
`data/` were **not changed** (another session works on them; what they need
is in [Proposals](#proposals)). Nothing was merged.

## Summary

| Part | Check | Result |
|---|---|---|
| 1 | Fake model `scripts/stub_llm.py` | **Done.** Chat-completions server, fixed valid answer and token counts, failures and garbage by call number or by marker |
| 2 | Contract tests `tests/test_contract.py` (real CLI, fake model over HTTP) | **Pass**: 23 tests (with the e5 files and `CONTRACT_SLOW=1`; 21 pass and 2 skip without them, as in CI), **3 expected failures** = gaps in `src/cli.py` (duplicate ids, byte order mark, invalid UTF-8) |
| 3 | Evidence of session 6's two arms against the booklet pages | **embed-e5-small: pass. section-route: 12 of 284 items fail "verbatim"** (not one contiguous piece of their page); every other rule passes in both arms |
| 4 | Clean-machine workflow `.github/workflows/clean-machine.yml` | **Pass on GitHub** (no internet, read-only root and `/data`): image 1.29 GB uncompressed, build 19–22 s, cold run on the examples 19 s. Reproduced locally |
| 5 | 15 unseen booklets (5 dates outside dev and test) | **2026-09-27: 3 of 3 complete. 2018–2019: 0 of 12** (votes found, no parts). Proposal: 14 of 15, dev unchanged |
| 6 | Router stress test, 300 reworded openings | **131 right, 4 wrong part, 153 fall back**, 12 correct fallbacks. Proposal: 273 right, 0 wrong, dataset routes unchanged |
| 7 | Speed and memory per dev booklet, host and container (2 CPUs, 4 GB) | **Measured.** Container, 300 dev cases without the model: default context p95 19.3 s, worst 44.4 s, peak 1.8 GiB; section-route p95 3.7 s, worst 31.9 s (long law parts), peak 2.7 GiB (under 4 GB). Cold start, one task A case: 26–27 s (default), 3 s (section-route) |
| 8 | Hygiene: secrets in git history, licences, sizes | **No secret found** (every commit on all refs); the image's Python packages and the e5 model are permissive (MPL-2.0 for two), its Debian base has the usual GPL/LGPL packages; `data/` 9.6 MB; image 1.29 GB uncompressed (681 MB compressed) |
| 9 | `technical_report.md`, `docs/remaining_errors.md` | **Written**; gaps marked TODO; the 14 errors are all reading errors |

## Part 1: fake model

`scripts/stub_llm.py` (standard library only, so it also runs inside the image):

- `POST /v1/chat/completions` (or `/chat/completions`) answers like the real
  endpoint: HTTP 200, `choices[0].message.content`, `usage` with fixed
  `prompt_tokens` (100) and `completion_tokens` (10).
- The answer is fixed but valid for the requested schema (read from
  `response_format.json_schema`, as `src/llm.py` sends it):
  `{"paragraphs": [1], "label": L}` for section-route, `{"pages": [P],
  "label": L}` for page contexts (P = the first `=== PAGE n ===` sent), and
  `{"label": L}` for task B; `L = --label` (default 0).
- Failures for chosen calls: by call number (`--fail-calls`, `--garbage-calls`,
  `--html-calls`, `--error-calls`; retries count as calls) or by a marker in the
  request, which does not depend on case order: `STUB_FAIL` (HTTP 500 every
  attempt), `STUB_FAIL_ONCE` (500, then the normal answer on the retry),
  `STUB_GARBAGE` (not JSON), `STUB_EMPTY` (content null), `STUB_HTML` (an
  HTML body), `STUB_400`, `STUB_NO_USAGE`, `STUB_LABEL_1`/`STUB_LABEL_2`,
  `STUB_BAD_PAGES` (cites numbers that were not sent).
- `GET /_stub/calls` lists every call (model, whether an `Authorization`
  header and which `User-Agent` came; the key's value is never stored).

Run: `python3 scripts/stub_llm.py --port 8099`, then
`BASE_URL=http://127.0.0.1:8099/v1 API_KEY=stub python3 -m src.cli --input ... --output ...`.

## Part 2: contract checks

`tests/test_contract.py` runs the real CLI (`src.cli.main`) in a subprocess
against the fake model over HTTP, on the committed example booklet
(`examples/booklets/2020_09_27_fr.pdf`), its first 8 pages as a small booklet,
a broken and an empty PDF, and missing paths. After **every** run it checks:
exit code 0; exactly one valid response per input id (label/label_name agree,
evidence items with non-empty text ≤ 5,000 characters, a 1-based int page for
task A, `null` or no evidence for task B, metrics non-negative ints); the
fake key never appears in stderr or the output; **no write outside the output
and temporary folders** (a Python audit hook records every file write: open
for writing, mkdir, rename, replace, remove, ...); the data folder's hash is
unchanged.

| Test | Result |
|---|---|
| Mixed file of task A and B (section-route and default) | pass |
| All nine language pairs; unknown (`en`, `rm`, `xx`) and missing languages | pass (languages change nothing) |
| Malformed lines (`{not json`, blank, `[1,2,3]`, `null`, a string, a number, no id) | pass: skipped and logged, every other case answered |
| Missing or wrong fields (no source, both sources, no vote, no path, `booklet: null`, booklet as a string, `claim: null`, claim as a string, claim text a number, no reference text, no claim text, only an id) | pass: fallback answer (neutral, no evidence) |
| Missing booklet, broken PDF, empty PDF, a folder as path, a path outside `/data` | pass: fallback, no model call |
| Empty and blank claims | pass |
| Blank input file | pass: empty output file, exit 0 |
| Failed and garbage answers: HTTP 500 (both attempts), garbage text, null content, HTML body, HTTP 400, no usage, cited pages not sent, endpoint unreachable, no `BASE_URL` at all | pass: every case a valid response; a 5xx is retried exactly once; tokens of an unreadable answer still counted |
| One failed attempt, then success | pass: answer used, retry pause included in the time |
| Failures chosen by call number | pass |
| Environment: `BASE_URL`/`API_KEY`/`MODEL`, default model `swiss-ai/Apertus-v1.5-8B`, `BASE_URL` without `/v1`, `LLM_*` fallback, `User-Agent` | pass |
| **Order independence**: three orders (given, reversed, seeded shuffle), first with an empty booklet cache, the others reusing it; default settings and section-route | pass: identical labels and evidence per id |
| Order independence, default settings on the full booklet (`CONTRACT_SLOW=1`) | pass (run here, 2026-10-09) |
| The audit hook sees the pipeline's own writes (output file, booklet cache) | pass |
| Unwritable cache folder | pass (the case is answered) |
| Default context uses the embedding when the e5 files are there | pass (skipped without them) |
| **Duplicate ids get exactly one response** | **expected failure**: the CLI answers both lines; the starter's scorer then marks the id invalid (P1) |
| **A UTF-8 byte order mark** | **expected failure**: the first line is unreadable, its case gets no response (P2) |
| **One byte that is not UTF-8** | **expected failure**: the whole run stops with a traceback, no output file at all (P3) |

Without the e5 model files (fresh checkout, CI test job) task A answers come
from the whole booklet (`--context-a full`) and the embedding test is
skipped; the pipeline's own fallback (context selection failed → neutral) is
covered either way. Runtime here: about 2.5 minutes (each run starts a Python
process and, for task A, loads the e5 model).

Run: `python3 -m pytest tests/test_contract.py` (add `CONTRACT_SLOW=1` for the
full-booklet order test).

## Part 3: evidence on saved runs (session 6's two arms)

`scripts/check_evidence.py` on `docs/runs/2026-10-08_rashad_section-route-vs-embed_devA300/{section-route,embed-e5-small}`
with the dev booklets. Run folder: `docs/runs/2026-10-09_rashad_evidence-check_devA300/`.
The starter's normalisation, re-implemented, equals the starter's own
`normalize()` on 3,677 texts (all items and all dev pages); the starter's
`evaluate.py` re-scored both arms to their recorded numbers.

| Rule | section-route (284 items) | embed-e5-small (769 items) |
|---|---|---|
| Text verbatim on the page it names (after normalisation) | **12 violations** (+1 verbatim only without hyphen joining) | pass (2 verbatim only without hyphen joining) |
| Page an int ≥ 1 that exists | pass | pass |
| At most 5,000 characters | pass | pass |
| At most five items | pass (at most 3) | pass |
| Neutral answers have no evidence | pass | pass |
| (warning) label 0/2 without evidence | 0 | 0 |

**The 12 violations** (case ids, all `-A`): v1.1-row-2, 5, 168, 412, 419, 455,
1276, 1291, 1302, 1304, 1324, 1335. Cause, checked for each: `src/booklet.py`
drops lines from inside a paragraph (a lone `-`, the PDF's trace of a
hyphenated word, or once a page number "3"), so the evidence text is the
page's lines with one to three lines left out. With those lines removed the
item is a substring of its page; its partial ratio against the page is 99.0
to 99.9. It does not lower the evidence score (the scorer matches against the
gold passage at ≥ 90), but it is not strictly verbatim (P8).
Also noted: 6 section-route responses repeat one text twice (identical
clauses in law texts, two paragraphs both cited; P7).

## Part 4: clean-machine build

`.github/workflows/clean-machine.yml` (repository root; the push was
accepted, so no manual step is needed). On `ubuntu-latest` it:

1. builds the image with **`make build`** (`docker build --platform linux/amd64`), and checks the architecture is amd64;
2. creates an **`--internal` Docker network** (no internet) and starts the fake model there, as a container of the same image (`--read-only`);
3. checks that `https://pypi.org`, `https://huggingface.co` and `https://1.1.1.1` are **not** reachable from that network;
4. runs the image with the Makefile's own **`make run`** target on `examples/cases.jsonl`: `--read-only` root filesystem, `--tmpfs /tmp`, `/data/cases.jsonl` and `/data/booklets` mounted **read-only**, `BASE_URL` = the fake model, a dummy `API_KEY`;
5. fails if the run fails, if any input id is missing (or duplicated, or unknown), if `scripts/check_format.py` fails, or if the fake model was not called once per case or a case fell back;
6. writes image size, build time and run time to the job summary.

A second job runs `pytest tests` on Python 3.12 without the e5 files.

**Reproduced here** (same commands; Docker 29.8.2, 4 CPUs, 15 GB): network
has no internet (name resolution fails), `make run` exit 0, 2 of 2 ids
answered, format check "errors: none", fake model called twice with
`User-Agent: hackapertus-voting-nli/0.1`. Image: 681 MB compressed content
(this Docker uses the containerd image store, whose "2.0 GB" disk usage
counts the compressed and the unpacked layers); build **86 s** (with the
sandbox's proxy certificate bind-mounted for `pip install` only, see the
decisions file); run on the examples **21.6 s** cold (2 cases; the task A
case embeds the whole booklet first). onnxruntime logs "Failed to persist telemetry
device ID" because the root filesystem is read-only; harmless (it uses an
in-memory id), and it shows the read-only root works.

**On GitHub** (runs of `clean-machine` on this branch):

| Run | Commit | Image job | Tests job |
|---|---|---|---|
| 1 (PR opened) | `20edd79` | **pass**: build 22 s, run 19 s, image 1,293,593,836 bytes (1.29 GB), 2 calls for 2 cases, format "errors: none", internet unreachable from the network | **fail**: `results.md` not regenerated at that commit, and one order test assumed the e5 files (the hunting law's long part needs e5; without it the case gets the fallback). Fixed in `8eec72c` and `db6770f` (reproduced in a worktree without `models/` first, then 110 passed) |
| 2 (dispatched) | `5574e20` | **pass**: build 19 s, run 19 s | **pass** (24 s) |
| FINAL_RUN_ROW |

The pushes from this session did not start new `pull_request` runs (only
opening the PR did), so runs after the first were started by hand
(`workflow_dispatch`). Pushes by the team start them as usual.

## Part 5: unseen booklets

Run folder: `docs/runs/2026-10-09_rashad_unseen-booklets_15/` (details,
JSON per vote). Booklets from the Federal Chancellery (downloads were not
blocked): the 2026-09-27 booklet (after the dataset) and the four most recent
older dates (every 2020–2026 date in the archive is already in the dataset),
in German, French and Italian; `scripts/fetch_unseen_booklets.py` re-downloads
them; they are not committed.

| Date | Votes | de | fr | it | What failed |
|---|---|---|---|---|---|
| 2026-09-27 | 2 | complete | complete | complete | nothing |
| 2019-05-19 | 2 | no parts | no parts | no parts | no start page for the council's arguments |
| 2019-02-10 | 1 | no parts | no parts | no parts | same |
| 2018-11-25 | 3 | no parts | no parts | no parts | same |
| 2018-09-23 | 3 | no parts | no parts | no parts | same; vote 1 also: no arguments heading on page 14 |

Every contents entry and every vote was found (33 votes); where a vote's
title could be read from its detail page, `find_vote()` picked that vote. A
vote that fails a check gets no parts, so its cases fall back to
embed-e5-small: the parser never guessed. Why 2018–2019 fail and what would
fix it: P9.

## Part 6: router stress test

Run folder: `docs/runs/2026-10-09_rashad_router-stress_300/` (every claim
with intended part, route and outcome). 100 openings per language written for
the test (none from the dataset).

| | right | wrong part | fall back (part intended) | correct fallback |
|---|---|---|---|---|
| de | 40 | 2 | 54 | 4 |
| fr | 47 | 1 | 48 | 4 |
| it | 44 | 1 | 51 | 4 |
| **all** | **131** | **4** | **153** | **12** |

- **Routed to the wrong part (flagged):** "Der Bundesrat ist laut Zusammenfassung der Ansicht …" → council (intended summary); "Das Komitee kritisiert gemäss der Zusammenfassung …" → committee; "Le Conseil fédéral, selon le résumé, …" → council; "Il Consiglio federale, secondo il riassunto, …" → council.
- Lower case, upper case, leading spaces, non-breaking space, line break: routed as before. **All 38 openings with a leading quote («, „, ", ') and all 8 with a leading dash fall back.**
- Main fallback kinds: "Nach Ansicht / Aus Sicht des Bundesrates", "Gemäß dem Bundesrat" (ß), "Bundesrat und Parlament …" without article, "Conseil fédéral et Parlement", "Consiglio federale e Parlamento", "Pour le / De l'avis du Conseil fédéral", "A parere / Ad avviso del Consiglio federale", plural committees, "Die Initiantinnen und Initianten", "Les initiants", "I promotori", "Wird die Initiative angenommen", "Si l'initiative est acceptée", "Se l'iniziativa viene accettata", "En cas d'acceptation", "In caso di approvazione", "Laut Initiativtext", "Selon le texte de l'initiative", "In Kürze", "En bref", "In breve".
- No opening without a source was routed. Patterns: P10.

## Part 7: speed and memory

Run folder: `docs/runs/2026-10-09_rashad_speed-memory_dev44/` (per-booklet
JSON for host and container, `summary.json`, the driver log, notes). No model
was called: per-case times come from the real CLI against the fake model,
which answers in milliseconds, so they are the local steps only. Host: 4
CPUs, 15 GB. Container: the image with `--cpus 2 --memory 4g --memory-swap
4g`, read-only root. MB = MiB.

**Per booklet** (44 dev booklets, one fresh process each, empty cache; min / median / max):

| Step | Host | Container (2 CPUs, 4 GB) |
|---|---|---|
| import of the pipeline | 0.18 / 0.19 / 0.28 s | 0.41 / 0.44 / 0.50 s |
| PDF to page texts (pypdf) | 0.44 / 1.15 / 2.87 s | 0.53 / 1.36 / 3.48 s |
| booklet parse (`src/booklet.py`) | 0.005 / 0.02 / 0.06 s | 0.005 / 0.02 / 0.07 s |
| the claim router alone (300 dev claims) | 16 µs per claim | not measured |
| e5 model load | 1.67 / 1.87 / 7.70 s* | 1.75 / 1.85 / 2.07 s |
| embedding the whole booklet (first `embed-e5-small` case) | 1.6 / 7.3 / 21.3 s | 3.0 / 13.8 / 44.8 s |
| a later `embed-e5-small` case (claim only) | 0.008 / 0.013 / 0.079 s | 0.009 / 0.025 / 0.064 s |
| slowest `section-route` case per booklet (router, parse, vote match, e5 for long parts) | 0.005 / 0.04 / 25.4 s | 0.005 / 0.05 / 34.0 s |
| peak memory | 1,197 / 1,640 / 2,868 MB | 1,190 / 1,616 / 2,871 MB |

\* the 10 loads above 2.4 s were all among the first 12 booklets, while other work ran on the machine; from the 13th booklet on, at most 2.4 s.

**End to end, all 300 dev task A cases in one process:**

| Context | Host total | Host median / p95 / max | Container total | Container median / p95 / max | Peak memory host / container |
|---|---|---|---|---|---|
| `embed-e5-small` (default) | 412 s | 0.02 / 10.4 / 21.6 s | 786 s | 0.06 / 19.3 / 44.4 s | 1,853 / 1,800 MB |
| `section-route` | 170 s | 0.03 / 2.3 / 14.9 s | 287 s | 0.04 / 3.7 / 31.9 s | 2,809 / 2,763 MB |

**Slowest cases** (container):

- `embed-e5-small`: v1.1-row-31-A 44.4 s, 367 40.1 s, 94 38.3 s, 5 37.9 s, 154 35.0 s. Each is the first case on a large booklet (2021-06-13 has 144 pages) and pays for embedding the whole booklet; the booklet's later cases take milliseconds.
- `section-route`: v1.1-row-500-A 31.9 s, 782 31.6 s, 580 27.2 s, 904 26.9 s, all law parts of 385 to 636 paragraphs (79,000 to 136,000 characters) that are embedded to keep the 8 most similar; then v1.1-row-1383-A 18.4 s, the one fallback case (whole booklet). The same four law cases were the slowest in E5 (16 to 20 s, host). Length-sorted batches would embed them 2.2 to 2.9 times faster with identical vectors (P6).

**Peak memory:** the e5 model takes about 1.2 GiB once loaded; the peak, 2,871 MiB or 2.8 GiB (2021-06-13 fr), comes when it embeds a whole booklet or a long part in batches of 32. `section-route`'s end-to-end peak (2,763 MiB in the container) is higher than the default's (1,800 MiB) because of the long law parts. Both stay under the 4 GiB limit (at most 70 %); a 3 GiB limit would leave almost no headroom with today's batch size.

**Cold start** (container, `docker run` to exit, one case, twice each):

| Case | Wall time | Case time (`inference_time_ms`) | Peak memory |
|---|---|---|---|
| one task B case | 0.96 s, 0.96 s | 7 ms, 5 ms | 31 MB |
| one task A case, `embed-e5-small` (88-page booklet) | 27.1 s, 26.3 s | 25.9 s, 25.0 s | 1,459 MB |
| one task A case, `section-route` (short part, no model loaded) | 3.0 s, 2.9 s | 2.1 s, 2.0 s | 37 MB |

On GitHub the cold run of the two examples took 19 s (the task A case 17.5 s).

## Part 8: hygiene

**Secrets.** `scripts/scan_secrets.py` searched every line added in every
commit reachable from all refs (all remote branches fetched, including the
parallel session's), and every file name ever added: known token formats
(`sk-`, `hf_`, `ghp_`/`github_pat_`, `xox?-`, `AKIA`, `AIza`, private key
blocks, JWTs), values of 16+ characters assigned to any `*KEY*`, `*TOKEN*`,
`*SECRET*`, `*PASSWORD*`, `*AUTH*` name, `Bearer` values, and `.env`,
`*.pem`, `*.key`, `id_rsa` files. **Result: 0 findings** (SCAN_COUNTS). Only
`.env.example` was ever committed, with placeholders. The scanner was checked
on made-up keys of each kind (all found) and placeholders (none flagged).
GitHub's own secret scanning was not run: its tool needs the content pasted
into the call. For a second opinion, the repository's Security tab shows
GitHub's secret-scanning alerts (free for public repositories).

**Licences** (from the package metadata inside the image; files in
`docs/runs/2026-10-09_rashad_hygiene/`):

| In the image | Licence |
|---|---|
| pypdf 6.17.0 | BSD-3-Clause |
| rapidfuzz 3.14.6 | MIT |
| requests 2.32.3 | Apache-2.0 |
| onnxruntime 1.30.0 | MIT |
| tokenizers 0.23.2 | Apache-2.0 |
| numpy 2.5.3 | BSD-3-Clause (bundled parts: 0BSD, MIT, Zlib, CC0-1.0) |
| transitive: urllib3, charset-normalizer, idna, certifi | MIT, MIT, BSD-3-Clause, **MPL-2.0** |
| transitive (onnxruntime): flatbuffers, protobuf, packaging | Apache-2.0, BSD-3-Clause, Apache-2.0 OR BSD-2-Clause |
| transitive (tokenizers → huggingface_hub): huggingface_hub, hf-xet, httpx, httpcore, h11, anyio, click, fsspec, filelock, PyYAML, tqdm, typing_extensions | Apache-2.0, Apache-2.0, BSD-3-Clause, BSD-3-Clause, MIT, MIT, BSD-3-Clause, BSD-3-Clause, MIT, MIT, **MPL-2.0 AND MIT**, PSF-2.0 |
| pip 25.0.1 (base image) | MIT |
| Python 3.12 (base image `python:3.12-slim`) | PSF-2.0 |
| 87 Debian packages of the base image (`debian_packages.txt`) | GPL-2+, GPL-3+, LGPL, BSD, Expat/MIT, public domain and others, from their copyright files, as in any Debian image; 5 without a machine-readable line |
| **Embedding model** `intfloat/multilingual-e5-small` @ `614241f6` | **MIT** (model card metadata at that commit) |

| Development only (`requirements-dev.txt`, not in the image) | Licence |
|---|---|
| pandas 3.0.5, scikit-learn 1.9.1, pytest 9.1.1, pyarrow 25.0.1 | BSD-3-Clause, BSD-3-Clause, MIT, Apache-2.0 |
| transitive: scipy, joblib, threadpoolctl, narwhals, cloudpickle, python-dateutil, six, iniconfig, pluggy, Pygments | BSD-3-Clause, BSD-3-Clause, BSD-3-Clause, MIT, BSD-3-Clause, Apache-2.0 or BSD-3-Clause, MIT, MIT, MIT, BSD-2-Clause |

The Python packages and the model are permissive; MPL-2.0 (certifi, part of tqdm) is
file-level copyleft and only matters if those files are modified. The Debian
base packages come with their sources from Debian, as for any image built on
`python:3.12-slim` (not legal advice). The dataset is MIT. The starter has
no licence and is used outside the repository only. Note: `LICENSE` is
Apache-2.0 while the template asks for CC-BY-4.0 (TODO for the team).
`huggingface_hub` is in the image only as a dependency of `tokenizers`; the
pipeline never calls it (no download at run time; the CI run had no internet).

**Sizes.** `data/`: **9.6 MB** (9,934,439 bytes; limit 100 MB; largest file
`raw/v1.1.parquet`, 2.7 MB). Image: **1.29 GB uncompressed** (1,293,593,836
bytes, `docker image inspect` on the GitHub runner), **681 MB compressed
content** (here). Of the layers, 487 MB is the e5 model and another 487 MB its
second copy made by `RUN chmod -R a+rX /app/models` (P11); 210 MB the Python
packages; the rest the `python:3.12-slim` base.

## Part 9: documents

- `technical_report.md`: filled following its template (summary,
  architecture, how context is prepared and supplied, use of Apertus, data,
  evaluation, limitations incl. "not political advice", reproducibility, next
  steps). Every number names its run folder in `docs/runs`; gaps are **TODO**:
  team name and members' full names, demo, the final task A default, the
  dataset README's label definitions, the booklets' terms of use, the
  evaluation's model, server and hardware, the submission commit and tag, and
  the licence mismatch.
- `docs/remaining_errors.md` (generated by `scripts/remaining_errors.py`):
  the 14 wrong `section-route` answers of E5, each with the claim, the
  numbered paragraphs sent (rebuilt with the run's code; page and length of
  every paragraph checked against the run's record), the answer, the evidence
  and the gold passage. Gold 0 → answered 1: 4; 0 → 2: 1; 2 → 1: 7; 2 → 0:
  2. **In all 14 a sent paragraph lies inside the gold passage**: reading
  errors, not selection misses. Two (one detail, one law case) were cut to
  the 8 most similar paragraphs.

## Proposals

For files this branch must not change. Each is measured or reproduced where
possible; none is applied.

| # | File | Proposal | Evidence |
|---|---|---|---|
| P1 | `src/cli.py` | Answer each id once (the first line with that id), log the rest | The CLI writes two responses for a duplicated id; the starter's scorer then counts that id invalid. Test `test_duplicate_ids_get_exactly_one_response` (expected failure) |
| P2 | `src/cli.py` | Read the input with `encoding="utf-8-sig"` | A byte order mark makes line 1 unreadable: its case gets no response. Test `test_byte_order_mark_does_not_lose_the_first_case` |
| P3 | `src/cli.py` | Decode line by line with `errors="replace"` (or read bytes and decode per line) | One invalid byte anywhere: `UnicodeDecodeError`, exit 1, **no output file**. Test `test_invalid_utf8_line_does_not_stop_the_run` |
| P4 | `src/cli.py` | Write each response as soon as it is ready (append, flush) | Now all responses are written at the end: a kill (time limit, out of memory) or an uncaught `BaseException` loses every answer |
| P5 | `src/cli.py` | Optional: for a line that is not valid JSON but shows `"id": "..."`, answer that id with the fallback | Truncated lines and trailing garbage now get no response (the contract promises valid JSON, so low priority) |
| P6 | `src/contexts/embed_e5_small.py` (`E5Embedder.embed`) | Sort texts by length before batching, then restore the order | The four slowest routed cases (long law parts, 27 to 32 s in the container) embed 2.2 to 2.9 times faster on the host with identical vectors (largest difference 0.0) and the same 8 paragraphs (`scripts/embed_batching_check.py`). Re-parsing the booklet per case is not worth caching: at most 0.07 s |
| P7 | `src/contexts/section_route.py` | In `evidence_items`, skip a paragraph whose text equals one already taken | 6 E5 responses repeat a text (identical law clauses) |
| P8 | `src/booklet.py` | Keep evidence contiguous: return the page's text from a paragraph's first to its last line (lone `-` lines and page numbers included) as the evidence, while the prompt keeps the cleaned text | 12 E5 items are not one contiguous piece of their page (Part 3) |
| P9 | `src/booklet.py` | Council titles with "und Parlament / et du Parlement / e del Parlamento" optional; "deliberazioni in Parlamento" as a debate name; accept a debate heading as the arguments' start heading | Measured in memory (`scripts/unseen_booklets.py --proposal`): 14 of 15 unseen booklets complete (was 3), 32 of 33 votes; the 44 dev booklets parse identically. Patterns in that script |
| P10 | `src/claim_router.py` | Strip leading quotes, dashes and spaces; add the patterns in `scripts/router_stress.py` (`PROPOSED`): more prepositions and verbs, "Bundesrat und Parlament" without article, ß, plural committees, initiants/promotori, the initiative or law as subject of "if accepted", "In Kürze / En bref / In breve", other names for the text; a summary named within the first words overrides the subject | Measured in memory: 273 of 300 right (was 131), 0 wrong (was 4); 0 of 877 dataset claims outside test change route. Written after seeing the stress claims, so not an unseen measure |
| P11 | `Dockerfile` (allowed, but the submission image; left for its own change) | `RUN mkdir -p /app/models/multilingual-e5-small`, then `ADD --chmod=644 ${E5_URL}/model.onnx ${E5_URL}/tokenizer.json /app/models/multilingual-e5-small/`, instead of `ADD` + `RUN chmod -R a+rX /app/models` (which copies the 487 MB model a second time) | Built and run here: compressed image 681 → **395 MB**, uncompressed about 1.29 → 0.81 GB, same predictions on the examples. **Without the `mkdir`**, `ADD --chmod=644` also gives the folders it creates mode 644, so a non-root user cannot enter them: the model fails to load and every task A case silently gets the neutral fallback (seen here with `--user 1001:1001`). With the `mkdir` first: folders 755, files 644, non-root run identical to today's image (checked). `make run` runs as the caller's user, so CI (non-root) would catch the broken form |
| P12 | `Dockerfile` | Optional: `ENV HOME=/tmp` so onnxruntime's telemetry id write goes to the writable `/tmp` instead of failing | Log line "Failed to persist telemetry device ID" under `--read-only`; harmless |

## What could not be verified

- **The evaluation's hardware** and whether it imposes CPU or memory limits: Part 7 measured 2 CPUs / 4 GB as asked; the real limits are unknown.
- **The official scorer** (pages, extra items): only the starter's `evaluate.py` exists.
- **Booklets older than 2018** and the booklets' terms of use were not checked.
- **Model behaviour**: nothing here says how Apertus answers; every label in Parts 2 and 4 comes from the fake model.

## How to rerun

From `track_2a/` (booklets: `python3 scripts/fetch_dev_booklets.py`,
`python3 scripts/fetch_unseen_booklets.py`; e5 files as in the Dockerfile in
`models/multilingual-e5-small/`):

```bash
python3 -m pytest tests                                   # unit + contract tests (CONTRACT_SLOW=1 for the slow one)
python3 scripts/check_evidence.py --run docs/runs/2026-10-08_rashad_section-route-vs-embed_devA300/section-route \
    --run docs/runs/2026-10-08_rashad_section-route-vs-embed_devA300/embed-e5-small
python3 -I scripts/unseen_booklets.py --booklets output/booklets_unseen --out /tmp/unseen [--proposal]
python3 scripts/router_stress.py --out /tmp/router [--proposal]
EMBED_MODEL_DIR=models/multilingual-e5-small python3 scripts/speed_memory.py --booklets output/booklets_dev \
    --cases data/dev/cases.jsonl --out /tmp/speed.json
python3 scripts/scan_secrets.py
EMBED_MODEL_DIR=models/multilingual-e5-small python3 scripts/remaining_errors.py \
    --run docs/runs/2026-10-08_rashad_section-route-vs-embed_devA300/section-route --out docs/remaining_errors.md
```
