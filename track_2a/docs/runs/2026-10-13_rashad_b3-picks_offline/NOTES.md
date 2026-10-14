### B3 offline: selector T with the reference's first line changes the picks of 71 % of long references (session 13, step 2)

`scripts/taskb_b3_picks.py` (no endpoint call; e5 locally): for every task B reference that today's rule cuts (over
3,000 characters and more than 4 paragraphs), the 4 paragraphs selector T keeps (e5 on each paragraph's first 300
characters) against the 4 that B3 keeps (`cut4-tf`: e5 on "<first line>: <the paragraph's first 300 characters>").

| Set | Long references | Pick changed |
|---|---|---|
| dev | 190 | 133 |
| val | 349 | 250 |
| together | 539 | **383 (71 %)** |

The instruction's bar is 10 %: **B3 is an arm** of the step 2 dev run.
