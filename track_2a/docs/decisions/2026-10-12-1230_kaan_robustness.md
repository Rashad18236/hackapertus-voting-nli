## Robustness experiments: cross-language tournament, negation, decomposition, retrievers (2026-10-12, from 12:30 UTC)

Kaan's experiments, with Claude Code. Branch `kaan/robustness-experiments` from `main` at `42b2a3c`. Report:
`docs/robustness_experiments.md`. Everything new is off by default; no default was changed. The test split
was never used.

- **Four ideas, each a switch, compared in one interleaved run against today's defaults.** Kaan's request: try the cross-language tournament, the negation check, claim decomposition and other retrievers, each on its own, with results per variant.
- **Model calls run alongside session 10, one request every 2 s (`--min-interval 2`).** Kaan's choice ("run now, slowly"); half of session 10's rate, so the two together stay at the rate session 10 used alone.
- **Translation is local (facebook/m2m100_418M, MIT, CTranslate2 int8), not Apertus.** Kaan's choice: no tokens for translation; one model covers all six directions (opus-mt has no French-to-Italian model). Its time counts as local time, which the organisers score (T).
- **The MT packages go into `requirements-experiments.txt`, not `requirements.txt`.** The Docker image stays the submission until a variant is adopted.
- **A strategy keeps today's request as its building block (`judge`), and records every sub-answer.** Then the strategies differ only in what they ask, and other combination rules can be computed offline from the saved answers at no token cost (`scripts/strategy_analysis.py`).
- **Strategies apply to routed task A cases and to task B; the fallback path (about 1 in 300 dev cases) stays a single call.** The fallback answers pages, not paragraphs; covering it would double the code for almost no cases.
- **Tournament: both sides agree → that label, else one tie-break call with today's request.** Kaan: "only if both sides align we conclude"; the tie-break keeps a disagreement from turning into a guess.
- **Negation: a neutral answer is replaced by the label the negation implies; otherwise today's answer stays.** Most task A errors are supported or refuted claims called neutral; a rule that also overrides entailment and contradiction would risk the cases that are right today. Alternatives are scored offline.
- **Decomposition only for claims of at least 180 characters (about a quarter of dev claims), each part judged by its own call.** Shorter claims are mostly one fact; one call per part reuses the tested prompt instead of a new multi-claim prompt.
- **Retrievers: BM25 (pure Python), BM25 on the claim translated into the booklet's language, reciprocal-rank fusion with e5, and that fusion on the vote's pages; all on embed-e5-small's chunks with its prompt.** Only the ranking differs, so the comparison is about retrieval alone.
- **Retrieval is measured first offline (gold passage among the sent chunks, `scripts/retrieval_check.py`, no tokens), then with the model with routing off.** Routing already sends the gold passage in 200 of 200 routed dev cases, so retrievers matter for the cases routing cannot handle; running them alone shows what such a case would get.
- **The booklet's language for bm25-mt is detected from its text (`src/langid.py`).** The context variants' interface does not pass the request's language fields; detection also copes with a wrong field.
- **No new variant becomes a default here.** Adoption needs a val confirmation and the token/time trade-off under the official formula; that is a separate decision.
- **At the merge with `main` (sessions 10 and 11), `main`'s `src/cli.py` was taken unchanged and the `--strategy-a/-b` hooks were dropped.** `main` turned `src/cli.py` into a prepare-then-run pipeline; the strategies were measured and not adopted, so porting their hooks would add code for nothing. The runs' code is commit `95588ed`; `src/strategies.py` and its tests stay. The retriever variants need no hook (context registry) and still run with `--context-a`.
