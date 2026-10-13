"""Session 13, step 3 (no model calls): task A evidence under three page rules, today's items and H's.

Run from track_2a/ (EMBED_MODEL_DIR set as for the CLI; booklets under each set's data folder):

    python3 scripts/evidence_pages.py --out docs/runs/<folder>/evidence_pages.json \\
        --set dev output/devA/cases.jsonl output/devA/expected-labels.jsonl docs/runs/<final>/task-A output/data_dev \\
        --set val ... --set probe ...

For every gold entailment or contradiction case, the items of the run's response (today's) count as a text hit when
one of the first five matches the gold passage (the starter's rule, as in scripts/evidence_loss.py). For the cases
with a text hit, the hit items' pages are scored under three rules the organisers have not settled:

1. the page of the quoted text: the item's text lies on the page it names (partial ratio >= 90 against that page);
2. any page of the gold passage (gold pages located as in scripts/evidence_loss.py: 200-character windows, the
   pages reachable from the page holding most windows with at most two pages in between);
3. the first page of the gold passage (the lowest of those pages).

A case passes a rule when at least one hit item does. H's items (src/evidence.py hedge) are built from the same
answer: the routed part is prepared again exactly as the CLI prepares it (src/cli.py prepare, no model call; checked
against the raw answer's paragraphs_sent) and today's items are rebuilt and checked against the response. Labels are
the run's; only routed answers with label 0 or 2 can change.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from rapidfuzz import fuzz  # noqa: E402

import evidence_loss as el  # noqa: E402
from src import cli, context, evidence, nli, parse  # noqa: E402

RULES = ("text hit", "rule 1 (quote's page)", "rule 2 (any gold page)", "rule 3 (first gold page)")


def load(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def on_page(item, pages):
    text, page = el.norm(item["text"]), el.norm(pages.get(item["page"]) or "")
    return bool(text) and bool(page) and fuzz.partial_ratio(text, page, score_cutoff=el.MIN_RATIO) >= el.MIN_RATIO


def judge(items, gold_norm, gold_pages, pages):
    hits = [it for it in items[:el.MAX_ITEMS] if el.item_matches(it["text"], gold_norm)]
    first = min(gold_pages) if gold_pages else None
    return {"text hit": bool(hits),
            "rule 1 (quote's page)": any(on_page(it, pages) for it in hits),
            "rule 2 (any gold page)": any(it["page"] in gold_pages for it in hits),
            "rule 3 (first gold page)": any(it["page"] == first for it in hits)}


def hedge_items(case, data_dir, raw, pred):
    """(H's items or None if H does not apply, note). None: not a routed answer with label 0 or 2."""
    if pred["label"] not in (0, 2) or not raw.get("route") or not pred["evidence"]:
        return None, "not routed or no evidence"
    label, numbers, _ = nli.parse_label_and_pages(raw.get("answer") or "", key="paragraphs")
    settings = cli.Settings(evidence_hedge_a=True)
    prepared = cli.prepare(case, data_dir, settings)
    if prepared.kind != "A-paragraphs" or prepared.routed is None:
        return None, f"prepared as {prepared.kind}"
    paragraphs = prepared.routed[1]
    if [[p, len(t)] for p, t in paragraphs] != raw.get("paragraphs_sent"):
        return None, "routed part differs from the run's"
    today = context.VARIANTS["section-route"].evidence_items(paragraphs, numbers, halves=True)
    if today != pred["evidence"]:
        return None, "today's items differ from the run's"
    return evidence.hedge(today, paragraphs, numbers, prepared.page_texts), "ok"


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--set", nargs=5, action="append", required=True,
                        metavar=("NAME", "CASES", "EXPECTED", "RUN", "DATA_DIR"))
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    result = {"rules": RULES, "sets": {}}
    for name, cases_file, expected_file, run, data_dir in args.set:
        cases = {c["id"]: c for c in load(cases_file)}
        gold = {g["id"]: g for g in load(expected_file)}
        preds = {p["id"]: p for p in load(Path(run) / "predictions.jsonl")}
        raws = {r["id"]: r for r in load(Path(run) / "raw_answers.jsonl")}
        counts = {"today": dict.fromkeys(RULES, 0), "H": dict.fromkeys(RULES, 0)}
        notes, changed, unknown_gold, n = {}, [], 0, 0
        for cid, case in cases.items():
            if gold.get(cid, {}).get("label") not in (0, 2) or cid not in preds:
                continue
            n += 1
            pages = parse.load_pages(Path(data_dir) / case["booklet"]["path"])
            gold_norm = el.norm(gold[cid]["reference"])
            _, gold_pages, _, _ = el.gold_pages(pages, gold_norm)
            unknown_gold += not gold_pages
            today = judge(preds[cid]["evidence"], gold_norm, gold_pages, pages)
            items, note = hedge_items(case, data_dir, raws.get(cid, {}), preds[cid])
            notes[note] = notes.get(note, 0) + 1
            hedged = judge(items, gold_norm, gold_pages, pages) if items is not None else today
            if items is not None and items != preds[cid]["evidence"]:
                changed.append(cid)
            for rule in RULES:
                counts["today"][rule] += today[rule]
                counts["H"][rule] += hedged[rule]
            if hedged != today:
                notes.setdefault("cases whose rules differ", []).append([cid, today, hedged])
        result["sets"][name] = {"gold_0_2_cases": n, "gold_pages_not_found": unknown_gold, "counts": counts,
                                "evidence_changed_by_H": len(changed), "notes": notes}
        print(name, n, json.dumps(counts), "H changed", len(changed), flush=True)
    better3 = all(s["counts"]["H"][r] >= s["counts"]["today"][r] for s in result["sets"].values() for r in RULES)
    gain3 = sum(s["counts"]["H"][RULES[3]] - s["counts"]["today"][RULES[3]] for s in result["sets"].values())
    result["verdict"] = {"at_least_as_good_under_every_rule": better3, "rule_3_gain": gain3,
                         "adopt_if_also_G1_G2": better3 and gain3 > 0}
    Path(args.out).write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result["verdict"]))


if __name__ == "__main__":
    main()
