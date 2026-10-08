## Merge of session 3 and the `embedding` branch (2026-10-08, from 15:35 UTC)

Both lines started from session 2 and both wrote a `src/context.py`, so the
branch was merged by hand (a merge commit keeps both histories).

- **Model rule, as set by the team: only Apertus v1.5 is called as the language model, every remote call goes through `BASE_URL`; local parsing, OCR and embedding models are allowed if they are open-weight, baked into the image (no run-time downloads), run on CPU and are described in the report; Apertus makes the entailment decision.** Our copy of the contract states the Apertus, `BASE_URL`, local-embedding, no-GPU and baked-weights parts; open weights, the report and "Apertus decides" are the team's own additions, all stricter. e5-small meets every point: MIT, open weights, CPU via onnxruntime, it only picks passages.
- **One `src/context.py` with three modes (`full`, `vote-section`, `embed-e5-small`) and one entry point, `context.select(pages, vote, claim, mode)`, which returns the prompt text and the pages it comes from.** The CLI needs one call for every mode; each mode's code is unchanged from its branch.
- **The mode name is `full` (session 3), not `fulldoc` (embedding branch).** Same behaviour and prompt (`A-v3-fulldoc`); one name avoids confusion. Older raw answers keep the name they were run with.
- **Every context mode uses the json_schema answer (max_tokens 128), including `embed-e5-small`.** It removed unparseable answers by construction in E1; the embedding run used a prompt-only JSON answer with 64 tokens.
- **The prompt per mode: `A-v3-fulldoc` for `full` and `vote-section`, `A-v3-excerpts` for `embed-e5-small`.** Unchanged from both branches, so their earlier runs stay comparable.
- **Evidence comes only from pages whose text was sent; for `embed-e5-small` that is the full text of the pages the selected chunks come from.** Same rule as `vote-section`: the model can only have checked what it saw. In the embedding branch a cited page outside the excerpts also counted; this changes evidence only when the model cites a page it was not shown.
- **The default stays `vote-section` until a paired run on dev beats it.** The embedding's 0.767 is promising but was not paired, ran about six hours after its reference, and had no schema.
- **`make compare` now defaults to all three modes; numbers for `docs/results.md` come from `scripts/paired_run.py`.** `make compare` runs the modes one after the other in Docker (a check that each works in the image); paired runs control for drift.

### Checks after the merge

- **Unit tests: 54 pass (45 from session 3, plus the embedding branch's tests and a test that every context mode sends the answer schema); all 14 self-checks pass.**
- **The image builds with the model inside (2 GB); the model files' SHA-256 equal the pinned download, and e5 runs in the container with `--network none`.** This shows nothing is fetched at run time.
- **`make run` on the two example cases, exit 0 and format check clean in both modes.** `vote-section`: same answer as at the end of session 3 (entailment, pages 4, 58 to 61, 15,579 input tokens). `embed-e5-small`: entailment, pages 60, 62, 63, 64 (no page from another ballot), 1,934 input tokens, but 35.9 s for the task A case.
- **`scripts/retrieval_check.py` on the merged code (commit `9081b8b`) reproduces the embedding branch's offline numbers exactly: hit@8 0.741, evidence ceiling 0.612 (all pages 0.856), 5,386 of 128,537 characters sent on average.** The merge did not change what the embedding selects. The check took 12 minutes on 4 CPU cores for the 201 cases (44 booklets).
- **The embedding has a one-off cost per booklet: the first case of a booklet embeds every chunk of it (about 20 to 35 s on CPU here and in the embedding branch's run, where the median case took 1.8 s and the slowest 33.9 s).** Time is scored, so the paired run must report mean and p95 time with this cost included.
