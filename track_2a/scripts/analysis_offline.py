"""Session 9, phase B: analyses of answers we already have. No model calls.

Run from track_2a/ (dev booklets in output/booklets_dev):

    EMBED_MODEL_DIR=models/multilingual-e5-small python3 scripts/analysis_offline.py --out <folder> \\
        [--task-b-val <run folder with val task B answers> --task-b-val-cases output/valB]

Answers used (the default settings when they were recorded):
- task A, dev: E5's section-route arm (2026-10-08, all 300 dev task A cases);
- task A, val: E6's section-route arm (2026-10-09, the balanced 300 val cases);
- task B, dev: stability point 1 (2026-10-09, all 300 dev task B cases, v3-topic-first);
- task B, val: only if --task-b-val is given (phase C's "current" arm on the 580 val task B cases).

B1  Error margin: 95 % bootstrap interval of Macro-F1 (2,000 resamples of the cases, seed 42), dev and val
    pooled, per task; and accuracy by claim language x source language.
B2  Task A evidence pages: of the gold entailment/contradiction cases whose evidence matches the gold passage
    (the starter's text rule), how many also have the right page, under three rules: (1) the item's page is any
    page of the gold passage; (2) it is the passage's first page; (3) it is the page that holds the quoted text.
    Gold pages are found as in session 5 (200-character windows of the gold passage, scripts/evidence_loss.py).
B3  Claims tagged for numbers, dates, negation and qualifying words (word lists below, de/fr/it); accuracy per
    tag, per task.
B4  Rules without a model (never used in the pipeline): always neutral; task B "a reference over 8,000
    characters is neutral".
B5  The 13 val errors of E6: was the gold passage among the paragraphs sent? The paragraphs are rebuilt with
    today's code (session 8's gate G1 showed that it sends the same requests for these cases).
B6  Every neutral answer of E5: the e5 similarity between the claim and the most similar paragraph sent;
    true neutral against wrongly neutral; is there a threshold that separates them?

Writes analysis.json and per_case.jsonl to --out and prints the summary.
"""

import argparse
import json
import random
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import evidence_loss as el  # noqa: E402
from src import evaluate, parse  # noqa: E402
from src.contexts import retrieval, section_route  # noqa: E402

RUNS = ROOT / "docs" / "runs"
E5 = RUNS / "2026-10-08_rashad_section-route-vs-embed_devA300" / "section-route"
E6 = RUNS / "2026-10-09_rashad_section-route-vs-embed_valA300" / "section-route"
STABILITY_1 = RUNS / "2026-10-09_rashad_stability-1_dev600" / "task-B"
BOOKLETS = ROOT / "output" / "booklets_dev"
SEED, RESAMPLES = 42, 2000
LANGS = ("de", "fr", "it")

# B3: word lists, lower case, matched as whole words (a trailing * allows any ending).
TAGS = {
    "number": [r"\d"],
    "date": [r"\b(1[89]|20)\d\d\b",
             r"\b(januar|februar|märz|april|mai|juni|juli|august|september|oktober|november|dezember)\b",
             r"\b(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\b",
             r"\b(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\b"],
    "negation": [r"\b(nicht|kein\w*|nie|niemals|weder|ohne)\b",
                 r"\b(ne|n['’]|pas|aucun\w*|jamais|ni|sans)\b",
                 r"\b(non|nessun\w*|mai|né|senza)\b"],
    "qualifier": [r"\b(nur|alle|allen|immer|mindestens|höchstens|ausschliesslich|ausschließlich|sämtliche|einzig\w*|"
                  r"mehr als|weniger als|über|unter)\b",
                  r"\b(seulement|uniquement|tous|toutes|toujours|au moins|au plus|exclusivement|plus de|moins de)\b",
                  r"\b(solo|soltanto|solamente|tutti|tutte|sempre|almeno|al massimo|esclusivamente|più di|meno di)\b"],
}


def load(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def by_id(path):
    return {r["id"]: r for r in load(path)}


def macro(gold, pred):
    return evaluate.label_scores(gold, pred)["macro_f1"]


def bootstrap(gold, pred):
    rng = random.Random(SEED)
    n, values = len(gold), []
    for _ in range(RESAMPLES):
        idx = [rng.randrange(n) for _ in range(n)]
        values.append(macro([gold[i] for i in idx], [pred[i] for i in idx]))
    values.sort()
    return {"macro_f1": round(macro(gold, pred), 4), "low": round(values[int(0.025 * RESAMPLES)], 4),
            "high": round(values[int(0.975 * RESAMPLES) - 1], 4), "cases": n}


def source_language(case):
    return (case.get("booklet") or case.get("reference"))["language"]


def tags_of(text):
    t = text.lower()
    return [tag for tag, patterns in TAGS.items() if any(re.search(p, t) for p in patterns)]


def answer_set(name, cases_path, gold_path, pred_dir, raw=True):
    cases = by_id(cases_path)
    gold = by_id(gold_path)
    preds = by_id(pred_dir / "predictions.jsonl")
    raws = by_id(pred_dir / "raw_answers.jsonl") if raw else {}
    ids = [i for i in gold if i in preds]
    assert len(ids) == len(gold), (name, len(ids), len(gold))
    return {"name": name, "ids": ids, "cases": cases, "gold": gold, "preds": preds, "raws": raws}


def b1(sets_by_task):
    out = {}
    for task, sets in sets_by_task.items():
        rows = [(s, i) for s in sets for i in s["ids"]]
        gold = [s["gold"][i]["label"] for s, i in rows]
        pred = [s["preds"][i]["label"] for s, i in rows]
        entry = {"pooled": bootstrap(gold, pred), "sets": [s["name"] for s in sets]}
        for s in sets:
            entry[s["name"]] = bootstrap([s["gold"][i]["label"] for i in s["ids"]],
                                         [s["preds"][i]["label"] for i in s["ids"]])
        table = {}
        for cl in LANGS:
            for sl in LANGS:
                sub = [(s, i) for s, i in rows if s["cases"][i]["claim"]["language"] == cl
                       and source_language(s["cases"][i]) == sl]
                right = sum(1 for s, i in sub if s["preds"][i]["label"] == s["gold"][i]["label"])
                table[f"{cl}->{sl}"] = {"cases": len(sub), "right": right,
                                        "accuracy": round(right / len(sub), 3) if sub else None}
        entry["claim_x_source"] = table
        out[task] = entry
    return out


def b2(sets, pages_of):
    out, per_case = {}, []
    for s in sets:
        counts = defaultdict(int)
        for i in s["ids"]:
            g = s["gold"][i]
            if g["label"] not in (0, 2) or not g.get("reference"):
                continue
            counts["gold cases"] += 1
            case = s["cases"][i]
            pages = pages_of(case)
            gold_norm = el.norm(g["reference"])
            _, gold_pages, _, _ = el.gold_pages(pages, gold_norm)
            items = s["preds"][i]["evidence"][:el.MAX_ITEMS]
            text_ok = [it for it in items if el.item_matches(it["text"], gold_norm)]
            if not text_ok:
                continue
            counts["text matches"] += 1
            rule1 = any(it["page"] in gold_pages for it in text_ok)
            rule2 = bool(gold_pages) and any(it["page"] == gold_pages[0] for it in text_ok)
            rule3 = any(it["page"] in pages and el.item_matches(it["text"], el.norm(pages[it["page"]]))
                        for it in text_ok)
            counts["rule 1: any gold page"] += rule1
            counts["rule 2: first gold page"] += rule2
            counts["rule 3: page of the quoted text"] += rule3
            counts["no gold page found"] += not gold_pages
            per_case.append({"set": s["name"], "id": i, "gold_pages": gold_pages,
                             "matching_item_pages": [it["page"] for it in text_ok],
                             "rule1": rule1, "rule2": rule2, "rule3": rule3})
        out[s["name"]] = dict(counts)
    return out, per_case


def b3(sets_by_task):
    out = {}
    for task, sets in sets_by_task.items():
        stats = defaultdict(lambda: [0, 0])
        for s in sets:
            for i in s["ids"]:
                right = s["preds"][i]["label"] == s["gold"][i]["label"]
                tags = tags_of(s["cases"][i]["claim"]["text"])
                for tag in TAGS:
                    key = f"{tag}: yes" if tag in tags else f"{tag}: no"
                    stats[key][0] += 1
                    stats[key][1] += right
                stats["any tag" if tags else "no tag"][0] += 1
                stats["any tag" if tags else "no tag"][1] += right
        out[task] = {k: {"cases": n, "right": r, "accuracy": round(r / n, 3)} for k, (n, r) in sorted(stats.items())}
    return out


def b4(sets_by_task):
    out = {}
    for task, sets in sets_by_task.items():
        for s in sets:
            gold = [s["gold"][i]["label"] for i in s["ids"]]
            entry = {"always neutral": round(macro(gold, [1] * len(gold)), 4)}
            if task == "B":
                long = {i: len(s["cases"][i]["reference"]["text"]) > 8000 for i in s["ids"]}
                for name, chosen in (("long", True), ("short", False)):
                    sub = [i for i in s["ids"] if long[i] == chosen]
                    entry[f"{name} references"] = {"cases": len(sub),
                                                   "neutral": sum(1 for i in sub if s["gold"][i]["label"] == 1)}
                entry["long -> neutral, else entailment"] = round(
                    macro(gold, [1 if long[i] else 0 for i in s["ids"]]), 4)
                entry["long -> neutral, else the model's answer"] = round(
                    macro(gold, [1 if long[i] else s["preds"][i]["label"] for i in s["ids"]]), 4)
                entry["the model's answer"] = round(macro(gold, [s["preds"][i]["label"] for i in s["ids"]]), 4)
            out[f"{task} {s['name']}"] = entry
    return out


def sent_paragraphs(case, pages):
    routed = section_route.route(pages, case["vote"], case["claim"]["text"])
    return None if routed is None else routed


def b5(val_set, pages_of):
    rows = []
    for i in val_set["ids"]:
        pred, gold = val_set["preds"][i]["label"], val_set["gold"][i]
        if pred == gold["label"]:
            continue
        case = val_set["cases"][i]
        pages = pages_of(case)
        routed = sent_paragraphs(case, pages)
        raw = val_set["raws"].get(i, {})
        row = {"id": i, "gold": gold["label"], "pred": pred, "claim_language": case["claim"]["language"],
               "booklet_language": case["booklet"]["language"], "route": raw.get("route"),
               "claim": case["claim"]["text"], "answer": raw.get("answer")}
        if routed is None:
            row["sent"] = "fell back to embed-e5-small"
        else:
            part, paragraphs = routed
            row["sent_paragraphs"] = len(paragraphs)
            if gold["label"] in (0, 2) and gold.get("reference"):
                gold_norm = el.norm(gold["reference"])
                inside = [n for n, (_, t) in enumerate(paragraphs, start=1) if el.item_matches(t, gold_norm)]
                row["gold_passage_sent"] = bool(inside)
                row["gold_paragraphs"] = inside
                try:
                    row["cited"] = json.loads(raw.get("answer") or "{}").get("paragraphs")
                except ValueError:
                    row["cited"] = None
            else:
                row["gold_passage_sent"] = "no gold passage (gold neutral)"
        rows.append(row)
    return rows


def b6(dev_set, pages_of):
    rows = []
    for i in dev_set["ids"]:
        if dev_set["preds"][i]["label"] != 1:
            continue
        case = dev_set["cases"][i]
        routed = sent_paragraphs(case, pages_of(case))
        if routed is None:
            rows.append({"id": i, "gold": dev_set["gold"][i]["label"], "similarity": None})
            continue
        _, paragraphs = routed
        texts = [section_route.display(t) for _, t in paragraphs]
        vectors = retrieval.embedder("e5-small").embed([f"passage: {t}" for t in texts])
        scores = vectors @ retrieval.query_vector("e5-small", case["claim"]["text"])
        rows.append({"id": i, "gold": dev_set["gold"][i]["label"], "similarity": round(float(max(scores)), 4)})
    true_n = sorted(r["similarity"] for r in rows if r["gold"] == 1 and r["similarity"] is not None)
    wrong_n = sorted(r["similarity"] for r in rows if r["gold"] != 1 and r["similarity"] is not None)
    thresholds = []
    for t in sorted(set(true_n + wrong_n)):
        thresholds.append({"threshold": t, "wrongly_neutral_at_or_above": sum(1 for x in wrong_n if x >= t),
                           "true_neutral_at_or_above": sum(1 for x in true_n if x >= t)})
    describe = lambda xs: ({"n": len(xs), "min": min(xs), "median": statistics.median(xs), "max": max(xs)}  # noqa: E731
                           if xs else {"n": 0})
    return {"neutral_answers": len(rows), "true_neutral": describe(true_n), "wrongly_neutral": describe(wrong_n),
            "thresholds": thresholds}, rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--task-b-val", type=Path)
    ap.add_argument("--task-b-val-cases", type=Path, default=ROOT / "output" / "valB")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    a_dev = answer_set("dev (E5)", ROOT / "output/devA/cases.jsonl", ROOT / "output/devA/expected-labels.jsonl", E5)
    a_val = answer_set("val (E6)", ROOT / "data/val/sample300/cases.jsonl",
                       ROOT / "data/val/sample300/expected-labels.jsonl", E6)
    b_dev = answer_set("dev (stability 1)", ROOT / "output/devB/cases.jsonl", ROOT / "output/devB/expected-labels.jsonl",
                       STABILITY_1)
    sets = {"A": [a_dev, a_val], "B": [b_dev]}
    if args.task_b_val:
        sets["B"].append(answer_set("val (phase C current)", args.task_b_val_cases / "cases.jsonl",
                                    args.task_b_val_cases / "expected-labels.jsonl", args.task_b_val))

    cache = {}

    def pages_of(case):
        path = BOOKLETS / Path(case["booklet"]["path"]).name
        if path not in cache:
            cache[path] = parse.load_pages(path)
        return cache[path]

    result = {"B1": b1(sets), "B3": b3(sets), "B4": b4(sets)}
    result["B2"], b2_rows = b2(sets["A"], pages_of)
    result["B5"] = b5(a_val, pages_of)
    result["B6"], b6_rows = b6(a_dev, pages_of)
    (args.out / "analysis.json").write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    with (args.out / "per_case.jsonl").open("w", encoding="utf-8") as f:
        for row in b2_rows:
            f.write(json.dumps({"analysis": "B2", **row}, ensure_ascii=False) + "\n")
        for row in b6_rows:
            f.write(json.dumps({"analysis": "B6", **row}, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "B5"}, indent=1, ensure_ascii=False)[:6000])
    print(json.dumps(result["B5"], indent=1, ensure_ascii=False)[:6000])


if __name__ == "__main__":
    main()
