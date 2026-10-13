### Replay reference of session 12's final defaults (G1/G2 anchor from now on)

`scripts/prompt_snapshot.py` runs the real CLI with the final defaults against the fake model and records the SHA-256
of every request body, of every parsing or translation call, and every task A path; the fake model answers each
request with the saved answer of the final runs (`2026-10-13_rashad_final-s12_dev600`, task A and B; `..._val1160`,
task A). Built in two passes: a case that falls back across languages first asks Apertus to translate the claim, and
that translation chooses the chunks of its reading request, so the first pass learns the translations and the second
the reading requests they lead to.

Replaying reproduces the final runs exactly: **0 label and 0 evidence differences in 1,180 cases**
(`replay_vs_final_runs.json`); 1,183 requests (1,180 answers, 3 translations). Task A paths: routed 876, bm25-ap
fallback 4. G1 (requests and paths) and G2 (labels and evidence) after a code change now compare with this folder;
`scripts/local_time.py` replays its `replay_table.json` by default.
