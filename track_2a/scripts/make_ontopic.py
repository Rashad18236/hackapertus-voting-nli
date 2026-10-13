"""The on-topic neutral set (session 10, step 6): dev claims that the routed part does talk about, with the gold
passage taken out, so the right answer is neutral. Indicative only. No model calls.

Run from track_2a/ (dev booklets in output/booklets_dev):

    EMBED_MODEL_DIR=models/multilingual-e5-small python3 scripts/make_ontopic.py

For every dev task A case with gold label 0 or 2 that section-route routes (router, vote match, part found):

1. the routed part's paragraphs are taken before any length cut (src/booklet.py's part_paragraphs);
2. a paragraph overlaps the gold passage if, normalised as the starter's scorer normalises (scripts/evidence_loss.py),
   either text lies inside the other (rapidfuzz partial ratio >= 90; partial ratio aligns the shorter text along
   the longer, so both directions count), or one of its 60-character windows (every 30 characters) lies inside
   the gold passage (partial ratio >= 90): a paragraph that holds only part of the passage counts too;
3. the case is kept if at least one paragraph overlaps (the gold passage is in the routed part) and at least
   three paragraphs remain after removing every overlapping one.

Writes data/ontopic_neutral/: cases.jsonl (the dev cases, id "<row>-ot-A"), expected-labels.jsonl (label 1),
exclusions.json ({id: [the removed paragraph texts, verbatim]}, for scripts/paired_run.py --exclude-paragraphs)
and summary.json. The claim is unchanged; what the model reads is the routed part without the passage the claim
came from, so a correct answer is neutral, unless the rest of the part happens to state the same thing.
"""

import json
import sys
from pathlib import Path

from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import evidence_loss as el  # noqa: E402
from src import booklet, claim_router, parse  # noqa: E402
from src.contexts import section_route  # noqa: E402

OUT = ROOT / "data" / "ontopic_neutral"
MIN_REMAINING = 3
WINDOW, STEP, THRESHOLD = 60, 30, 90


def overlaps(text, gold_norm):
    t = el.norm(text)
    if not t or not gold_norm:
        return False
    if fuzz.partial_ratio(t, gold_norm) >= THRESHOLD:
        return True
    return any(fuzz.partial_ratio(t[i:i + WINDOW], gold_norm) >= THRESHOLD
               for i in range(0, max(1, len(t) - WINDOW + 1), STEP) if len(t[i:i + WINDOW]) >= WINDOW // 2)


def main():
    cases = [json.loads(line) for line in (ROOT / "data/dev/cases.jsonl").read_text(encoding="utf-8").splitlines()
             if line.strip()]
    gold = {g["id"]: g for g in map(json.loads, (ROOT / "data/dev/expected-labels.jsonl").read_text(
        encoding="utf-8").splitlines())}
    kept, exclusions, counts = [], {}, {"gold_0_or_2": 0, "routed": 0, "gold_in_part": 0, "kept": 0}
    for case in cases:
        if "booklet" not in case or gold[case["id"]]["label"] not in (0, 2):
            continue
        counts["gold_0_or_2"] += 1
        pages = parse.load_pages(ROOT / "output/booklets_dev" / Path(case["booklet"]["path"]).name)
        part = claim_router.route(case["claim"]["text"])
        found = booklet.find_vote(section_route.parsed_booklet(pages), case["vote"]) if part else None
        if found is None or not found.ok:
            continue
        paragraphs = booklet.part_paragraphs(pages, found, part)
        if not paragraphs:
            continue
        counts["routed"] += 1
        gold_norm = el.norm(gold[case["id"]].get("reference") or "")
        removed = [text for _, text in paragraphs if overlaps(text, gold_norm)]
        if not removed:
            continue
        counts["gold_in_part"] += 1
        if len(paragraphs) - len(removed) < MIN_REMAINING:
            continue
        new_id = case["id"][:-len("-A")] + "-ot-A"
        kept.append({**case, "id": new_id})
        exclusions[new_id] = removed
    counts["kept"] = len(kept)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cases.jsonl").write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in kept), encoding="utf-8")
    (OUT / "expected-labels.jsonl").write_text("".join(json.dumps({"id": c["id"], "label": 1, "reference": ""}) + "\n"
                                                       for c in kept), encoding="utf-8")
    (OUT / "exclusions.json").write_text(json.dumps(exclusions, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    counts["removed_paragraphs_mean"] = round(sum(len(v) for v in exclusions.values()) / max(1, len(exclusions)), 2)
    (OUT / "summary.json").write_text(json.dumps(counts, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(counts))


if __name__ == "__main__":
    main()
