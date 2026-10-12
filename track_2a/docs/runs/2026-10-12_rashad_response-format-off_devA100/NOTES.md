### Task A without response_format: is the free-text answer readable? (session 10, step 7)

**Why.** `src/llm.py` drops `response_format` for the rest of a run if the endpoint refuses it (session 9). The
organisers' proxy may refuse it; then every task A answer is read as free text. This run checks how often such an
answer cannot be read.

**Run.** 100 dev task A cases (every third case of `output/devA/cases.jsonl`: 34 entailment, 33 neutral, 33
contradiction), two arms interleaved, Public AI `apertus-v1.5-8b`, one request per second; all 200 answers from one
backend (blablador); 0 failed calls.

| arm | Macro-F1 | evidence | neutral recall | unreadable | input + output tokens | fixes / breaks |
|---|---|---|---|---|---|---|
| today (json_schema) | 0.969 | 0.955 (64 of 67) | 1.000 | 0 | 1,230.0 + 14.5 | |
| no response_format | 0.980 | 0.970 (65 of 67) | 1.000 | **0** | 1,230.0 + 15.8 | 1 / 0 |

**Result: 0 of 100 answers unreadable** (rule: more than 2 % would call for a more tolerant reader; not needed).
Without the schema the model still wrote the same JSON object (`{"paragraphs": [...], "label": n}`) every time;
it used 1.3 more output tokens per case. No default changes: the schema stays (it guarantees the keys).

**Task B** sends no `response_format` by default (`schema_b` off since session 2), so "today" and "off" are the
same requests; there is nothing to compare, and no task B run was made.
