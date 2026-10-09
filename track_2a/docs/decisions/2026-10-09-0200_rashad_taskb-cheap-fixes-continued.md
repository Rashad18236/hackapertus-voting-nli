## Task B cheap fixes, continued (2026-10-09, from 02:00 UTC)

Rashad's instructions; report: `docs/taskb_cheap_fixes.md` (section "Continued: one interleaved run"). Branch
`claude/eager-cannon-08bx1h-taskb`. The test split is never used.

**New method (from this stage on; it replaces "each run is compared with the best version kept so far" and the stored baseline of the earlier cheap-fixes decisions):**

- **Versions are compared only inside one interleaved run: every case is sent to all versions back to back, in an order that rotates from case to case. Scores from different runs are never compared.** The endpoint changed what it answers twice in 13 hours (2026-10-08 13:25 and 2026-10-09 between 01:36 and 01:50 UTC), so a stored baseline stops describing the endpoint without warning.
- **The acceptance rule's thresholds stay; they are applied between arms of the same run.** This run's three comparisons use Rashad's rules for each one (below).

Setup:

- **Every model call records the endpoint's identity in the raw answers (`endpoint`): the body's `model` and `system_fingerprint`, the response headers that name a model, backend or provider (LiteLLM's `x-litellm-model-*`, `x-litellm-version`, `x-litellm-attempted-fallbacks`/`-retries`, `llm_provider-server`, `server`, `cf-placement`, and any other header naming a model, backend, upstream, region, deployment or fingerprint), and Cloudflare's data centre from `CF-RAY`.** These are what the response says about who answered; a change among them is the first thing to look for when answers change.
- **Never recorded: headers about our account (key, spend, cost, budget, auth, cookies, tokens) and values that differ on every call (request and call ids, dates, durations, the ray id itself); URLs lose any query string.** Logging nothing secret is Rashad's rule; per-call values would make every call look different.
- **Each call also records its requests (1 plus retries) and how many were answered with HTTP 429 (`attempts`, `http_429`).** The run must report 429s and retries.
- **The canary no longer blocks runs. It keeps its 30 cases and its request (v3-topic-first, max_tokens 32, no response_format), runs immediately before and after each task B run, and appends each result to `docs/canary_log.md` (time, the 30 answers, endpoint identity, which earlier results it matches) and `docs/canary_results.jsonl`.** Under the new method a changed endpoint cannot spoil a comparison between runs, but it can still change during a run, and the log shows when it happened.
- **A task B run's `run.json` names its two canary checks (`"canary": {"before": time, "after": time}`); `scripts/build_docs.py` marks the run "endpoint changed during run" in `docs/results.md` when their answers differ.** Computed from the records, so it cannot be forgotten.
- **The canary's earlier results are in the log too, written by hand from earlier records: the 01:25 baseline (run 1's answers) and the 01:50 and 01:51 checks (their logs kept only the three differing answers, one cut at 60 characters).** So a new check can say whether the endpoint went back to an earlier behaviour.
- **One interleaved run on all 300 dev task B cases with four arms: A v3-topic-first as it is (plain output, max_tokens 32); B v3 with `--schema-b` and `--max-tokens-b 10`; C v5-min with schema and 10; D v5-ballot with schema and 10.** Rashad's design: three comparisons of one change each, all inside one run.
- **v5-ballot is v5-min plus one sentence after "Use only the reference text.": "The first line of the reference text names the ballot it is about." It adds 14 tokens (Apertus v1 tokenizer), 100 fixed tokens in all.** 17 of the 24 v3 errors on dev were claims about another ballot called a contradiction, and every task B passage starts with its own ballot's title. Placed before the label rules, so the model reads it before rule 1 ("a different ballot").
- **`scripts/paired_run.py` now takes two or more arms. With an even number of arms the order follows a balanced Latin square (Williams design: 0 1 3 2, 1 2 0 3, 2 3 1 0, 3 0 2 1), so each arm is in each position once and directly after each other arm once in every four cases; with two arms it alternates exactly as before.** Arms A and B send the same prompt: under a plain rotation B would come right after A in three of four cases and profit from A's cached prompt; the balanced order gives both the same chance.
- **Requests are paced: `--min-interval 1.0`, at least one second between the starts of two requests (at most 60 per minute), the pause outside the timed case; the canary uses the same pace.** The HTTP 429 of the confirmation stage came at about 96 requests per minute.

Comparisons (Rashad's rules, fixed before the run):

- **B against A: keep B if Macro-F1 falls by no more than 0.01, no answer is unreadable, and B adds fewer than 30 tokens per case.** If B fails, the comparisons stop there; nothing replaces B.
- **C against B: keep C if Macro-F1 falls by no more than 0.01 and no label's F1 falls by more than 0.03.**
- **D against C: keep D only if Macro-F1 rises by at least 0.01.**
- **"Tokens per case" are the mean input plus output tokens, as in the acceptance rule.**
- **No default changes in this stage; the report recommends one arm to freeze.** Rashad's instruction.
