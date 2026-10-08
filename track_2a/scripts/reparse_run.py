"""Re-derive a task A run's predictions from its saved raw answers with the current parser.

Run from track_2a/:
    python3 scripts/reparse_run.py RUN_DIR CASES BOOKLET_DIR OUT_DIR

No model calls: labels and pages come from RUN_DIR/raw_answers.jsonl, read with
the current nli.parse_label_and_pages; evidence is rebuilt from the same
booklets with parse.evidence_items; metrics (tokens, time) are copied from
RUN_DIR/predictions.jsonl, since the calls are the same. Failed calls keep
their fallback response. Used to measure parser changes without new calls.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import nli, parse  # noqa: E402


def main():
    run_dir, cases_path, booklet_dir, out_dir = map(Path, sys.argv[1:5])
    cases = {json.loads(l)["id"]: json.loads(l) for l in open(cases_path, encoding="utf-8")}
    preds = {json.loads(l)["id"]: json.loads(l) for l in open(run_dir / "predictions.jsonl", encoding="utf-8")}
    raws = [json.loads(l) for l in open(run_dir / "raw_answers.jsonl", encoding="utf-8")]
    out_dir.mkdir(parents=True, exist_ok=True)
    changed = recovered = 0
    with open(out_dir / "predictions.jsonl", "w", encoding="utf-8") as f:
        for raw in raws:
            old = preds[raw["id"]]
            new = dict(old)
            if raw.get("answer") is not None:
                label, pages, _ = nli.parse_label_and_pages(raw["answer"])
                if label is None:
                    label, evidence = 1, []  # same fallback as the pipeline
                else:
                    recovered += bool(raw.get("parse_reason"))
                    booklet = parse.load_pages(Path(booklet_dir) / Path(cases[raw["id"]]["booklet"]["path"]).name)
                    evidence = parse.evidence_items(booklet, pages) if label in (0, 2) else []
                new.update(label=label, label_name=nli.LABEL_NAMES[label], evidence=evidence)
            changed += new != old
            f.write(json.dumps(new, ensure_ascii=False) + "\n")
    (out_dir / "README.txt").write_text(
        f"Re-parsed offline from {run_dir.name}/raw_answers.jsonl with the current parser "
        f"(explicit prose label statements accepted). No new model calls; metrics copied.\n"
        f"Responses changed: {changed}; previously unparseable answers now read: {recovered}.\n", encoding="utf-8")
    print(f"{run_dir.name}: responses changed {changed}, unparseable answers now read {recovered}")


if __name__ == "__main__":
    main()
