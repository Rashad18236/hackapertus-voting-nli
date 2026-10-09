### 2026-10-09, task B cheap fixes, continued: four arms interleaved on the 300 dev task B cases

- Command (from `track_2a/`, on the host, code `75171d7`): `LLM_NAME=swiss-ai/apertus-v1.5-8b python3 scripts/paired_run.py --cases output/devB/cases.jsonl --data-dir output/devB --out-dir docs/runs/2026-10-09_rashad_taskb-4arm_devB300 --min-interval 1.0 --arm '{"name": "A-v3-plain", "prompt_b": "v3-topic-first", "schema_b": false, "max_tokens_b": 32}' --arm '{"name": "B-v3-schema", "prompt_b": "v3-topic-first", "schema_b": true, "max_tokens_b": 10}' --arm '{"name": "C-v5-min", "prompt_b": "v5-min", "schema_b": true, "max_tokens_b": 10}' --arm '{"name": "D-v5-ballot", "prompt_b": "v5-ballot", "schema_b": true, "max_tokens_b": 10}'`.
- 02:11:42 to 02:39:43 UTC; 1,200 requests, at least 1 s apart. For each case the four arms ran back to back in a balanced order (0 1 3 2, 1 2 0 3, 2 3 1 0, 3 0 2 1, in turn). Canary (`docs/canary_log.md`) immediately before (02:11:06) and after (02:39:43).
- Scored with the starter's `evaluate.py`; the table, flips, backends and identities come from `scripts/interleaved_analysis.py` (`analysis.json`).
- **0 failed calls, 0 HTTP 429 answers, 0 retries** in all four arms.

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
| HTTP 429 answers / retries | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

Comparisons (Rashad's rules, fixed before the run):

| Comparison | Macro-F1 | F1 E / N / C | Tokens per case | Unreadable | Right → wrong | Wrong → right | Verdict |
|---|---|---|---|---|---|---|---|
| B against A | −0.0132 | −0.007 / −0.029 / −0.004 | −0.9 | 0 | 12 | 8 | **B fails** (falls by more than 0.01) |
| C against B | −0.0669 | +0.001 / −0.088 / −0.114 | −114.2 | 27 | 48 | 27 | not judged: the comparisons stopped when B failed |
| D against C | +0.0536 | −0.019 / +0.088 / +0.091 | +13.9 | 22 | 20 | 36 | not judged: the comparisons stopped when B failed |

**The endpoint served the run from two backends.** Every call asked for `swiss-ai/apertus-v1.5-8b`; Public AI's gateway (LiteLLM) sent each one to one of two deployments, and the responses say which:

| | Backend 1 | Backend 2 |
|---|---|---|
| `x-litellm-model-api-base` | `https://api.blablador.fz-juelich.de/v1` | `https://api.featherless.ai/v1` |
| `x-litellm-model-name` (the deployment's own model name) | `openai/alias-apertus` | `openai/swiss-ai/Apertus-8B-Instruct-2509` |
| `x-litellm-model-id` | `8c4216b4…` | `d89d2d4e…` |
| `system_fingerprint` | `vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840` | `fp1-nst-nes` |
| `llm_provider-server` | `openresty/1.27.1.2` | `cloudflare` |
| Answers in this run (by fingerprint) | 737 (A 189, B 185, C 183, D 180) | 463 (A 111, B 115, C 117, D 120) |

- The share moved over time: cases 51 to 100 and 251 to 300 went to backend 1 (all but 1 of their 400 calls), cases 126 to 225 mostly to backend 2 (319 of 400 calls). Within one case the four arms did not always meet the same backend (all four did in 191 of 300 cases).
- **The backend changes the answers.** A and B send the same prompt. Where both were answered by the same backend (250 cases), their labels differ in 3 cases and Macro-F1 is the same (0.877 against 0.877); where they met different backends (50 cases), labels differ in 19 (0.781 against 0.685). So B's −0.013 comes from the cases where A and B met different backends, not from the schema.
- The deployment name of backend 2 is the September 2025 Apertus release (`Apertus-8B-Instruct-2509`), not v1.5. What weights it serves is not visible from here.
- Everything else in the identity was constant: `model` in the body (`swiss-ai/apertus-v1.5-8b`), `x-litellm-model-group`, `x-litellm-version` (1.98.0), no LiteLLM fallbacks or retries (`x-litellm-attempted-fallbacks` and `-retries` 0), Cloudflare data centre IAD; `cf-placement` was `remote-MXP` in 1,248 calls and `local-IAD` in 12.

**The gateway caches identical requests for about 10 minutes.** 12 arm A calls (all canary cases, sent 2 to 10 minutes after the canary check) came back in about 0.6 s, without the upstream `llm_provider-*` headers, with exactly the canary's answer; for row 49 the routing headers named backend 2 while the fingerprint was backend 1's. A probe after the run (one new request sent twice) confirmed it: the second answer had the same response id, an `x-litellm-cache-key` header, no `llm_provider-*` headers, and took 604 ms against 890 ms. No arm A call sent more than about 10 minutes after the canary was cached. Arms B, C and D send other requests (schema, other prompts) and had no cache hits. Since this run, `src/llm.py` marks such answers `gateway_cache_hit`.

**The canary after the run differs from the one before in 2 of 30 answers (rows 1014 and 1128): "endpoint changed during run".** Both are cache copies of this run's arm A answers (row 1014 written by backend 2 without the reasoning paragraph the check before had; row 1128 written by backend 1, also without it); 11 of the 30 answers after the run came from the cache. Labels are the same in both checks.

- Unreadable answers in C and D: without format instructions, the schema-constrained model writes JSON with spaces and line breaks (`{\n  "label": 1\n \n`), uses all 10 tokens in 257 (C) and 250 (D) of 300 answers, and is cut before the closing brace in 27 and 22. The label is visible in 27 of 27 and 21 of 22 of them; the parser (unchanged) needs a complete JSON object, so they got the fallback label neutral.
- v5-ballot's sentence adds exactly 14.0 input tokens per case (D against C), as counted beforehand.
- Arm A: 289 answers are exactly `{"label": n}`, 11 add text after the JSON (all from backend 1); B's 300 are all exactly `{"label": n}` (7 tokens).
- Mean time by position in the case's order (1st to 4th): A 1,335 / 1,251 / 1,297 / 1,539 ms; B 1,342 / 1,145 / 1,274 / 1,228; C 1,527 / 1,497 / 1,389 / 1,509; D 1,522 / 1,420 / 1,449 / 1,461. Arm A's mean includes its 12 cache hits.
