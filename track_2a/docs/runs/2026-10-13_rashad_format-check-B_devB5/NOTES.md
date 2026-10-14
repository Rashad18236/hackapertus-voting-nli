### Format check of step 2's five arms (session 13): B1 void

Five dev task B cases (rows 500, 501, 994 with long references, 2 and 4), five arms interleaved, 1 request per second,
22:35 UTC, one backend (blablador). Checked by `fmt_check_b.py` (session scratchpad) and by reading the raw answers:
every answer one JSON object, fields in the schema's order, label readable.

- today, B2 (`v7-unrelated`), B3 (`cut4-tf`), B4 (`v7-claim-first`): 5 of 5 readable, fields in order.
- **B1 (`v7-same-ballot`): void.** Row 2's answer stops `passage_ballot` at the schema's `maxLength` of 80 characters
  and then produces only whitespace until the 160-token budget runs out: no complete JSON object. The instruction marks
  an arm with unreadable answers void; the schema is the instruction's and is not changed, so B1 and B1+B3 are not run.
- B1's other 4 answers: claim_ballot is written in the reference's language in 3 of 4 (row 500, an Italian reference,
  gets a German claim_ballot). Row 500 also shows that B1's label does not follow its own field: `same_ballot` false,
  label 2 (gold 1); Python reads the label as given and never checks it against `same_ballot`.
