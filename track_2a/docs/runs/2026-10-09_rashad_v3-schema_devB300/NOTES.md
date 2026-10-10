### 2026-10-09, task B cheap fixes, run 1 (v3 + strict JSON): stopped before the first case, the canary failed

- Before run 1, `scripts/canary_taskb.py` re-sent the 30 canary cases (`docs/canary_taskb.json`) with exactly the baseline request (v3-topic-first, max_tokens 32, no response_format, temperature 0, `swiss-ai/apertus-v1.5-8b` on Public AI).
- **01:50:33 UTC (`canary.txt`): 3 of 30 answer texts differ from the baseline run of 01:25** (`2026-10-09_rashad_v3-topic-first_devB300-run1`):
  - `v1.1-row-767-B`: `{"label": 2}` then, `{"label": 1}` now;
  - `v1.1-row-869-B`: `{"label": 2}` then, `{"label": 1}` now;
  - `v1.1-row-1128-B`: `{"label": 2}` then, the same label followed by a "**Reasoning:**" paragraph now.
- **01:51:32 UTC (`canary_repeat.txt`, a repeat for the report, not a run): the same three differences, character for character.** The new answers are stable, so this is a change of what the endpoint serves, not noise: the baseline runs of 01:25 and 01:33 had given identical texts in all 299 cases both answered.
- The change happened between 01:36 (end of the second baseline run) and 01:50 UTC. The status page (status.publicai.co) shows `swiss-ai/apertus-v1.5-8b` as "Operational" (27 % uptime over 30 days) and names no supplier change.
- Both changed labels move from contradiction to neutral on gold-neutral cases (rows 767 and 869 were in the baseline's error list), so the new behaviour may score differently on all 300; that is not measured. **The 0.919 baseline no longer describes the current endpoint.**
- As the stage rule says, no run started: neither the 20-case token check of the schema nor the 300-case run.
