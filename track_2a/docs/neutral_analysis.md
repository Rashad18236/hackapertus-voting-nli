# Neutral cases in task B (dev)

Written 2026-10-08 for session 2, step 1. Data: the 300 task B dev cases
(`data/dev/`), and the run `contract-v2-dev` (prompt `v2-label-only`), in
which 96 of the 99 neutral cases were predicted as contradiction.

## 1. Does `vote` name the claim's ballot or the reference's?

**The reference's.** In all 300 task B dev cases, for every label, `vote` is
exactly the first line of the reference text, which is the title of the
ballot the passage belongs to. (Check: normalised `vote` equals the first
line of `reference.text` in 102/102 entailment, 99/99 neutral, 99/99
contradiction cases.)

Consequence for task B: `vote` adds no information the model does not
already have, because the reference already starts with that title. It
cannot reveal that a neutral claim is about another ballot. **Run B (adding
the vote name) is therefore skipped.**

(For task A this is different: there `vote` is the only way to find the
reference's section in a booklet with several ballots.)

## 2. Are claim and reference from the same booklet, vote and language?

The dataset does not say where a neutral claim comes from, so we estimated
it. For every dev claim we searched all distinct reference passages *in the
claim's language* for the one sharing the largest share of the claim's words
(5+ letters), and took that passage's booklet (voting date).

- **Validation:** for entailment and contradiction cases, where the claim
  belongs to the reference's ballot by construction, this finds a passage
  from the reference's own booklet in **64 %** of cases (201 cases). The
  method is rough, but clearly better than chance (1 in 20 booklets).
- **Neutral cases:** the best match is in the reference's booklet in only
  **5 of 99** cases (5 %), and the same vote in about 1.

So neutral claims come almost entirely from **other booklets**, which means
other voting dates and other ballots. This matches the starter's own comment:
"Neutral rows pair the claim with an unrelated passage." Some neutral claims
may not come from any booklet at all; for example, a new SBB direct line
Bern–Zürich was never a federal ballot.

**Languages:** the dev split is balanced over the nine claim/reference
language pairs for every label (11 or 12 rows per label and pair), so
language does not distinguish neutral cases.

## 3. What the model does with them

We read 10 neutral cases that `v2-label-only` called contradiction (drawn
at random, seed 42). In **all 10**, the claim is about a subject the
reference does not mention at all:
- a COVID-19 law against vocational training;
- tenancy law against a CO2 tax;
- the Health insurance cost brake against an SBB rail link;
- the SSR licence fee against the AHV retirement age;
- and so on.

No case was subtle.

In plain words, the model seems to:

1. **Read the attribution as the claim.** Most claims, in every label, are
   framed as "According to the voting text / the committee / the Federal
   Council / the summary, X". When the reference does not say X, the model
   concludes that "the text says X" is false, and answers contradiction.
2. **Use "the Federal Council recommends no" as a refutation of anything.**
   Many references end with the authorities' recommendation, and the model
   treats it as contradicting unrelated claims about what the Federal Council
   supports.
3. **Never use "insufficient information".** It answered neutral only 6
   times in 300 cases, so the prompt's definition of neutral is
   not being applied.

The fix to try first (Run A, prompt `v3-topic-first`) is a decision rule:
first check whether the reference addresses the claim's subject at all; if
not, the answer is neutral. Missing information is never a contradiction.

## 4. Five examples (gold neutral, predicted contradiction)

| id | reference (title) | claim |
|---|---|---|
| v1.1-row-930-B (it→it) | Legge COVID-19 | Secondo il comitato, la riforma della formazione professionale dovrebbe essere approvata per modernizzare il sistema educativo svizzero. |
| v1.1-row-981-B (de→it) | Änderung des Obligationenrechts (Mietrecht: Untermiete) | Stando al testo di voto, dal 2025 la Svizzera ha introdotto una tassa sul carbonio per diminuire le emissioni di CO2 nel settore dei trasporti. |
| v1.1-row-656-B (de→de) | Volksinitiative «Für tiefere Prämien – Kostenbremse im Gesundheitswesen (Kostenbremse-Initiative)» | Laut dem Abstimmungstext soll die Einführung einer neuen SBB-Direktverbindung zwischen Bern und Zürich die durchschnittliche Reisezeit um 30 Minuten verkürzen. |
| v1.1-row-640-B (fr→de) | Initiative populaire « 200 francs, ça suffit ! (initiative SSR) » | Laut der Zusammenfassung soll das AHV-Rentenalter für Frauen und Männer auf 67 Jahre angehoben werden. |
| v1.1-row-510-B (it→de) | Iniziativa sulle cure infermieristiche | Der Bundesrat befürwortet, dass die Revision des Geldspielgesetzes in ihrer vorliegenden Form in Kraft tritt. |

Language pairs are written source→claim, as in the starter.
