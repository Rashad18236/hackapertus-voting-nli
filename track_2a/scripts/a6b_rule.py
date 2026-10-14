"""Session 15, step 2: the A6b RULE for one interleaved run with the arms "today" (A6) and "A6b" on dev, val, probe and
the on-topic neutral set (docs/decisions/2026-10-14-1313_rashad_session-15.md has the rule and its readings).

Run from track_2a/ after scoring each arm with the starter's evaluate.py against dev's, val's and probe's expected
labels (official_score_dev.json, official_score.json for val, official_score_probe.json):

    python3 scripts/a6b_rule.py --run docs/runs/<folder> --out docs/runs/<folder>/a6b_rule.json

Both arms share every first answer (the gateway's cache answers the arm sent second), so they differ only by the second
look. A second look's fix: the first answer (neutral, the only one A6 looks at) was wrong and the final label is right;
its break: the first answer was right (gold neutral) and the final label is not. Per set and arm: Macro-F1, per-label
F1, evidence, mean input and output tokens per case, unreadable answers (first and second), second looks, changed
answers, fixes, breaks; on the on-topic set the flips away from neutral (ids). Then the rule: (1) on val + probe A6b's
fixes >= A6's - 1 and its breaks <= A6's; (2) A6b's on-topic flips < A6's; (3) A6b's mean input tokens per case over dev
+ val + probe <= A6's x 1.005.
"""

import argparse
import json
from pathlib import Path

ARMS = ("today", "A6b")
SETS = {"dev": ("output/devA/expected-labels.jsonl", "official_score_dev.json"),
        "val": ("data/val/expected-labels.jsonl", "official_score.json"),
        "probe": ("output/probeA/expected-labels.jsonl", "official_score_probe.json")}
ONTOPIC = "data/ontopic_neutral/expected-labels.jsonl"
STILL_WRONG = ["v1.1-row-235-A", "v1.1-row-1200-A", "v1.1-row-1347-A", "v1.1-row-1351-A"]  # session 14's four


def load(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    run = Path(args.run)
    preds = {a: {p["id"]: p for p in load(run / a / "predictions.jsonl")} for a in ARMS}
    raws = {a: {r["id"]: r for r in load(run / a / "raw_answers.jsonl")} for a in ARMS}
    same_first = sum(1 for i in raws["today"] if raws["today"][i].get("answer") == raws["A6b"].get(i, {}).get("answer"))
    out = {"run": str(run), "first_answers_identical": same_first, "cases": len(raws["today"]), "sets": {}}
    gold_all = {}
    for name, (expected, score_file) in SETS.items():
        gold = {e["id"]: e["label"] for e in load(expected) if e["id"].endswith("-A")}
        gold_all.update(gold)
        rows = {}
        for a in ARMS:
            official = json.loads((run / a / score_file).read_text())["tasks"]["A"]
            ids = [i for i in gold if i in preds[a]]
            looks = [i for i in ids if "second_look_a6" in raws[a][i]]
            changed = [i for i in looks if preds[a][i]["label"] != 1]
            rows[a] = {"cases": len(ids), "macro_f1": round(official["macro_f1"], 4),
                       "f1": {k: round(v["f1"], 4) for k, v in official["per_class"].items()},
                       "evidence": round(official["evidence_score"], 4),
                       "input_tokens": round(sum(preds[a][i]["metrics"]["input_tokens"] for i in ids) / len(ids), 1),
                       "output_tokens": round(sum(preds[a][i]["metrics"]["output_tokens"] for i in ids) / len(ids), 1),
                       "unreadable_first": sum(1 for i in ids if raws[a][i].get("parse_reason")),
                       "unreadable_second": sum(1 for i in looks if raws[a][i]["second_look_a6"].get("parse_reason")),
                       "failed_second": sum(1 for i in looks if raws[a][i]["second_look_a6"].get("error")),
                       "second_looks": len(looks), "second_looks_per_100": round(100 * len(looks) / len(ids), 2),
                       "changed": len(changed),
                       "fix_ids": [i for i in looks if gold[i] != 1 and preds[a][i]["label"] == gold[i]],
                       "break_ids": [i for i in looks if gold[i] == 1 and preds[a][i]["label"] != 1],
                       "gold_2_answered_1": sum(1 for i in ids if gold[i] == 2 and preds[a][i]["label"] == 1)}
            rows[a]["fixes"], rows[a]["breaks"] = len(rows[a]["fix_ids"]), len(rows[a]["break_ids"])
        out["sets"][name] = rows
    ontopic = [e["id"] for e in load(ONTOPIC)]
    flips = {a: [i for i in ontopic if "second_look_a6" in raws[a][i] and preds[a][i]["label"] != 1] for a in ARMS}
    looks_ot = {a: sum(1 for i in ontopic if "second_look_a6" in raws[a][i]) for a in ARMS}
    out["ontopic"] = {a: {"neutral": sum(1 for i in ontopic if preds[a][i]["label"] == 1), "second_looks": looks_ot[a],
                          "flips": flips[a]} for a in ARMS}
    out["still_wrong_val"] = {i: {a: preds[a][i]["label"] for a in ARMS} | {"gold": gold_all.get(i),
                              "second_look": {a: (raws[a][i].get("second_look_a6") or {}).get("answer") for a in ARMS}}
                              for i in STILL_WRONG}
    vp = {a: {k: sum(out["sets"][s][a][k] for s in ("val", "probe")) for k in ("fixes", "breaks")} for a in ARMS}
    tokens = {a: sum(preds[a][i]["metrics"]["input_tokens"] for i in gold_all if i in preds[a]) /
                 sum(1 for i in gold_all if i in preds[a]) for a in ARMS}
    out["rule"] = {
        "1_fixes_and_breaks_val_probe": {"A6": vp["today"], "A6b": vp["A6b"],
                                         "holds": vp["A6b"]["fixes"] >= vp["today"]["fixes"] - 1
                                         and vp["A6b"]["breaks"] <= vp["today"]["breaks"]},
        "2_ontopic_flips": {"A6": len(flips["today"]), "A6b": len(flips["A6b"]),
                            "holds": len(flips["A6b"]) < len(flips["today"])},
        "3_input_tokens_dev_val_probe": {"A6": round(tokens["today"], 1), "A6b": round(tokens["A6b"], 1),
                                         "change_percent": round(100 * (tokens["A6b"] / tokens["today"] - 1), 3),
                                         "holds": tokens["A6b"] <= 1.005 * tokens["today"]},
    }
    out["rule"]["adopt"] = all(v["holds"] for v in out["rule"].values())
    Path(args.out).write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for s, rows in out["sets"].items():
        for a in ARMS:
            r = rows[a]
            print(f"{s:5s} {a:5s} F1 {r['macro_f1']:.4f} ev {r['evidence']:.4f} in {r['input_tokens']} out {r['output_tokens']} "
                  f"looks {r['second_looks']} changed {r['changed']} fixes {r['fixes']} breaks {r['breaks']} "
                  f"unread {r['unreadable_first']}+{r['unreadable_second']} g2->1 {r['gold_2_answered_1']}")
    print("on-topic", json.dumps(out["ontopic"]))
    print("rule", json.dumps(out["rule"]))


if __name__ == "__main__":
    main()
