### Format check of B1 with the format fixed (session 15, step 3): readable, not void

The first 10 dev task B cases, arms `today` and `B1f` (`--prompt-b v7-same-ballot-f`: B1's prompt with "at most 6 words"
for both ballot fields, `maxLength` 40, 64 tokens), real calls, 14:11 UTC, one backend (blablador `vllm-0.23.1rc1`).

All 10 B1f answers are valid JSON with the four fields in the schema's order (`passage_ballot`, `claim_ballot`,
`same_ballot`, `label`) and a readable label: **the arm is not void**. Six of the ten ballot names are cut by the 40-
character cap (sometimes inside a word, with soft hyphens or zero-width spaces copied from the booklet's title), but the
answer still closes properly; session 13's failure (a string at its cap followed by whitespace until the budget ran out)
did not occur. In all ten answers `claim_ballot` repeats `passage_ballot` word for word and `same_ballot` is true.
