### 2026-10-08, E4 (Part 4): embed-e5-small vs vote-section-embed-e5-small-k12 (task A, all 300 dev cases, paired, 8B thinking)

- Question: does the setting chosen by the offline grid (`2026-10-08_rashad_search-grid_devA201`: e5 chunks from the vote section, top 12; hit 0.846 against 0.741 offline) beat `embed-e5-small` once Apertus reads it? The run was due because 0.846 is more than 0.05 above 0.741.
- Both arms: json_schema answers, max_tokens 128, prompt `A-v3-excerpts`, evidence setting `cited` (the default); only the context differs. Code `663c330`. Order alternating (150 first each).
- Model: **`swiss-ai/apertus-v1.5-8b-thinking` for the whole run.** `apertus-v1.5-8b` was down on Public AI (HTTP 504 at 19:38 and 19:44 UTC; status page "Down"); on Rashad's instruction the run started on the thinking model at 19:47 instead of probing for the full 30 minutes. One model name for the whole run.
- Command (from `track_2a/`, on the host, nothing else running): `LLM_NAME=swiss-ai/apertus-v1.5-8b-thinking EMBED_MODEL_DIR=models/multilingual-e5-small python3 scripts/paired_run.py --cases output/devA/cases.jsonl --data-dir output/data_dev --out-dir docs/runs/2026-10-08_rashad_section-k12-vs-embed-thinking_devA300 --arm '{"name": "embed-e5-small", "context_a": "embed-e5-small"}' --arm '{"name": "vote-section-embed-e5-small-k12", "context_a": "vote-section-embed-e5-small-k12"}'`, 19:47 to 20:16 UTC. **0 failed calls and 0 unparseable answers in 600 calls.** Both arms start with an empty embedding cache, as a real run would.

| Paired, 300 cases | embed-e5-small (control) | vote-section-embed-e5-small-k12 |
|---|---|---|
| Macro-F1 (official) | **0.711** | 0.674 |
| F1 entailment / neutral / contradiction | 0.720 / 0.722 / 0.691 | 0.686 / 0.699 / 0.636 |
| Evidence score | 0.373 (75/201) | **0.403 (81/201)** |
| Mean input tokens | **1,868** | 2,777 |
| Median / p95 time | **1.7 s** / 11.4 s | 2.2 s / **5.8 s** |
| Same-language / cross-language Macro-F1 | 0.720 / 0.707 | 0.675 / 0.672 |

- Confusion (rows gold E/N/C): embed-e5-small E 67/8/27, N 11/70/18, C 6/17/76; vote-section-embed-e5-small-k12 E 60/8/34, N 4/65/30, C 9/14/76.
- Where one arm was right and the other wrong: embed-e5-small right 40 times, vote-section-embed-e5-small-k12 right 28 times; both right 173, both wrong 59.
- **The more context, the more contradiction answers**: the new arm calls 34 gold entailments and 30 gold-neutral claims contradiction, against 27 and 18. This matches Part 1 (`2026-10-08_rashad_e3-embed-errors_devA300`): most errors are reading errors, so finding the passage more often does not help when the model then misreads more.
- Time: the p95 difference is the one-off embedding. First case of each booklet (control, 44 cases): mean 8.6 s; first case of each booklet and vote (new arm, 122 cases): mean 3.9 s. All other cases: median 1.6 s against 1.7 s, p95 3.3 s against 3.4 s.
- **Verdict (rule set for this run): embed-e5-small stays.** The new setting would need Macro-F1 no more than 0.02 lower (it is 0.037 lower), evidence at least as good (yes, 0.403 against 0.373), and clearly lower input tokens or p95 time (p95 yes, tokens no). The first condition fails.
- The control's 0.711 on the thinking model is close to its 0.721 in E3 (8B for cases 1 to 180, thinking for 181 to 300).
