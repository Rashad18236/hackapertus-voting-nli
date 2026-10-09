# Task B errors: v3-topic-first on the 300 dev cases

Run: `docs/runs/2026-10-09_rashad_v3-topic-first_devB300-run1/` (task B
confirmation stage; Macro-F1 0.919, 24 of 300 wrong). The second run on the
same cases gave the same answer text in all 299 cases it answered, so this
list holds for both. The cases below are written by
`scripts/taskb_analysis.py`; the patterns were described by reading every case.

## The patterns in plain words

**1. An unrelated claim called a contradiction (17 of 24).** The dataset
builds its neutral cases by pairing a claim with the passage of another
ballot (in all 99 neutral dev cases the passage belongs to a different vote
than the claim). In these 17 the model said the passage refutes the claim
instead of "does not deal with it". 13 of the 17 claims attribute a statement
to a source ("according to the summary / the text put to the vote / the
committee / the Federal Council, X"), 4 begin "if the vote is accepted, X";
many state specific invented facts (a French law of 2023, a 2-billion
defence budget, joining the EU by 2025). 12 of the 17 are cross-language.
v3's rule says that such a claim is neutral when the text does not deal
with X; in these cases the model does not follow it. All neutral passages
are long (9,746 to 20,284 characters), and the errors are about as frequent
among the shorter ones (10 of 61 under 15,000 characters) as among the
longer (7 of 37).

**2. A refuted claim called neutral (5).** Each time, the refuting statement
is one detail of the passage, and the model did not use it:

- `1016` (French passage, German claim): the passage says the Federal
  Council *will* choose the type and number of aircraft if the people
  accept; the claim says it fixed them before the vote.
- `1138` (German, German): "75 % der Einnahmen sollen an die Kantone, 25 % an
  den Bund gehen"; the claim says half each. The passage is short (1,560
  characters), so length is not the reason here.
- `1167` (German passage, French claim): the committee has withdrawn the
  Glacier initiative on condition, and only after a "no" does it decide
  whether the initiative goes to the vote; the claim says it goes to the vote
  if the law is accepted.
- `1208` (German passage, French claim): the legal text's last article says
  the Federal Assembly recommends *rejecting* the initiative; the claim says
  accepting.
- `1468` (German passage, Italian claim): in a 19,312-character legal text,
  the Confederation pays 70 % (not all) of the cantons' hardship measures for
  firms with a turnover up to 5 million francs.

Four of the five are cross-language; three hinge on a number or a reversed
recommendation stated once.

**3. A supported claim called neutral (1).** `22` (German, German): the
passage says "Die Verfassung definiert die Ehe nicht als Verbindung zwischen
Frau und Mann", which is the claim's point.

**4. A supported claim called a contradiction (1).** `31` (French passage,
German claim): the passage says the initiative demands a ban on importing
food that contains synthetic pesticides or was produced with them, which is
the claim.

No wrong answer came from a failed call: run 1 had none, and its one
unreadable answer (a bare `1`, row 645) got the fallback label neutral, which
is its gold label.
