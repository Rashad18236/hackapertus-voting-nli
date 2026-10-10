# Runs

One folder per run. `docs/results.md` is generated from these folders by
`scripts/build_docs.py`; never edit it by hand.

## Folder name

New runs: `YYYY-MM-DD_person_variant_cases`, for example
`2026-10-09_kaan_embed-e5-small_devA300`. Sorting the folder list then sorts
by date and person. A paired or interleaved comparison is one folder with one
subfolder per arm (`<comparison>/<arm>/`), as `scripts/paired_run.py` writes
it.

Folders from before 2026-10-08 16:29 UTC keep their old names (`s2-...`,
`s3-...`), because reports and recorded commands point to them.

## What goes in a folder

- `run.json`: who, when, which code and settings, and the numbers (below).
- `NOTES.md`: what happened, starting with a `### ` heading. Several runs
  may share one notes file (both arms of a paired run: `"notes": "../NOTES.md"`).
- The run's files: `predictions.jsonl`, `raw_answers.jsonl`,
  `official_score.json` and `.txt` (the starter's scorer), `breakdown.*`
  (`src/evaluate.py`), `run.log`, `settings.json` (paired runs).

## run.json

```json
{
 "person": "rashad",
 "date": "2026-10-08",
 "start_utc": "12:06",
 "kind": "model run",
 "code": "session-3 working tree",
 "task": "A",
 "variant": "vote-section",
 "cases": "dev, all 300 task A cases",
 "setup": "A-v3-fulldoc + json_schema, vote section",
 "format": "official, paired (E2)",
 "paired_with": "s3-E2-A300/fulldoc-schema",
 "highlight": true,
 "model": "swiss-ai/apertus-v1.5-8b",
 "endpoint": "Public AI",
 "notes": "../NOTES.md",
 "results": {
  "macro_f1": 0.732,
  "f1": {"entailment": 0.845, "neutral": 0.674, "contradiction": 0.676},
  "evidence": {"score": 0.224, "found": 45, "cases": 201},
  "parse_failures": 0,
  "failed_calls": 6,
  "mean_input_tokens": 15868,
  "mean_time_ms": 8248,
  "p95_time_ms": 13513
 }
}
```

| Field | Meaning |
|---|---|
| `person` | who ran it (lower case first name); runs done in a Claude Code session count as the person who ran that session |
| `date`, `start_utc` | when the model calls started (UTC). A re-parse carries the start of the run whose answers it re-reads. `null` if not recorded; never guess |
| `kind` | `model run`, `re-parse` (answers re-read, no new calls), `re-score` (answers kept, evidence rebuilt, no new calls), `offline check` (no model calls), `model check` (model calls outside the pipeline, e.g. Apertus as a router; listed with the analyses), `stopped`, or `part of another run` (then also `part_of`) |
| `code` | the commit that ran, or the working tree it ran from |
| `task` | `A` or `B` |
| `variant` | task A context variant (`src/context.py`), or `null` |
| `cases`, `setup`, `format` | which cases; prompt and settings; scorer and whether the run is paired |
| `paired_with` | the other arm of a paired run, a list of the other arms of an interleaved run with more than two arms, or `null` |
| `highlight` | shown in bold in the results table |
| `model`, `endpoint` | the Apertus model name and the endpoint. One run uses one model name; the only exception is E3 (`2026-10-08_rashad_embed-vs-section_devA300`, recorded before this rule), whose `model` says which cases used which |
| `summary` | optional one-line result for an offline analysis that has no retrieval numbers |
| `notes` | path of the notes file, relative to this folder |
| `task_b` | task B runs only: `prompt_version`, `change` (what the prompt changed against the previous version), `n_cases`, `strict_json` (whether `response_format` was used), `max_tokens`; optional `failed_calls` for runs without a results block. `scripts/build_docs.py` shows them in the task B table and checks `n_cases` against `predictions.jsonl` |
| `canary` | task B runs since 2026-10-09 02:00 UTC: `{"before": time, "after": time}`, the canary checks made immediately before and after the run (their `time` in `docs/canary_results.jsonl`). If their answers differ, `docs/results.md` marks the run "endpoint changed during run" |
| `results` | the numbers; `null` for stopped runs. Retrieval checks use their own keys (`hit_at_k`, `evidence_ceiling_selected`, ...); other offline analyses may hold any keys |

`python3 scripts/build_docs.py --check` compares `results` with the run's own
files where they exist (`official_score.json`, `predictions.jsonl`,
`raw_answers.jsonl`) and fails on any difference.
