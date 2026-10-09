# Session 8: hardening without a model

2026-10-09, 13:48 to about 16:00 UTC, branch `rashad/hardening`, run unattended
by Claude Code for Rashad. Decisions:
`docs/decisions/2026-10-09-1348_rashad_session-8.md`.

- **No model calls.** `.env` was never read and no key was used. Wherever
  the pipeline needs an endpoint, the fake model (`scripts/stub_llm.py`)
  answered.
- **Nothing off-limits was touched:** the test split, the splits, the
  scorer, `src/nli.py`, `src/llm.py`, the Settings defaults in `src/cli.py`,
  the Dockerfile, the Makefile and `data/`.
- **Starting point:** `main` at `25ed5fa`, which contains PR #12
  (`docs/checks_no_model.md`). PR #12 was merged a minute after the session
  started, and the branch was then recreated from the freshly pulled `main`.

## 1. In short

**All five changes were applied; none was reverted.** Each is one commit,
and after each one both gates held and the full test suite passed:

- G1 (requests): every request and every path was the same as in the
  reference.
- G2 (answers): every label was the same. Evidence was the same everywhere
  except in change E, where it differs exactly in the 19 responses that
  repeated a text, as that change allows.

| Change | Commit | Result | G1 requests and paths | G2 labels and evidence | Extra gate | Numbers |
|---|---|---|---|---|---|---|
| Step 0: reference | `c5e638b` | done | 1,180 requests hashed | replay of E5 and E6 reproduces them exactly | – | dev 0.953 / 0.905, val 0.956 / 0.946 (starter's scorer, as recorded) |
| A. CLI input and output (P1–P4) | `72cf03a` | **applied** | pass (0 differences) | pass (0 differences) | the 3 expected failures now pass; new kill test passes | 121 tests pass, 0 expected failures |
| B. Length-sorted embedding batches (P6), batch size 16 | `bdd816c` | **applied** | pass | pass | vectors of 45 booklets identical (largest difference 0.0); same 8 chunks in 880 of 880 cases | container, 300 dev cases: total 364.9 → 228.5 s, p95 4.15 → 3.21 s, slowest case 51.2 → 17.6 s, peak 3,287 → 2,254 MiB |
| C. Router patterns (P10) | `7343fee` | **applied** | pass | pass | `router_stress.py`: 273 right, 0 wrong part (was 131 and 4) | 126 tests pass |
| D. Parser patterns (P9) | `6df4a86` | **applied** | pass | pass | full parse of 45 dev and val booklets (132 votes) identical; 14 of 15 unseen booklets complete (was 3) | 129 tests pass |
| E. Repeated evidence (P7) | `4a60c24` | **applied** | pass | labels pass; evidence differs in exactly the 19 responses that repeated a text (6 dev, 13 val) | evidence score not lower | dev 0.9055 → 0.9055, val 0.9461 → 0.9461; 131 tests pass |

## 2. Step 0: the reference

**What the snapshot records.** `scripts/prompt_snapshot.py run` runs the real
CLI (`src.cli.main()`, default settings) on two sets, each in its own
process against its own fake model:

- dev: all 600 cases of `data/dev/cases.jsonl` (300 task A, 300 task B);
- val: all 580 task A cases of `data/val/cases.jsonl`.

It matches each model call to its case, in order, and checks the match: the
request must contain the case's claim (1,180 of 1,180). For each case it
records:

- the SHA-256 of the whole request body (model, messages, max_tokens,
  temperature, response_format, as canonical JSON);
- for task A, the path taken: dev 299 routed and 1 fallback, val 577 routed
  and 3 fallbacks.

**The replay.** The fake model now has a replay mode (`--replay TABLE`). The
table gives, for each request hash, the answer E5 (dev) or E6 (val sample)
saved for that case:

- 600 requests are answered from the table;
- the rest get the fake model's fixed answer: the 300 dev task B cases and
  the 280 val cases outside E6's sample.

**The replay on the unchanged code reproduces E5 and E6 exactly:**

- labels and evidence: 0 differences in 300 dev and 300 val cases;
- starter's scorer, dev: Macro-F1 0.9533, evidence 0.9055 (182 of 201);
- starter's scorer, val sample: Macro-F1 0.9559, evidence 0.9461 (193 of
  204).

These are the recorded numbers, so there was no difference to explain. The
reference is
`docs/runs/2026-10-09_rashad_prompt-snapshot_devAB-valA/`. Every gate run's
comparison is stored in its `gates/` folder, along with the extra gates'
outputs.

## 3. The changes

**A. `src/cli.py` input and output.**

- *Input:* the input is read as bytes, and a UTF-8 byte order mark is
  dropped. Lines are split at `\n`, `\r\n` or `\r`, and each line is decoded
  with `errors="replace"`.
- *Duplicates:* a duplicated id is answered from its first line; later lines
  are logged and skipped.
- *Output:* each response and raw answer is written as one line and flushed
  at once, and a blank input still gives an empty output file.
- *Tests:*
  - The three expected failures of `tests/test_contract.py` are normal
    tests.
  - The invalid-byte test now also expects an answer for the bad line, which
    is still JSON with an id: a stricter check.
  - The duplicate test checks that the first line is the one answered.
  - New: `StoppedRun` sends SIGKILL after five answers and checks that they
    are complete, valid lines in input order.
  - New: `ReadLines`. Its case with a U+2028 character inside a string shows
    that the old `str.splitlines()` could cut a line in two.

**B. Faster embedding.**

- *The change:* `E5Embedder.embed` sorts the texts by length, embeds them in
  batches and restores their order.
- *Extra gate (`scripts/embed_equivalence.py`):* the vectors and selections
  of the old code were saved first, then compared with the new code. The
  vectors of every chunk of the 45 dev and val booklets and the 880 query
  vectors are bit-identical, and embed-e5-small selects the same 8 chunks in
  all 880 cases.
- *Container measurement (`scripts/container_speed.sh`):* 2 CPUs, 4 GB,
  read-only root, no internet, the fake model in a second container, the
  working tree's `src/` mounted over the image's.

| Section-route, 300 dev task A cases | Total | p95 | Slowest case | Peak memory |
|---|---|---|---|---|
| before | 364.9 s | 4.15 s | 51.2 s (row 9) | 3,287 MiB |
| sorted, batch 32 | 248.4 s | 3.63 s | 20.9 s (row 1383) | 2,764 MiB |
| **sorted, batch 16 (kept)** | **228.5 s** | **3.21 s** | **17.6 s** (row 1383) | **2,254 MiB** |

- *Batch size 16:* kept by its rule. Selections are identical (same extra
  gate, G1 and G2), peak memory is lower, and the total time is 8 % better
  where up to 10 % worse was allowed.
- *The long law parts* (rows 500, 782, 580 and 904) take about half as long.
  Row 1383 is the one dev case that falls back and embeds a whole booklet.

**C. Router patterns.**

- *The change:* the 19 patterns of `scripts/router_stress.py` and the
  stripping of leading quotes, dashes and spaces moved into
  `src/claim_router.py`. They are unchanged and checked first; the original
  patterns follow.
- *Checked beforehand:* the new router routes all 1,177 claims (300 stress
  claims, 877 dataset rows outside test) exactly as the proposal did.
- *The stress script:* it now tests the router as it is, with no
  `--proposal` option: 273 right, 0 wrong part, 15 fallbacks, 12 correct
  fallbacks.
- *Tests:*
  - New: 33 openings, one or more per new pattern group, starting with the
    four that went to the wrong part. Also quotes and dashes, and openings
    without a source.
  - Changed: `test_only_the_opening_counts` expected "Die Initiative sagt
    laut der Zusammenfassung etwas." to get no route. The requested rule
    routes it to the summary, so the test now pins the new boundary instead:
    a summary named after a comma, or more than 40 characters in, still
    gives no route.

**D. Parser patterns.**

- *The change:* the three proposed changes moved into `src/booklet.py`:
  - council titles where "und Parlament / et du Parlement / e del
    Parlamento" is optional;
  - "deliberazioni in/al Parlamento" as a debate name;
  - the debate heading accepted as the start heading of the arguments.
- *Extra gate (`scripts/parse_equivalence.py`):* the full parse output was
  saved before the change and compared after it: every vote's title, entry,
  ok, problems, part pages, boxes, and every paragraph's page and text.
  It is identical for all 45 booklets (132 votes).
- *Unseen booklets:* the 15 were downloaded again. They give 14 of 15
  complete, 32 of 33 votes ok, which is the checks session's proposal output
  exactly, apart from times. `scripts/unseen_booklets.py` no longer has
  `--proposal`.
- *Tests:* one per new pattern, applied as the parser applies it.

**E. Repeated evidence.**

- *The change:* `section_route.evidence_items` skips a cited paragraph whose
  text equals one already taken.
- *Effect:* evidence changed in 19 responses: dev rows 288, 1022, 1205,
  1283, 1342 and 1407; val rows 61, 65, 312, 366, 383, 1134, 1158, 1168,
  1175, 1299, 1411, 1417 and 1425. Each is the reference's evidence with
  the repeats removed: no other change, nothing added, no repeat left
  (`gates/E_evidence_changes.json`).
- *Evidence score:* unchanged (dev 0.9055, val 0.9461).

## 4. Records

- **Run folders:**
  - `2026-10-09_rashad_prompt-snapshot_devAB-valA`: the reference, the
    replay table, and the gates of every change.
  - `2026-10-09_rashad_container-speed_devA300`: change B's measurements.
- **New scripts:** `prompt_snapshot.py`, `embed_equivalence.py`,
  `parse_equivalence.py`, `container_speed.sh`.
- **New tests:** `test_stub_replay.py`, `test_embed_order.py`, plus new
  classes in `test_cli.py`, `test_contract.py`, `test_claim_router.py`,
  `test_booklet.py` and `test_section_route.py`.
- **Documents updated:**
  - `technical_report.md`: architecture, evaluation, limitations and next
    steps, wherever these changes close what the report listed as missing.
  - `docs/checks_no_model.md`: a note on which proposals were applied.
  - CLAUDE.md: "Current stage".
- **Test suite:** 131 tests pass, 1 skipped, here with the e5 files. The
  clean-machine workflow result is in the pull request.

## 5. What was not verified

- **Model behaviour.** No model was called, so the gates show that the
  requests are byte-identical and that the same answers give the same
  output. They say nothing about new requests. Openings that newly route
  (change C) or booklets that newly parse (change D) send requests Apertus
  has never answered. No dev or val case is among them; the test split and
  the private set may contain some.
- **The router and parser patterns were written after seeing their test
  data** (the stress openings and the 2018–2019 booklets). Their 273 of 300
  and 14 of 15 are not unseen measures.
- **The container measurement** used the image built by the checks session,
  with this session's `src/` mounted over it, rather than a rebuild
  (the Dockerfile is unchanged). Its "before" run (364.9 s, 3,287 MiB) is
  slower and higher than the checks session's 287 s and 2,763 MiB on the same
  image, for a reason not found here; only the three runs of this session
  compare with each other. One run each, so the times carry run-to-run noise
  (not measured).
- **The evaluation hardware** and its limits are unknown; 2 CPUs and 4 GB
  are an assumption.
- **The kill test** sends SIGKILL to a local process. Whether the
  organisers' runner stops a container in another way (a time limit, the
  out-of-memory killer) was not tested; the flush after each line covers
  both.
- **Inputs that are not UTF-8 at all** (for example a whole file in
  Latin-1) are answered line by line with replacement characters; such input
  breaks the contract and was not tested beyond one bad line.
