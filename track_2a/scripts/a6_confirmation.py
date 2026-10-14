"""Session 14, step 1: the A6 CONFIRMATION RULE for one interleaved run with the arms "today" and "today+A6" on val, probe
and the on-topic neutral set (docs/decisions/2026-10-14-0832_rashad_session-14.md has the rule and its readings).

Run from track_2a/ after scoring each arm with the starter's evaluate.py twice: against val's expected labels
(official_score.json) and against probe's (official_score_probe.json):

    python3 scripts/a6_confirmation.py --run docs/runs/<folder> --val data/val/expected-labels.jsonl \\
        --probe output/probeA/expected-labels.jsonl --ontopic data/ontopic_neutral/expected-labels.jsonl \\
        --focus docs/runs/2026-10-13_rashad_final-s12_val1160/task-A --out docs/runs/<folder>/a6_rule.json

Per set (val, probe) and arm: scripts/arm_table.py's numbers (Macro-F1, per-label F1, evidence, input and output
tokens, unreadable answers, fixes and breaks, the row "gold contradiction answered neutral", A6's second looks; on val
also which of session 12's errors answered neutral are fixed). Then the rule's seven conditions:
(a) val Macro-F1 +0.005; (b) probe Macro-F1 not below today's; (c) fixes > breaks over val and probe, one-sided sign
test p <= 0.10; (d) mean input tokens per case over val and probe at most +3 %; (e) unreadable answers over the whole run
(first answers and second looks) not more than today's; (f) at most 2 on-topic cases answered neutral by today and not
neutral by today+A6; (g) at most one second look per case, and each case's metrics equal its recorded calls (no hidden
call).
"""

import argparse
import json
from pathlib import Path

import arm_table  # scripts/arm_table.py (same folder)


def calls_of(raw):
    """[(name, input tokens, output tokens)] of every call a raw answer records besides the main one: A6's second look
    ("second_look_a6") and the parsing roles (AP-part, AP-structure, AP-translate: "ap_calls")."""
    calls = []
    look = raw.get("second_look_a6")
    if isinstance(look, dict):
        calls.append(("second_look_a6", look.get("input_tokens", 0), look.get("output_tokens", 0)))
    for call in raw.get("ap_calls") or []:
        calls.append((call.get("version"), call.get("input_tokens", 0), call.get("output_tokens", 0)))
    return calls


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--run", required=True)
    ap.add_argument("--val", required=True)
    ap.add_argument("--probe", required=True)
    ap.add_argument("--ontopic", required=True)
    ap.add_argument("--focus")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    run = Path(args.run)
    load = arm_table.load
    focus = {p["id"]: p for p in load(Path(args.focus) / "predictions.jsonl")} if args.focus else None
    arms = ("today", "today+A6")
    preds = {a: {p["id"]: p for p in load(run / a / "predictions.jsonl")} for a in arms}
    raws = {a: {} for a in arms}
    raw_counts = {a: {} for a in arms}
    for a in arms:
        for r in load(run / a / "raw_answers.jsonl"):
            raws[a][r["id"]] = r
            raw_counts[a][r["id"]] = raw_counts[a].get(r["id"], 0) + 1
    out = {"run": str(run), "sets": {}}
    for name, expected, score_file in (("val", args.val, "official_score.json"),
                                       ("probe", args.probe, "official_score_probe.json")):
        gold = {e["id"]: e["label"] for e in load(expected) if e["id"].endswith("-A")}
        out["sets"][name] = {a: arm_table.arm_numbers(run / a, "A", gold, None if a == "today" else preds["today"],
                                                      None, focus if name == "val" else None, None, score_file)
                             for a in arms}
        for a in arms:  # fix and break ids are long lists; keep them, they are the report's case lists
            out["sets"][name][a]["gold_ids"] = len(gold)
    val, probe = out["sets"]["val"], out["sets"]["probe"]
    scored = [i for i in preds["today"] if not i.endswith("-ot-A")]
    ontopic = [e["id"] for e in load(args.ontopic)]
    fixes = val["today+A6"]["fixes"] + probe["today+A6"]["fixes"]
    breaks = val["today+A6"]["breaks"] + probe["today+A6"]["breaks"]
    p_one = arm_table.sign_test(fixes, breaks)
    tokens = {a: sum(preds[a][i]["metrics"]["input_tokens"] for i in scored) / len(scored) for a in arms}
    unreadable = {}
    for a in arms:
        first = sum(1 for r in raws[a].values() if r.get("parse_reason"))
        second = sum(1 for r in raws[a].values() if (r.get("second_look_a6") or {}).get("parse_reason"))
        unreadable[a] = {"first_answers": first, "second_looks": second, "total": first + second}
    flips = [i for i in ontopic if preds["today"][i]["label"] == 1 and preds["today+A6"][i]["label"] != 1]
    flips_by_look = [i for i in flips if "second_look_a6" in raws["today+A6"][i]]
    other_changes = [i for i in ontopic if preds["today"][i]["label"] != preds["today+A6"][i]["label"] and i not in flips]
    # (g): one raw record per case and arm; today never has a second look; each case's metrics equal its main call
    # plus the calls its raw answer records (a third call would show as tokens no record accounts for)
    once = {"records_per_case_max": {a: max(raw_counts[a].values()) for a in arms},
            "today_second_looks": sum(1 for r in raws["today"].values() if "second_look_a6" in r),
            "a6_second_looks": sum(1 for r in raws["today+A6"].values() if "second_look_a6" in r)}
    mismatched = []
    for i, r in raws["today+A6"].items():
        extra = calls_of(r)
        main_out = r.get("output_tokens")
        if main_out is None:
            continue
        if preds["today+A6"][i]["metrics"]["output_tokens"] != main_out + sum(c[2] for c in extra):
            mismatched.append(i)
    once["metrics_not_matching_recorded_calls"] = mismatched
    once["holds"] = (once["records_per_case_max"]["today"] == 1 and once["records_per_case_max"]["today+A6"] == 1
                     and once["today_second_looks"] == 0 and not mismatched)
    rule = {
        "a": {"today": val["today"]["macro_f1"], "today+A6": val["today+A6"]["macro_f1"],
              "diff": round(val["today+A6"]["macro_f1"] - val["today"]["macro_f1"], 4),
              "holds": val["today+A6"]["macro_f1"] >= val["today"]["macro_f1"] + 0.005},
        "b": {"today": probe["today"]["macro_f1"], "today+A6": probe["today+A6"]["macro_f1"],
              "holds": probe["today+A6"]["macro_f1"] >= probe["today"]["macro_f1"]},
        "c": {"fixes": fixes, "breaks": breaks, "sign_test_p_one_sided": round(p_one, 4),
              "sign_test_p_two_sided": round(min(1.0, 2 * min(p_one, arm_table.sign_test(breaks, fixes))), 4),
              "holds": fixes > breaks and p_one <= 0.10},
        "d": {"cases": len(scored), "today": round(tokens["today"], 1), "today+A6": round(tokens["today+A6"], 1),
              "change_percent": round(100 * (tokens["today+A6"] / tokens["today"] - 1), 2),
              "holds": tokens["today+A6"] <= 1.03 * tokens["today"]},
        "e": {**{a: unreadable[a] for a in arms}, "holds": unreadable["today+A6"]["total"] <= unreadable["today"]["total"]},
        "f": {"cases": len(ontopic), "today_neutral": sum(1 for i in ontopic if preds["today"][i]["label"] == 1),
              "a6_neutral": sum(1 for i in ontopic if preds["today+A6"][i]["label"] == 1),
              "flips": flips, "flips_by_second_look": flips_by_look, "other_changes": other_changes,
              "holds": len(flips) <= 2},
        "g": once,
    }
    rule["adopt"] = all(rule[k]["holds"] for k in "abcdefg")
    out["rule"] = rule
    Path(args.out).write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for k in "abcdefg":
        print(k, json.dumps({x: y for x, y in rule[k].items() if x not in ("flips",)}, ensure_ascii=False)[:300])
    print("adopt:", rule["adopt"])


if __name__ == "__main__":
    main()
