### 2026-10-08, session 2, Run C: v4-topic-first-examples (task B)

- Only change against v3: three short examples (one per label, an invented ballot, not from the dataset) before the answer format. They add exactly **168 input tokens per case** (paired difference on the same cases).
- Same command with `--prompt-b v4-topic-first-examples`, 06:24 to 06:33 UTC. 0 failed calls, 0 parse failures.
- Confusion (rows gold E/N/C): E 101/0/1, N 0/83/16, C 2/1/96. The examples help entailment but push more neutral cases to contradiction. Same-language 0.928, cross-lingual 0.935.
- Not kept: lower Macro-F1 than v3 on the same cases, and 168 more input tokens per case.
- Runs A and C ran from the `session-2` working tree before its first commit: the code equals the first session-2 commit except that `llm.py` had no retry yet and the task A path was still the placeholder (B-only input never reaches it). Per-label F1 is shown as E/N/C.
