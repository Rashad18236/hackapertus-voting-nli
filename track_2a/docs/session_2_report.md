# Session 2 report: task B improvement, then task A baseline

2026-10-08, 05:59 to about 08:59 UTC, branch `session-2`. All numbers come from
actual runs on the dev split, scored with the starter's official
`evaluate.py`; the test split was never run. Model: `swiss-ai/apertus-v1.5-8b`
on Public AI. Every run is a row in `docs/results.md`, and every decision is in
`docs/decisions.md` (section "Session 2").

## 1. Headline

- **Task B: Macro-F1 0.947 on dev** with prompt `v3-topic-first` (was 0.541),
  above the 0.75 minimum. The only change was the decision rule: first ask
  whether the reference deals with the claim's subject at all; missing
  information is never a contradiction.
- **Task A: Macro-F1 0.589 on all 300 dev cases** with the first
  full-document baseline `A-v3-fulldoc` (minimum 0.60), evidence score
  0.209 (42 of 201). This is the reference row for every later context-selection
  experiment: 39,706 input tokens, 11,501 ms mean and 30,334 ms p95
  per case.
- **Task A is held back by answer format, not understanding.** 110 of 300
  answers (37 %) were not valid JSON (mostly prose cut off at the 64-token answer
  limit, some stray `<|inner_prefix|>` tokens) and fell back to neutral; on the 187
  parsed answers Macro-F1 is 0.765. Reading explicit prose labels ("the label is
  0"), re-parsed offline, lifts the full result to **0.608**. Neither a larger
  answer budget nor JSON mode fixed it in this session, and the endpoint's output
  drifted and failed often during those tests.
- Session input tokens: about 18.3 million (limit 40 million), counted from
  the runs' self-reported usage, plus estimates for a few diagnostic calls.

## 2. Every run

| Run | Task | Prompt | Cases | Macro-F1 | F1 entailment | F1 neutral | F1 contradiction | Evidence score | Mean input tokens | Mean time (ms) | p95 time (ms) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `contract-v2-dev` | B | v2-label-only (previous best, before session 2) | 300 | 0.541 | 0.922 | 0.057 | 0.642 | not scored (task B) | 1963 | 1944 | 2815 |
| `s2-A-v3-topic-first` | B | v3-topic-first (Run A) | 300 | 0.947 | 0.955 | 0.934 | 0.951 | not scored (task B) | 1968 | 2748 | 2878 |
| `s2-C-v4-topic-first-examples` | B | v4-topic-first-examples (Run C) | 300 | 0.933 | 0.985 | 0.907 | 0.906 | not scored (task B) | 2162 | 1765 | 2986 |
| `s2-A60-A-v3-fulldoc` | A | A-v3-fulldoc, 60-case sample | 60 | 0.767 | 0.872 | 0.744 | 0.684 | 0.375 (15/40) | 41124 | 9617 | 23331 |
| `s2-A240-A-v3-fulldoc` | A | A-v3-fulldoc, the other 240 dev cases (part of the 300) | 240 | 0.538 | 0.611 | 0.615 | 0.390 | 0.168 (27/161) | 39352 | 11972 | 37108 |
| `s2-A300-A-v3-fulldoc` | A | A-v3-fulldoc, all 300 dev cases (reference row) | 300 | 0.589 | 0.671 | 0.635 | 0.462 | 0.209 (42/201) | 39706 | 11501 | 30334 |
| `s2-A300-A-v3-fulldoc-reparsed` | A | same answers re-parsed offline with the prose-label parser | 300 | 0.608 | 0.686 | 0.647 | 0.491 | 0.209 (42/201) | 39706 | 11501 | 30334 |
| `s2-A60-A-v3-fulldoc-max256` | A | A-v3-fulldoc, max_tokens 256, 60-case sample (endpoint drift) | 60 | 0.398 | 0.276 | 0.467 | 0.452 | 0.150 (6/40) | 41124 | 11660 | 31684 |
| `s2-A60-A-v3-fulldoc-max256-reparsed` | A | same answers re-parsed offline | 60 | 0.553 | 0.595 | 0.520 | 0.545 | 0.150 (6/40) | 41124 | 11660 | 31684 |
| `s2-A60-A-v3-fulldoc-jsonmode_attempt1` | A | A-v3-fulldoc + JSON mode, 60-case sample, attempt 1 (27 % failed calls) | 60 | 0.378 | 0.357 | 0.483 | 0.294 | 0.125 (5/40) | 21041 | 15766 | 58256 |
| `s2-A60-A-v3-fulldoc-jsonmode_attempt2_stopped` | A | A-v3-fulldoc + JSON mode, rerun: stopped after 7 failed calls in 24 cases | stopped, not scored | | | | | | | | |

Notes:
- Task B runs use the 300 task B dev cases; task A runs use the 60-case
  sample (20 per label) and then all 300 task A dev cases (60-case run +
  240 remaining cases, same image and settings, scored together).
- Mean time includes failed calls. Run A had 5 calls that failed during an
  endpoint outage (about 61 s each); without them its mean is 1,753 ms.
- Run B (adding the vote name to task B) was not run: in all 300 task B
  dev cases `vote` is the first line of the reference, so it adds no
  information (`docs/neutral_analysis.md`).

## 3. What we kept and why

- **Task B prompt `v3-topic-first` is now the default.** On the 295 cases that
  both Runs A and C answered, it scores 0.963 against 0.933 for v4 (same rule plus three
  examples). It is also 168 input tokens per case cheaper, and time is similar. The examples
  helped entailment but pushed more neutral cases to contradiction.
- **One retry for HTTP 5xx and timeouts**, with the tokens of every attempt
  counted. Public AI returned 504s in bursts this session (10 failed calls in
  a row around 06:01 to 06:12 UTC); a single retry would have saved Run A's 5
  failures. It was added after Runs A and C, so their rows ran without it.
- **Task A `A-v3-fulldoc`**: the whole booklet with `=== PAGE n ===` markers,
  the vote name and the claim, and the answer `{"pages": [...], "label": n}`.
  Asking for the pages *before* the label was necessary: with the label first
  (A-v1, A-v2), the model always returned `"pages": []`. Evidence is the
  cited pages' text (split at 5,000 characters, at most five items).
- **The prose-label parser** (an explicit "label is N" in prose counts if all
  such statements agree). It reads the model's stated answer and never guesses;
  on the saved answers of the full task A run it recovers 13 answers (0.589 →
  0.608).
- **Not kept:** `max_tokens` 256 for task A (0.398 on the sample, but
  confounded by endpoint drift, so not attributable) and JSON mode (invented
  schemas without `label`, and the runs failed the 10 % rule). Both remain as
  development flags (`--max-tokens-a`, `--json-mode-a`), off by default.
- **Local PDF parsing with pypdf** (BSD licence), cached under `/tmp` by the
  file's SHA-256, so results do not depend on case order.

## 4. Wrong predictions, in plain words

### Task B (Run A, `v3-topic-first`; 11 wrong apart from failed calls)

| id | gold → predicted | why it went wrong |
|---|---|---|
| v1.1-row-946-B | neutral → contradiction | The reference is about the OECD minimum tax, the claim about a carbon tax. Both are "taxes", so the model treated the claim as on-topic and false. |
| v1.1-row-500-B | neutral → contradiction | AHV 21 / VAT reference against a claim about the direct federal tax rate. Same near-topic problem. |
| v1.1-row-854-B | neutral → contradiction | 13th AHV pension against "the Federal Council recommends retirement at 63 for men". Same pension domain, different ballot. |
| v1.1-row-1468-B | contradiction → entailment | Long Covid-19 law text; the claim says the costs are covered *entirely* for small firms. The model missed that the detail does not match. |
| v1.1-row-1167-B | contradiction → entailment | Glacier initiative counter-proposal: the claim gets the conditional procedure (what is put to the vote if the counter-proposal passes) the wrong way round, and the model accepted it. |

The topic-first rule removed the "unrelated claim, so contradiction" error
for clearly unrelated claims. What remains are **near-topic neutrals** (another
ballot in the same domain) and **fine details in long legal texts**.

### Task A (60-case sample, `A-v3-fulldoc`; 14 wrong, 6 of them parse failures)

| id | gold → predicted | why it went wrong |
|---|---|---|
| v1.1-row-608-A | neutral → contradiction | A claim about VAT on food against the factory-farming ballot. The old "unrelated, so contradiction" error comes back when the model reads a whole booklet. |
| v1.1-row-797-A | neutral → contradiction | A defence-budget claim against the CO2 law. Same pattern. |
| v1.1-row-1267-A | contradiction → entailment | The referendum committee calls the anti-terror law *ineffective*; the model attributed the government's view to the committee. Who says what gets lost in a long booklet with both sides' arguments. |
| v1.1-row-160-A | entailment → neutral | A clearly supported CO2-law claim. The model cited page 65 of a multi-ballot booklet and missed the right section; a retrieval failure inside a long document. |
| v1.1-row-263-A | entailment → contradiction | The booklet does say the premium-relief initiative costs billions a year. The model saw a conflict that is not there, probably over the amount or who pays. |

Other task A observations:
- **6 of 60 answers were unparseable** and got the label-1 fallback:
  - page lists longer than the 64-token limit, despite "at most five";
  - two stray `<|inner_prefix|>` outputs;
  - two answers in prose.
- **When the model cites the detailed section, the evidence matches well**
  (partial ratio 92 to 98). It often cites the summary pages at the front,
  which do not match the gold passage (around 50).

## 5. What could not be run or verified in this sandbox

- **Endpoint outage.** Public AI answered HTTP 504 to every call from about
  06:01 to 06:12 UTC: Run A's first attempt (5 calls, all failed) and smoke
  calls. The fallback URL `platform.publicai.co` is not an API (HTTP 405). The
  rerun after the two-minute wait recovered after 5 more failed calls.
- **Endpoint drift and failures in the second half.** Repeating two task A cases
  at 07:50 with the original settings (temperature 0) gave different answers
  than at 06:39, and the share of prose answers rose over the session (10 %,
  then 43 %, then 57 %). From 07:53, HTTP 503s persisted through the retry: the
  JSON-mode run failed 16 of 60 calls and its rerun 7 of 24, so it was stopped
  by the 10 % rule. Comparisons between task A runs made at different times are
  therefore weaker than the task B comparisons (Runs A and C, 06:10 to 06:33).
- **Booklet download.** The first `prepare_cases.py --download-booklets` run
  failed with HTTP 503 on its first PDF; the second attempt downloaded all 60.
  Not blocked, but flaky.
- **Docker in the sandbox.** The image is built with a sandbox-only step that
  adds the proxy's CA certificate, and runs need `DOCKER_RUN_FLAGS="--network
  host -e HTTPS_PROXY"`. The committed Dockerfile is unchanged; a judge's build
  was not reproduced from outside the sandbox.
- **Token counts are self-reported** (the endpoint's `usage`). The organisers'
  proxy count wins and may differ, for example for a 504 that still used
  tokens on the backend.
- **Evidence pages** are not checked by the local scorer ("not checked yet");
  our pages are 1-based PDF indexes as the contract asks, but this is not
  verified against the official run.
- **Runs A and C** ran from the working tree before the first session-2
  commit (`b11cf1e`). The code is the same except for the retry, which was added
  afterwards. Diagnostic task A calls (7) and a 2-case stopped run are counted
  in the token total partly by estimate.
- **The "evidence ceiling"** (how many gold cases any single page could
  match) was started but is too slow with rapidfuzz on full booklets; it was stopped. A faster version on the 60-case sample (8 most word-overlapping pages per booklet, then the exact official match) found a matching page for at least 35 of the 40 gold entailment/contradiction cases (0.875), against 15 cited. The evidence gap is page choice, not page text.

## 6. Final checks (step 9)

- All 38 unit tests pass; all 14 self-checks pass, including the agreement
  between our scorer and the official one.
- `make run` (08:26 UTC): exit 0, two responses in the official format
  (format check clean).
  - The task B example: entailment.
  - The task A example: now really sent to the model with its whole booklet
    (36k input tokens), but the answer was prose cut off at 64 tokens, so it
    got the label-1 fallback. That is the same issue as next step 1.
- No key and no `.env` are staged; the booklet PDFs used for dev runs are not
  committed. Only the task A example's booklet is, 0.9 MB.

## 7. Recommended next steps, in order

1. **Make task A answers reliably machine-readable, then rerun all 300 task A
   dev cases.** Format, not understanding, is the largest loss: 37 % fallbacks,
   and 0.765 on the parsed answers. Candidates, one per run:
   - a schema-constrained `response_format` (`json_schema` with `pages` and
     `label`), if the endpoint supports it, since plain JSON mode invented its
     own keys;
   - asking for the label first but with a short, fixed page format;
   - one cheap follow-up call that only asks for the label when the answer had none.

   Run them at a quiet time, with a same-time control, because the endpoint
   drifted during this session.
2. **The central experiment: selected context for task A.** Give the model
   only the vote's section of the booklet, found deterministically (the pages
   from the vote's title to the next ballot's title; no embeddings), and
   compare against the reference row `s2-A300-A-v3-fulldoc` (39.7k tokens,
   11.5 s). Expected gains:
   - far fewer input tokens;
   - better page choice: evidence is 0.21, while page text could match in at
     least 0.875 of cases;
   - fewer "unrelated, so contradiction" errors, which return in long contexts.
3. **Lock down the shipping configuration and the deliverables.**
   - Run the default pipeline once end to end through `make run` on all 600
     dev cases (task B v3 with retry, plus the improved task A).
   - Ask whether the CSCS development endpoint from the guide is available to
     us: Public AI had outages and drift this session.
   - Write the README statement (not political advice, traceable to the
     booklet) and the technical report, including how document context is
     prepared and supplied.
