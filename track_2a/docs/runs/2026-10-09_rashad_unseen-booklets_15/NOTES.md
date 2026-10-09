### 2026-10-09, checks without a model, Part 5: booklets the parser has never seen

- Booklets: the Federal Chancellery's PDFs for the five most recent vote dates in neither dev nor test that have a booklet: 2026-09-27 (published after the dataset; admin.ch) and 2019-05-19, 2019-02-10, 2018-11-25, 2018-09-23 (bk.admin.ch archive "Sammlung der Abstimmungsbüchlein seit 1978"), each in German, French and Italian; downloaded to `output/booklets_unseen/` (git-ignored) by `scripts/fetch_unseen_booklets.py`. Every 2020-2026 date in the archive is already in the dataset, so older dates were the only other unseen ones.
- Commands (from `track_2a/`): `python3 -I scripts/unseen_booklets.py --booklets output/booklets_unseen --out <folder>` and the same with `--proposal`; for the dev check `--booklets output/booklets_dev`. Outputs: `output.txt`, `output_proposal.txt`, `booklets.json`, `booklets_proposal.json`, `dev_with_proposal.txt`.

**As the parser is (src/booklet.py unchanged):**

| Booklet date | de | fr | it | What failed |
|---|---|---|---|---|
| 2026-09-27 (2 votes) | complete | complete | complete | nothing: all parts, boxes and paragraphs found |
| 2019-05-19 (2 votes) | no parts | no parts | no parts | no start page for the council's arguments |
| 2019-02-10 (1 vote) | no parts | no parts | no parts | no start page for the council's arguments |
| 2018-11-25 (3 votes) | no parts | no parts | no parts | no start page for the council's arguments |
| 2018-09-23 (3 votes) | no parts | no parts | no parts | vote 1: no arguments heading on page 14; votes 2-3: no start page for the council's arguments |

- In every booklet the contents were read and every vote was found (33 votes); a vote that fails a check gets no parts, so its cases would fall back to embed-e5-small (answered, not routed). The parser never guessed a wrong part.
- Where a vote's title could be read from its detail page, `find_vote()` picked that vote (no wrong pick).
- **Why 2018-2019 fail:** the per-vote lists and headings name the council's arguments "Argumente Bundesrat", "Les arguments du Conseil fédéral", "Gli argomenti del Consiglio federale", without "und Parlament / et du Parlement / e del Parlamento", which `_COUNCIL` requires. In 2018-09-23 the first vote (a direct counter-proposal, initiative withdrawn) has no committee; its arguments open with the parliamentary debate ("Debatte im Parlament", "Le débat au Parlement", "Le deliberazioni in Parlamento"), so the contents' "Argumente 14" page carries no "Argumente" heading; and the Italian name of the debate is not in `_DEBATE`.

**With the proposed patterns** (applied in memory by `--proposal`, `src/booklet.py` not changed): council titles with "und Parlament" optional; "deliberazioni in Parlamento" as a debate name; a debate heading accepted as the arguments' start heading. Result: **14 of 15 booklets complete, 32 of 33 votes**. The one left: Italian 2018-09-23, vote 1, where pypdf splits the heading "Le deliberazioni in Parlamento" into "Le delibe Parlamento" / "razioni". On the 44 dev booklets the proposal changes nothing (131 of 131 votes, identical parts, boxes and paragraph counts).
