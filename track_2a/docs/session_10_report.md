# Session 10: score what the organisers score

2026-10-12 11:42 UTC to 2026-10-13 13:00 UTC, branch `rashad/session-10` from `main` at `42b2a3c` (draft pull
request #17, never merged, no tag), run unattended by Claude Code for Rashad. Decisions:
`docs/decisions/2026-10-12-1142_rashad_session-10.md`; status log: `docs/session_10_status.md`; the organisers'
formula and our REF SCORE: `docs/official_scoring.md`.

## In short

**Finished:** steps 0 to 8, the optional step 9 on dev, and FINISH. Nothing was dropped for time. The sealed test
dates were never run, parsed or opened; `data/test/`, the splits file and the scorer are unchanged; no key was
printed, logged or committed. Every label comes from an answer of Apertus; [[FALLBACKS_SHORT]]

**Local time and tokens per case, `main` → final** (local time: `scripts/local_time.py`, the image with 2 CPUs,
fake model replaying saved answers after 1.0 s / 0.3 s; tokens: input + output from real runs on dev):

[[BEFORE_AFTER_TABLE]]

**Defaults changed, each by its rule:**

| Change | Rule | Evidence | Commit |
|---|---|---|---|
| Cases prepared in background worker processes while a request is in flight; one kept connection; each booklet parsed once; ONNX threads = the CPU limit; `src/` compiled in the image (step 2) | same answers (G1, G2) and local time per case falls for both tasks | G1/G2 pass; A 0.803 → 0.015 s, B 0.985 → 0.008 s at 1.0 s per request | `628f5b0`, `150ae44` |
| Task B sends the whole reference again (no B-cut) (step 2) | B-cut against no cut under REF SCORE with measured times and tokens | mean S_B over both delays dev 0.827 vs 0.821, val 0.821 vs 0.817 | `83e7fab` |
| A vote name the title match cannot place is placed by meaning (e5, lead ≥ 0.04) (step 8) | G1 and G2 unchanged on dev and val | G1/G2 pass; swap test 182 of 264 right, 0 wrong | `6204a67` |
| Two worker processes ("lanes"), each owning whole booklets | same answers and local time | G1/G2 pass; task A at 0.3 s per request 0.316 → 0.206 s per case | `2509882` |

**Tried and not adopted:** P-short and P-short+K4 (task A, step 5; fail on dev), K4 (passes on dev, fails on
val), BP-short and BP-short+B-cut4 (task B; fail on dev), **B-cut4** (passes the TOKEN RULE on dev and val with −55 %
tokens but lowers REF SCORE through local time), CS and SL (step 6; fail the PAIRED RULE), B-U (step 9; adds output
tokens and local time). Step 7: without `response_format` 0 of 100 answers unreadable; nothing to change.

[[PROBE_SHORT]]

**The Python rule "neutral with a citation → contradiction"** (offline only, from today's saved answers; never in
`src/`): dev 0.9833 → 0.9834, val 0.9589 → 0.9728, on-topic neutral set 31 → 28 of 46 answered neutral (all 3 changes
wrong).

**Each version on the on-topic neutral set** (46 dev cases whose gold passage was removed; expected neutral;
indicative): today 31 of 46 answered neutral (0.674), CS 28 (0.609), SL 31 (0.674).

**Not verified:** the organisers' hardware, model server and its speed (local time depends on it: at 0.3 s per
request task A's PDF reading no longer hides behind the requests); the other teams' best values (REF SCORE uses
ours); whether their proxy counts "in flight" as our fake model does; a cold start of the freshly pulled image (the
first read of the 470 MB e5 file was slow on this sandbox's disk); the parser gap on one probe booklet
(`2025_09_28_fr`) is reported, not fixed.

[[DETAILS]]
