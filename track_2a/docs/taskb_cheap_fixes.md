# Task B cheap fixes

2026-10-09, 01:40 to 03:00 UTC, branch `claude/eager-cannon-08bx1h-taskb`.
Run by Rashad, with Claude Code. The test split was never used. No default
was changed. Decisions: `docs/decisions/2026-10-09-0140_rashad_taskb-cheap-fixes.md`
and `docs/decisions/2026-10-09-0200_rashad_taskb-cheap-fixes-continued.md`.
Run: `docs/runs/2026-10-09_rashad_taskb-4arm_devB300/` (notes, `analysis.json`).

## 1. In short

- **B fails its rule, so the comparisons stopped there.** Strict JSON with max_tokens 10 (arm B) scored
  Macro-F1 0.853, against 0.867 for v3-topic-first as it is (arm A): a fall of 0.013,
  more than the 0.01 allowed. B had no unreadable answer and saved 0.9 tokens per case,
  so only the Macro-F1 condition failed. As instructed, C and D were not judged. They
  were measured in the same run and are in the table.
- **Recommendation: freeze arm A, v3-topic-first as it is (plain output, max_tokens
  32).** It is already the default; nothing was changed.
- **The run's main finding is about the endpoint, not the prompts.** Every request
  named `swiss-ai/apertus-v1.5-8b`, and Public AI sent each one to one of two backends:
  - `api.blablador.fz-juelich.de`: 737 answers;
  - `api.featherless.ai`: 463 answers. The response headers give this deployment's
    model name as `swiss-ai/Apertus-8B-Instruct-2509`, the September 2025 release.

  The backend changes the answers. On the 250 cases where A and B met the same
  backend, their Macro-F1 is identical (0.877) and only 3 labels differ. B's loss
  comes from the 50 cases where they met different backends.
- **Public AI's gateway answers repeated requests from a cache for about 10 minutes.**
  As a result, the noise floor of the confirmation stage (0.0033, two runs with
  identical answers) very likely measured this cache, not the model.
- **The endpoint changed during the run:** the canary after it differs from the canary
  before it in 2 of 30 answers. Both of those answers are cache copies of the run's own
  answers.
- 0 failed calls, 0 HTTP 429 answers and 0 retries at no more than 60 requests per
  minute.
- With strict JSON and no format line in the prompt (v5-min, v5-ballot), the model pads
  its JSON with spaces and line breaks. 27 and 22 answers were cut off at 10 tokens and
  became unreadable.

## 2. The method: compare only inside one run

Rashad's rule since 02:00 UTC: **versions are compared only inside one
interleaved run, and scores from different runs are never compared.** In one
run every case goes to all versions back to back, so whatever the endpoint
does at that moment affects all of them alike. The acceptance rule's
thresholds stay, applied between arms of the same run.

This run also shows its limit: arms of the same case can still be answered
by different backends (section 3).

## 3. Endpoint identity

**What is logged.** `src/llm.py` now records, for every call (in the raw
answers, field `endpoint`):

- the body's `model` and `system_fingerprint`;
- the response headers that name a model, backend or provider: LiteLLM's
  `x-litellm-model-api-base`, `-model-id`, `-model-name`, `-model-group`,
  `x-litellm-version`, `x-litellm-attempted-fallbacks` and `-retries`, plus
  `llm_provider-server`, `server` and `cf-placement`, and any other header naming a
  model, backend, upstream, region, deployment or fingerprint;
- Cloudflare's data centre (the code at the end of `CF-RAY`);
- since this run, `gateway_cache_hit` (section 4).

**What is never logged:**

- headers about our account: key, spend, cost, budget, authorisation, cookies, tokens;
- values that change with every call: request and call ids, dates, durations, the ray
  id itself.

Each call also records its requests (`attempts`) and HTTP 429 answers (`http_429`).

**What differed between calls.** Of the 1,260 calls (1,200 in the run, 60 in
the two canary checks), these fields took more than one value:

| Field | Backend 1 | Backend 2 |
|---|---|---|
| `x-litellm-model-api-base` | `https://api.blablador.fz-juelich.de/v1` | `https://api.featherless.ai/v1` |
| `x-litellm-model-name` | `openai/alias-apertus` | `openai/swiss-ai/Apertus-8B-Instruct-2509` |
| `x-litellm-model-id` | `8c4216b4…` | `d89d2d4e…` |
| `system_fingerprint` | `vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840` | `fp1-nst-nes` |
| `llm_provider-server` | `openresty/1.27.1.2` | `cloudflare` |
| Answers written in the run (A / B / C / D) | 737 (189 / 185 / 183 / 180) | 463 (111 / 115 / 117 / 120) |

- **Constant in every call:** `model` (`swiss-ai/apertus-v1.5-8b`),
  `x-litellm-model-group`, `x-litellm-version` 1.98.0, no LiteLLM fallbacks or retries,
  and data centre IAD. `cf-placement` was `remote-MXP` in 1,248 calls and `local-IAD`
  in 12.
- **The routing moved over time.** Cases 51 to 100 and 251 to 300 went to backend 1
  (all but 1 of their 400 calls), and cases 126 to 225 mostly to backend 2 (319 of 400).
  The four arms of one case met the same backend in only 191 of 300 cases.
- **The backend changes the answers.** Arms A and B send the same prompt (B adds the
  schema):

| A and B answered by | Cases | Labels differ | Macro-F1 A | Macro-F1 B | A right → B wrong | A wrong → B right |
|---|---|---|---|---|---|---|
| the same backend | 250 | 3 | 0.877 | 0.877 | 1 | 1 |
| different backends | 50 | 19 | 0.781 | 0.685 | 11 | 7 |

- **Do not compare the backends by their scores.** By the response, the canary's 30
  answers at 02:11 all came from backend 1. Backend 2 then answered 4 of the 30 canary
  cases differently: rows 549, 640, 767 and 869, which are gold neutral, became
  contradiction. Macro-F1 per backend is not a fair comparison, because the routing
  followed time and the case order, so each backend got a different mix of cases (for
  arm A, backend 2's cases are 71 of 111 neutral).
- **Is backend 2 Apertus v1.5?** We cannot tell. The request says v1.5 and so does the
  body's `model`, but the deployment's own name is the v1 model of September 2025.
  Only Apertus v1.5 may be used in the solution (the organisers' rule); at evaluation
  the organisers' endpoint is called, not Public AI. Our development numbers, however,
  mix the two backends.

## 4. The gateway cache

Public AI's gateway (LiteLLM) answers a request that is identical to one sent
in the last ~10 minutes from its cache:

- **In this run:** 12 of arm A's calls were canary cases sent 2 to 10 minutes after the
  canary check (whose request is the same as arm A's). They came back in about 0.6 s,
  without the upstream `llm_provider-*` headers, with exactly the canary's answer. For
  one of them (row 49) the routing headers named backend 2 while the fingerprint was
  backend 1's. No arm A call sent more than about 10 minutes after the canary was a
  copy. Arms B, C and D send other requests and had none.
- **A probe after the run** (one new request sent twice) confirmed it. The second answer
  had the same response id, an `x-litellm-cache-key` header, no `llm_provider-*`
  headers, and took 604 ms against 890 ms. `src/llm.py` now marks such answers
  `gateway_cache_hit` (only the fact; the header's value is not kept).

**What this means for the confirmation stage (correction).** Run 2 of the
confirmation stage started the moment run 1 ended. It repeated each of
run 1's requests 3 to 8 minutes later, gave the same answer text in all 299
cases it answered, and ran 2.5 times faster (median 0.6 s, the speed of a
cache copy here). **So its "noise floor" of 0.0033 very likely measured the
gateway's cache, not the model's run-to-run variation.** It cannot be checked
now, because that run did not record the endpoint identity. The noise floor
of fresh answers is unknown.

## 5. The canary

The canary keeps its 30 cases and its request (v3-topic-first, max_tokens
32, no response_format). It no longer blocks runs. It now runs immediately
before and after each task B run and appends to `docs/canary_log.md` (time,
the 30 answers, endpoint identity, which earlier results it matches) and to
`docs/canary_results.jsonl`. The earlier results (01:25, 01:50, 01:51) were
added to the log from their records.

| Check | Matches an earlier result? | Identity |
|---|---|---|
| 02:11:06, before the run | No. Closest: 01:50 and 01:51 (29 of 30 identical; row 1014 now adds a reasoning paragraph), the 01:25 baseline (26 of 30) | all 30 from backend 1 |
| 02:39:43, after the run | No. Closest: 01:50 and 01:51 (29 of 30), 02:11 (28 of 30) | 19 from backend 1; 11 copies from the cache, written by the run's arm A |

**The two checks differ (rows 1014 and 1128), so the run is marked "endpoint
changed during run" in `docs/results.md`.** The mark comes from the
`canary` block of each arm's `run.json`. Both differing answers are cache
copies of the run's arm A answers: row 1014's was written by backend 2 and row
1128's by backend 1, and both lack the reasoning paragraph of 02:11. The
labels are the same.

**Because of the cache, a canary right after a run that repeats its request
partly returns that run's own answers.** The canary therefore detects
changes less well than intended (section 9).

## 6. The run

- All 300 dev task B cases, four arms, 02:11:42 to 02:39:43 UTC, code `75171d7`:
  - A: v3-topic-first as it is (plain output, max_tokens 32);
  - B: v3-topic-first with `--schema-b` and `--max-tokens-b 10`;
  - C: v5-min with schema and 10;
  - D: v5-ballot with schema and 10.
- **v5-ballot** is v5-min plus one sentence after "Use only the reference text.": "The
  first line of the reference text names the ballot it is about." It adds 14 tokens
  (counted beforehand with the Apertus v1 tokenizer; measured in the run: D's input is
  14.0 tokens per case above C's), 100 fixed tokens in all.
- **Order.** `scripts/paired_run.py` now takes two or more arms. With four arms the
  order follows a balanced Latin square (0 1 3 2, 1 2 0 3, 2 3 1 0, 3 0 2 1, in turn),
  so in every four cases each arm is in each position once and directly after each
  other arm once. A and B send the same prompt; under a plain rotation B would come
  right after A in three of four cases and profit from A's cached prompt. With two arms
  the order alternates as before.
- **Pace.** At least 1 s between the starts of two requests (`--min-interval 1.0`, at
  most 60 per minute), outside the timed case.
- **HTTP 429s: 0. Retries: 0.** Failed calls: 0.

## 7. The four arms

| | A: v3 plain, max_tokens 32 | B: v3 + schema, 10 | C: v5-min + schema, 10 | D: v5-ballot + schema, 10 |
|---|---|---|---|---|
| **Macro-F1** | **0.867** | 0.853 | 0.786 | 0.840 |
| F1 entailment / neutral / contradiction | 0.917 / 0.812 / 0.870 | 0.910 / 0.784 / 0.866 | 0.911 / 0.696 / 0.752 | 0.892 / 0.784 / 0.844 |
| Confusion, gold E (pred E / N / C) | 88 / 12 / 2 | 86 / 15 / 1 | 87 / 15 / 0 | 83 / 19 / 0 |
| Confusion, gold N | 0 / 78 / 21 | 0 / 76 / 23 | 0 / 72 / 27 | 0 / 87 / 12 |
| Confusion, gold C | 2 / 3 / 94 | 1 / 4 / 94 | 2 / 21 / 76 | 1 / 17 / 81 |
| Input tokens, mean / p95 | 1,994.2 / 4,463 | 1,994.2 / 4,463 | 1,877.2 / 4,346 | 1,891.2 / 4,360 |
| Output tokens, mean | 7.87 | 7.00 | 9.79 | 9.73 |
| Tokens per case (input + output) | 2,002.1 | 2,001.2 | 1,887.0 | 1,900.9 |
| Time, mean / p95 | 1,355 / 2,346 ms | 1,247 / 2,191 ms | 1,480 / 2,485 ms | 1,463 / 2,329 ms |
| Failed calls | 0 | 0 | 0 | 0 |
| Unreadable answers | 0 | 0 | 27 | 22 |

- **Schema and input tokens.** The schema adds no input tokens: A and B have exactly the
  same `usage.prompt_tokens`.
- **Answer forms.**
  - B: all 300 answers are exactly `{"label": n}` (7 tokens).
  - A: 289 answers are exactly `{"label": n}`; 11 add text after the JSON (10 of them up
    to the 32-token cap).
  - C and D get no format line, and the schema leaves the model free to add spaces and
    line breaks (`{\n  "label": 1\n \n`). They used all 10 tokens in 257 and 250
    answers, and 27 and 22 answers were cut off before the closing brace. The label is
    visible in 27 of 27 and 21 of 22 of these, but the parser (unchanged) needs a
    complete JSON object, so they got the fallback label neutral.
- **Times.** Arm A's times include 12 cache copies of about 0.6 s. Between backends,
  backend 2 was slower for A and B (mean 1.7 s and 1.5 s against 1.2 s and 1.1 s).

## 8. The three comparisons

| Comparison | Rule | Macro-F1 | F1 E / N / C | Tokens per case | Unreadable | Right → wrong | Wrong → right | Verdict |
|---|---|---|---|---|---|---|---|---|
| B against A | keep if Macro-F1 falls by ≤ 0.01, 0 unreadable, adds < 30 tokens | −0.013 | −0.007 / −0.029 / −0.004 | −0.9 | 0 | 12 | 8 | **fails** (Macro-F1) |
| C against B | keep if Macro-F1 falls by ≤ 0.01 and no label's F1 by > 0.03 | −0.067 | +0.001 / −0.088 / −0.114 | −114.2 | 27 | 48 | 27 | not judged (stopped after B) |
| D against C | keep only if Macro-F1 rises by ≥ 0.01 | +0.054 | −0.019 / +0.088 / +0.091 | +13.9 | 22 | 20 | 36 | not judged (stopped after B) |

**B fails, and as instructed nothing replaces it.** B's loss is not the
schema's doing; the backend breakdown in section 3 shows this. On the 250
cases where A and B met the same backend, B equals A. The rule was applied
as written, to all 300 cases.

The C and D rows are measurements, not verdicts. The same breakdown on the cases
where both arms met the same backend:

- C against B: 238 cases, Macro-F1 0.884 against 0.835, 47 labels differ.
- D against C: 237 cases, 0.856 against 0.890, 12 labels differ.

## 9. Recommendation

**Freeze arm A: v3-topic-first as it is, plain output, max_tokens 32.** It
is the current default, so nothing changes.

- B failed its rule, and the comparisons stop there.
- A had no unreadable answer and no failed call.
- B would have saved only 0.9 tokens per case.

Proposals for Rashad, none of them done:

1. **Find out what the endpoint serves before the next comparison.** Ask Public AI why
   `swiss-ai/apertus-v1.5-8b` is routed to a deployment named
   `Apertus-8B-Instruct-2509`, or develop on the guide's endpoint (CSCS). Until then,
   every task B and task A number from Public AI mixes two backends, in proportions
   that change within minutes.
2. **Judge comparisons on the cases where all arms met the same backend**, now that
   every call records its fingerprint, or repeat a run when only one backend answers.
   This is a change to the method, so it is Rashad's decision.
3. **Keep the canary from reading the cache:** for example, ask LiteLLM not to use its
   cache for the canary's requests (LiteLLM documents a per-request `no-cache` option;
   not tried). That changes the canary's request.
4. **If v5-min or v5-ballot are tried again,** they need a format line or more than 10
   tokens. That would be a new version with a new name.

## 10. What stays unverified

- What weights backend 2 serves, and whether "Apertus-8B-Instruct-2509" in its
  deployment name means v1.
- Whether earlier runs (sessions 2 to 7, the confirmation stage) were also split across
  backends. They recorded no identity. The two "endpoint changes" (2026-10-08 13:25 and
  2026-10-09 between 01:36 and 01:50 UTC) may have been routing changes; this is not
  verified.
- The run-to-run noise of fresh answers on one backend. The 0.0033 of the confirmation
  stage was very likely the cache (section 4).
- The cache's exact lifetime (copies up to about 9.5 minutes after the first request
  were seen, none after about 10.3 minutes), and whether the organisers' proxy caches.
- The organisers' rate limits. At 60 requests per minute Public AI sent no 429.

## 11. Earlier in this stage (01:40 to 01:52 UTC)

- **Setup:**
  - old-endpoint marks in `docs/results.md` (task B rows from before 2026-10-08
    13:25 UTC);
  - the canary (`docs/canary_taskb.json`, `scripts/canary_taskb.py`);
  - HTTP 429 retries in `src/llm.py` (up to two: Retry-After if sent, else 2 s and 4 s,
    never more than 10 s; tested with fakes);
  - the acceptance rule;
  - the task B settings `--schema-b` and `--max-tokens-b`.
- **The canary stopped the first run at 01:50.** 3 of 30 answers differed from the
  01:25 baseline (rows 767 and 869 had become neutral; row 1128 added a reasoning
  paragraph), and a repeat at 01:51 gave the same. Under the method of that time no run
  started.
- **The vote-name run was skipped on its merits.** `vote` always names the passage's own
  ballot, and the passage already opens with that title (all 886 dataset rows outside
  the test split).
- **v5-min was written then.** Fixed instructions: 77 system tokens plus 9 for the user
  message's labels = 86 (v3's are 203). It keeps v3's three rules: another ballot or
  subject is neutral; contradiction only when both cannot be true; missing information
  is neutral, never contradiction.
