"""150 balanced dev task A cases whose opening names the same source in other words, which the rules do not match
(session 11, step 3c, run 2). No model calls.

Run from track_2a/:  python3 scripts/make_reworded.py --out output/devA_reworded150

The claim router (src/claim_router.py) matches the opening's formula ("Der Bundesrat ...", "Laut der
Zusammenfassung ...", "Si le vote est accepté ..."). Here the matched formula is replaced by a wording that names
the same source with other words (the Federal Council as "Die Landesregierung", the summary as "der Überblick im
Abstimmungsbüchlein", ...), so the label cannot change, and the result is kept only if the router finds no part in
it any more. A formula used as a prepositional phrase ("Laut dem Bundesrat") gets a prepositional replacement, a
subject ("Der Bundesrat") a subject. Cases: dev task A cases routed today, 50 per label, seed 42, in file order.

Writes <out>/cases.jsonl, <out>/expected-labels.jsonl and <out>/rewording.json (original and new opening per case).
"""

import argparse
import json
import random
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import claim_router  # noqa: E402

PREPOSITIONS = re.compile(r"^(laut|gemäss|gemäß|nach|dem|selon|d'après|secondo|stando|per|in|nel|dans|aux|a|ad|de)\b")
# (part, language, kind) -> replacement; kind "pp" (a prepositional phrase), "subject" or "clause" (detail).
REPLACEMENTS = {
    ("summary", "de", "pp"): "Gemäss dem Überblick im Abstimmungsbüchlein",
    ("summary", "de", "subject"): "Der Überblick im Abstimmungsbüchlein",
    ("summary", "fr", "pp"): "Selon l'aperçu de la brochure",
    ("summary", "fr", "subject"): "L'aperçu de la brochure",
    ("summary", "it", "pp"): "Secondo la panoramica dell'opuscolo",
    ("summary", "it", "subject"): "La panoramica dell'opuscolo",
    ("council", "de", "pp"): "Laut der Landesregierung",
    ("council", "de", "subject"): "Die Landesregierung",
    ("council", "fr", "pp"): "Selon le gouvernement fédéral",
    ("council", "fr", "subject"): "Le gouvernement fédéral",
    ("council", "it", "pp"): "Secondo il governo federale",
    ("council", "it", "subject"): "Il governo federale",
    ("committee", "de", "pp"): "Laut den Urhebern der Vorlage",
    ("committee", "de", "subject"): "Die Urheberschaft der Vorlage",
    ("committee", "fr", "pp"): "Selon les auteurs de la démarche",
    ("committee", "fr", "subject"): "Le collectif à l'origine de l'objet",
    ("committee", "it", "pp"): "Secondo il gruppo promotore",
    ("committee", "it", "subject"): "Il gruppo promotore",
    ("law", "de", "pp"): "Laut dem Wortlaut der Vorlage",
    ("law", "de", "subject"): "Der Wortlaut der Vorlage",
    ("law", "fr", "pp"): "Selon le libellé de l'objet",
    ("law", "fr", "subject"): "Le libellé de l'objet",
    ("law", "it", "pp"): "Secondo il tenore dell'oggetto",
    ("law", "it", "subject"): "Il tenore dell'oggetto",
    ("detail", "de", "clause"): "Kommt die Vorlage durch",
    ("detail", "fr", "clause"): "Dans l'hypothèse d'un oui",
    ("detail", "it", "clause"): "Nell'ipotesi di un sì",
}


def reword(claim, language):
    """(new claim, original opening, new opening) or None when the claim is not routed or the rules still match."""
    part = claim_router.route(claim)
    if part is None:
        return None
    text = unicodedata.normalize("NFKC", claim).replace("’", "'").replace("`", "'")
    lead = claim_router._LEAD.match(text.lower())
    start = lead.end() if lead else 0
    flat = claim_router.normalise(text[start:])
    if flat != text[start:].lower():  # the opening has irregular spacing: positions would not map back
        return None
    for name, pattern in claim_router._COMPILED:
        m = pattern.match(flat)
        if m and name == part:
            break
    else:
        return None
    opening = text[start:start + m.end()]
    kind = "clause" if part == "detail" else ("pp" if PREPOSITIONS.match(opening.lower()) else "subject")
    new_opening = REPLACEMENTS.get((part, language, kind))
    if new_opening is None:
        return None
    rest = text[start + m.end():]
    if kind == "clause":
        rest = rest.lstrip(" ,")
        new = f"{new_opening}, {rest}"
    else:
        new = new_opening + rest
    if claim_router.route(new) is not None:
        return None
    return new, opening, new_opening


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cases", type=Path, default=ROOT / "output" / "devA" / "cases.jsonl")
    ap.add_argument("--expected", type=Path, default=ROOT / "output" / "devA" / "expected-labels.jsonl")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--per-label", type=int, default=50)
    args = ap.parse_args()
    cases = [json.loads(line) for line in args.cases.read_text(encoding="utf-8").splitlines() if line.strip()]
    gold = {json.loads(line)["id"]: json.loads(line) for line in args.expected.read_text(encoding="utf-8").splitlines()
            if line.strip()}
    candidates = {0: [], 1: [], 2: []}
    for case in cases:
        new = reword(case["claim"]["text"], case["claim"]["language"])
        if new is not None:
            candidates[gold[case["id"]]["label"]].append((case, new))
    rng = random.Random(42)
    chosen = []
    for label in (0, 1, 2):
        picked = rng.sample(candidates[label], min(args.per_label, len(candidates[label])))
        chosen += picked
    order = {c["id"]: i for i, c in enumerate(cases)}
    chosen.sort(key=lambda x: order[x[0]["id"]])
    args.out.mkdir(parents=True, exist_ok=True)
    with open(args.out / "cases.jsonl", "w", encoding="utf-8") as f, \
         open(args.out / "expected-labels.jsonl", "w", encoding="utf-8") as g:
        for case, (new, _, _) in chosen:
            c = json.loads(json.dumps(case))
            c["claim"]["text"] = new
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
            g.write(json.dumps(gold[case["id"]], ensure_ascii=False) + "\n")
    rewording = {case["id"]: {"part": claim_router.route(case["claim"]["text"]), "language": case["claim"]["language"],
                              "opening": old, "new_opening": new_opening}
                 for case, (_, old, new_opening) in chosen}
    (args.out / "rewording.json").write_text(json.dumps(rewording, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    from collections import Counter
    print(len(chosen), "cases;", {k: len(v) for k, v in candidates.items()}, "candidates per label;",
          dict(Counter(r["part"] for r in rewording.values())), dict(Counter(r["language"] for r in rewording.values())))


if __name__ == "__main__":
    main()
