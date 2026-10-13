### Fallback levels on val, forced (session 11 step 2, confirmation): neither VW nor BW passes the FALLBACK RULE

The confirmation of `2026-10-12_rashad_fallbacks_devA300` on the balanced val sample (300 task A cases), with the
same forced situations (`scripts/paired_run.py`, arm field `force`): "no part" (the router returns nothing) for
today's fallback and VW, "no vote" (the vote match fails) for BW. Interleaved, 1 request per second, 21:22 to
22:18 UTC; all 900 answers from one backend (blablador `vllm-0.23.1rc1`). The dev run's today-routed arm is not
repeated here: val only confirms.

| Arm | Macro-F1 | Evidence (of 204) | F1 ent / neu / con | Input + output tokens per case | p95 time | Fixes / breaks vs today's fallback |
|---|---|---|---|---|---|---|
| today-fallback-nopart (embed-e5-small) | 0.875 | 0.593 (121) | 0.907 / 0.899 / 0.819 | 1,827 + 15.8 | 18.6 s | |
| VW-nopart | 0.873 | 0.716 (146) | 0.924 / 0.877 / 0.819 | 1,079 + 14.4 | 11.8 s | 19 / 19 |
| BW-novote | 0.856 | 0.627 (128) | 0.910 / 0.837 / 0.821 | 951 + 14.5 | 17.5 s | 21 / 27 |

0 failed calls, 0 unreadable answers, 0 HTTP 429. One today's-fallback answer cited no valid page for a label 0/2
(no evidence item; the label stands).

**FALLBACK RULE** ("VW and BW each replace today's fallback in their situation if, forced on val, Macro-F1 is at
least 0.02 higher and evidence at least 0.05 higher than today's fallback, neither is lower on dev, and no routed
case changes"):

- **VW: fails.** Evidence +0.123 (passes), but Macro-F1 −0.002 (needs +0.02). On dev it was +0.028 / +0.094;
  19 fixes and 19 breaks on val. VW stays in the code, switched off (`--fallback-a vw`).
- **BW: fails.** Macro-F1 −0.019 and lower on dev too (−0.042). Stays off (`--fallback-a bw`).

Today's fallback (embed-e5-small) therefore stays in both situations, and no routed case can change. What VW would
have brought (−41 % input tokens and +0.12 evidence on fallback cases) is reported, not used. The probe run
"today against the new defaults" is not run: there are no new defaults.

Files: one folder per arm, `rule_check.json` (today-fallback-nopart as the reference), `paired_run.log`.
