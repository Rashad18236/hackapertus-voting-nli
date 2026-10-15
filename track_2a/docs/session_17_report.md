# Session 17: the model-name fallback on HTTP 403, then freeze

Branch `rashad/session-17` from `main` at `d1513a0` (session 16 merged in step 0), 2026-10-15 from 19:42 UTC,
unattended. Status log: `docs/session_17_status.md`; decisions, each written before the step it concerns:
`docs/decisions/2026-10-15-1942_rashad_session-17.md`. Draft PR #26, not merged, no tag.

## In short

**Without `MODEL`, the image now answers on Public AI.** It asks for the contract's default name
`swiss-ai/Apertus-v1.5-8B`. Public AI refuses that name with HTTP 403 ("key not allowed to access model"), and
until now `src/llm.py` read `BASE_URL/models` only after an HTTP 404 (or a 400 once `response_format` was dropped).
On such an endpoint every case would have got the neutral fallback, and the submission would have been invalid.
The model-name fallback now also fires on HTTP 403, and on HTTP 400 or 422 whose body names the model, before the
`response_format` fallback. It reads `BASE_URL/models` once, picks the Apertus v1.5 8B id with the unchanged
`pick_model`, and sends the request again. Nothing changes for a request the endpoint accepts.

**Verification through the published image, without `MODEL`** (`docs/runs/2026-10-15_rashad_model-fallback_examples-dev40`):

- Runs: the 2 example cases, then the first 20 dev task A and the first 20 dev task B cases.
- Each run, in its own container, was refused once with HTTP 403 and logged "model name replaced" once.
- 0 labels were written by Python.
- **The 40 dev labels equal the session 15 final dev run** (no endpoint drift seen).
- With `MODEL` set: both examples were answered, with no replacement line.

**The sealed numbers stand.** The sealed run was made with `MODEL` set to Public AI's id. The only code change since
then is this fallback, and it does not fire on a request the endpoint accepts. G1/G2 against the session 15 replay
reference are identical.

**Kaan's report rewrite.** Step 0 found that `main` had moved: Kaan's `5095048` rewrote the technical report in plain
language, with a diagram and four charts, starting from the report before session 16. The merge into
`rashad/session-16` keeps his text and carries session 16's sealed content into it; the PDF stays at 6 pages. His
placeholder **"Qualitative examples. TODO" (§6) is still in the report**. It is his open item, and someone must fill
or remove it before submitting.

## Step 0: session 16 merged

- **Conflict:** PR #25 (`rashad/session-16`, tip `7bf5e25`) had green checks but a merge conflict, because Kaan's
  commit `5095048` (15:51 UTC, pushed straight to `main`) changed `technical_report.md`, `report.css` and the PDF.
- **Resolution:** I merged `origin/main` into the branch with a merge commit (`790a465`; no rebase, no force-push).
  - `report.css`: git merged both sides' changes.
  - `technical_report.md`: Kaan's text is the base.
  - Carried over from session 16: the title, the header fields, the first paragraph's sealed sentence, §1's sealed
    table, "Who did what" (now also crediting Kaan's report rewrite, diagram and charts), the §5 sealed line, the §6
    sealed paragraph, "traceable to the booklet", the §8 digest and tag line, and the sealed run in the references.
  - Layout to stay within 6 pages, with no number, table or figure removed:
    - §1's two tables use the compact style;
    - the sealed table's labels are shorter;
    - the charts are a little narrower;
    - body text went from 10 to 9.5 pt.
- **Checks on the merge commit:**
  - pytest: 357 passed, 1 skipped;
  - `build_docs --check`: passes;
  - numbers check: 395 of 395 numbers found;
  - PDF: 6 pages.
- **Merge:** PR #25's checks were green on `790a465`; it was marked ready and merged with a merge commit as
  **`d1513a0`**. `origin/main` contains `7bf5e25`.
- **Image:** publish-image on `main` (run 109) was green. `latest` pulls without a login: digest
  `sha256:f368637b98e9369c377a185921bbba86bef2125db6bbd3335ac2da71222a3ea7`, revision `d1513a0`. That is a new build
  of the sealed run's `src/`, so it has a different digest from the sealed image `sha256:0c1a10cd…`.
- **Branch:** `rashad/session-17` was created, and `publish-image.yml` now also builds it (tag `session-17`).

## Step 1: the change

`src/llm.py` gets two new functions:
- `_model_name_refused(response)`: true for HTTP 403, or for HTTP 400 or 422 whose body contains "model", "not
  allowed", "unsupported" or "no available" (case-insensitive; `MODEL_ERROR_WORDS`).
- `_replace_model(...)`: fallback (b), now in one place. It reads `BASE_URL/models` once per run and picks the id
  with `pick_model`. If that id differs from the name sent, it logs once "The endpoint refused the model name
  (HTTP …); model name replaced by <id>, listed by the endpoint, for the rest of the run" (the key is never logged),
  keeps the id for the rest of the run, and resends.

In `chat()`:
- (b) now runs first when `_model_name_refused` holds.
- Then (a) and the old 404 case follow as before. So if `/models` cannot be read, or lists no Apertus v1.5 8B id, or
  lists the same id, behaviour is as before: a 400 or 422 to a request with `response_format` still drops it, and the
  call fails with the neutral fallback, counted.
- Limits are unchanged: one `/models` read per run, at most 3 extra requests per run.

Tests:
- `scripts/stub_llm.py` gets `model_error_message` (the refusal's text).
- `tests/test_llm_fallbacks.py`, class `ModelRefused`:
  - 403 to the default name, then 200 to the listed id: no `MODEL` set; 2 requests; `response_format` kept;
    `/models` read once; "model name replaced" logged once; the second call uses the id directly.
  - 400 "Unsupported model or no available clients": (b) before (a), so `response_format` is kept.
  - 403 with no Apertus id listed: the call fails, `/models` is read once, no resend.
  - 200 at once: no `/models` read, no log line.
  - The refusal words.
- One existing test now expects the new order: a 400 that names the model gets (b) then (a) instead of (a) then (b).
  It still uses three extra requests.
- `tests/test_contract.py` (the CLI):
  - a 403 endpoint answered through the replaced id for task A and task B, one "model name replaced" line;
  - a 403 endpoint with no Apertus id, where both cases get the neutral fallback, counted "model call failed: 2".
- pytest: **364 passed, 1 skipped** (pypdf 6.17.0).

**G1/G2** (`scripts/prompt_snapshot.py run --replay` with the session 15 reference's replay table, then `compare`
against `docs/runs/2026-10-15_rashad_prompt-snapshot-final-s15_devAB-valA`), output:

    {
     "G1_request_or_path_differs": 0,
     "G2_label_differs": 0,
     "G2_evidence_differs": 0,
     "g1_examples": [],
     "label_examples": [],
     "evidence_cases": []
    }
    G1 pass | G2 pass

The fake model accepts every model name, so the new fallback never fires there. All 1,180 dev and val requests,
their paths, labels and evidence are identical (val: 580 cases, 592 model calls, all replayed).

## Step 2: the image

publish-image on `rashad/session-17` (run 110) pushed `session-17`. I pulled it with an empty Docker configuration:
digest `sha256:fe4324697372af91247c25a7f21c5b1c2ae6298c43b08ba424e2d22729ec43ae`, revision `898776f`.
`src.llm._model_name_refused` is present in the image.

## Step 3: verification (the only model run)

The image above, pinned by digest, with the organisers' command and the real endpoint (Public AI):
- extras: only this sandbox's proxy flags, `--raw`, CPUs 0–1, `LLM_MIN_INTERVAL=1`;
- `BASE_URL` and `API_KEY` set; `MODEL` and `LLM_NAME` unset; `.env` not mounted;
- 20:01:41–20:03:14 UTC.

| Run | Cases | Exit | "model name replaced" | Labels by Python | Same label as final-s15 dev |
|---|---|---|---|---|---|
| examples | 2 | 0 | 1 | 0 | 2 of 2 |
| dev task A | 20 | 0 | 1 | 0 | 20 of 20 |
| dev task B | 20 | 0 | 1 | 0 | 20 of 20 |
| examples with `MODEL=swiss-ai/apertus-v1.5-8b` | 2 | 0 | 0 | 0 | 2 of 2 |

Details:
- **Refusals:** each container without `MODEL` was refused once with HTTP 403, then answered every case with
  `swiss-ai/apertus-v1.5-8b`, all from one backend (blablador).
- **Requests:** 21 per dev run (20 + 1 refused). The refused request counts no tokens.
- **Gateway cache:** three answers came from the cache: the two example cases repeated within the minute in the dev
  runs, and both cases of the run with `MODEL`.
- **Tokens per case:** task A 1,431 + 15.6, task B 852 + 8.2. These are 20-case means, not comparable to the
  300-case ones.
- **Format:** `scripts/check_format.py` is clean for all four files.

## Step 4: documents

- `README.md`: the note under the run command is now one sentence: "The image asks for `swiss-ai/Apertus-v1.5-8B`
  and, if the endpoint refuses that name, resolves the Apertus v1.5 8B id from `BASE_URL/models`; `MODEL` can still
  override it." The sentence saying `MODEL` must be set is gone. The command is unchanged.
- `technical_report.md`:
  - §8 gets a "Model name" line saying the same.
  - §6's sealed paragraph ends with: "The sealed run was made with MODEL set to Public AI's id; the fallback added
    afterwards (session 17) does not change any request the endpoint accepts."
  - The header's image line now says its digest is the sealed run's, because `latest` will be a newer build.
  - The first paragraph and §1 are unchanged.
  - PDF: 6 pages. Numbers check: 396 numbers, 0 MISSING.
- `docs/submission_message.md`: the `MODEL` sentence is replaced by: the image resolves the model id from
  `BASE_URL/models` if the default name is refused; `MODEL` can override it.
- `docs/organiser_questions.md`: question 5 (server and model id) is marked "Mitigated (session 17): the image
  resolves the id from /models".

## Step 5: finish

The checks are in the PR description and the status log. After this PR is merged, `latest` is rebuilt from `main`
with this change (a new digest). The PR description lists Rashad's steps: the `latest` digest, the `submission` tag,
package visibility, the form, the keys.
