<!--
Title: what changed and the headline number, e.g.
"Task A embed-e5-small vs vote-section, paired on 300 dev cases (0.77 vs 0.73)".
Branch: person/topic, started from a fresh main. Merge into main the same day if you can.
-->

## Summary

What this PR does and why, in two or three sentences. Where to start reading.

- **Built by:** <!-- person (and whether with Claude Code) -->
- **Stage:** <!-- the current stage in CLAUDE.md -->

## Results on dev

<!-- Official starter scorer; never test. Write "No new model runs." if there are none. -->

| Run (`docs/runs/...`) | Variant / setup | Macro-F1 | Evidence | Mean input tokens | Mean / p95 time | Paired with |
|---|---|---|---|---|---|---|
| | | | | | | |

## What changed

- Code: <!-- files, and any new or changed variant name (a changed behaviour gets a new name) -->
- Runs added: <!-- docs/runs/<folder>/ with run.json and NOTES.md -->
- Decisions added: <!-- docs/decisions/<YYYY-MM-DD-HHMM>_<person>_<topic>.md -->
- Defaults changed: <!-- none, or which and why -->

## Checks

From `track_2a/`:

- [ ] `python3 -m pytest tests` passes
- [ ] `python3 scripts/build_docs.py --check` passes (results.md and decisions.md regenerated, not edited by hand)
- [ ] `python3 scripts/self_checks.py --starter <starter checkout>` passes
- [ ] `make run` exits 0 and `scripts/check_format.py` reports no errors (if code changed)
- [ ] No API key, `.env`, booklet PDF or model file in any commit; nothing run on `data/test/`
