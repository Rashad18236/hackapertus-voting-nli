# Session 15 status

One line per event, UTC. If the session is restarted with "continue", work goes on from "Next".

- **Branch:** `rashad/session-15` from `main` at `4f19500` (draft pull request, never merged, no tag).
- **Clock:** experiments stop on Thursday 15 October at 02:00 UTC; everything pushed by 03:00 UTC.
- **Decisions:** `docs/decisions/2026-10-14-1313_rashad_session-15.md`.
- **Replay reference for G1/G2:** `docs/runs/2026-10-14_rashad_prompt-snapshot-final-s14_devAB-valA`.

## Done

- (13:13 Wed) The instruction ends with "END OF SESSION 15 INSTRUCTION": complete. dockerd restarted (container
  restarted).
- (13:15) Step 0: PR #22 checked: open, draft, `mergeable_state` clean, head `ec7a6c1`, all four checks green. Marked
  ready (second attempt; the first hit a connection reset), merged with a merge commit: `main` = `4f19500` (branch kept).
  `origin/main` contains `ec7a6c1`.
- (13:16) Branch `rashad/session-15` from `origin/main`; the publish workflow also builds `session-15`.
- (13:22) Step 1: `second_look_a6 = True` by default; five tests that assumed A6 off say so explicitly; pytest 348
  passed, 1 skipped. G1/G2 against the session 14 reference: first requests and paths identical in all 1,180 cases;
  A6's second looks added in 15 cases (dev 5, val 10); G2 0 differences (stub second looks unreadable).
- (13:24) Step 0: publish-image on `main` (run 92) succeeded: `latest` and `sha-4f1950002ca0`. `latest` pulls without a
  login: digest `sha256:e3e61af166c0…`, the same image as `sha-4f1950002ca0`, revision label `4f19500` = `main`.
- (13:29) Step 2 code: A6b (`--second-look-a6-prompt A-v6-second-look-b`, off); test. Decisions for steps 0–2 written; G1/G2 with
  the A6b code identical to step 1's. Technical report: A6's role row, its negative-results row removed, the team's sentence in Limitations.
- (13:30) Step 2 run started (`docs/runs/2026-10-14_rashad_A6b_devA300-valA580-probeA94-ontopic46`: today (A6), A6b;
  1,020 cases, CPUs 0–1, 1 request per second).
- (13:36) Steps 3–4 code: `v7-same-ballot-f` (B1 with the format fixed) and B6 (`--second-look-b6`), both off; tests;
  pytest 356 passed, 1 skipped; G1/G2 identical to step 1's snapshot. Decisions for steps 3 and 4 written.
- (14:10) Step 2 run done (`docs/runs/2026-10-14_rashad_A6b_devA300-valA580-probeA94-ontopic46`, one backend, 0 failed
  calls, first answers shared): A6 and A6b gave the same finding in all 19 second looks; dev 0.977, val 0.981, probe
  0.990 for both; on-topic flips 3 and 3 (rows 85, 232, 1026). **A6b fails (2): not adopted.** Session 14's four
  still-wrong val cases get no second look (their first answer cites no paragraph).
- (14:11) Step 3 format check (`docs/runs/2026-10-14_rashad_format-check-B1f_devB10`): all 10 B1f answers readable,
  fields in order (6 ballot names cut at 40 characters, still closed): not void.
- (14:12) Step 3 dev run started (`docs/runs/2026-10-14_rashad_B1f_devB300`: today, B1f; 300 task B cases).

- (14:36) Step 3 dev run done (`docs/runs/2026-10-14_rashad_B1f_devB300`, one backend, 0 failed calls): B1f 0.892
  against 0.987, 19 unreadable, +13.1 % input tokens, 2 fixes / 30 breaks. **B1f fails (b), (d), (e) on dev: no val
  run, not adopted.** Gold neutral answered contradiction 20 (6 same / 14 cross language) against 1; 21 of 27 readable
  sampled `claim_ballot` values in the reference's language.
- (14:38) Step 4 dev run started (`docs/runs/2026-10-14_rashad_B6_devB300`: today, today+B6; 300 task B cases).

- (14:53) Step 4 dev run done (`docs/runs/2026-10-14_rashad_B6_devB300`, one backend, 0 failed calls, first answers
  shared): B6 0.970 against 0.987, +7.0 % input tokens, 0 unreadable; 99 second looks (33 per 100 cases), 7 changed
  (2 same / 5 cross language), 1 fix / 6 breaks. **B6 fails (b), (d) on dev: no val run, not adopted.** The 6 breaks
  are claims that misstate the reference's own ballot, answered "not about the ballot".
- (15:00) No default changed beyond step 1: no combination run; final defaults = S, H, two lanes, A6 on.
  `scripts/stability.py` (step 5) and the B6 block of `scripts/arm_table.py` added; step 5's plan in the decisions file.

- (14:58) Branch image of `7ae78ad` published (`sha-7ae78ad87cfd` = `session-15`, digest `sha256:a89c507afff1…`) and
  pulled.
- (15:00) One queue for step 5 and the final runs (decisions file): stability run 1 at 15:23 → final val1160 →
  stability run 2 (≥ 30 min after run 1) → final probe188 → stability run 3 (≥ 30 min after run 2) → final dev600
  (≥ 30 min after run 3), all through `sha-7ae78ad87cfd`.

- (15:23) Stability run 1 started (task A 15:23–15:34: 0.977, evidence 0.990).
- (15:33) Memory grid of the final image (`docs/runs/2026-10-14_rashad_memory-grid-final-s15_grid24`, CPUs 2–3, no
  model calls): every response at every limit (4g … 512m, 2 and 1 CPUs, both tasks); task A two lanes with 2 CPUs at
  every limit, peak 206–242 MiB. Its task A local time is higher than session 14's grid; the same image with A6 on and
  off gives 0.084 / 0.077 against 0.077 / 0.092 s per case at 0.1 s per request: not A6.

- (15:40) Stability run 1 done: task A 0.977 (evidence 0.990), task B 0.987; one backend, 0 cache hits.
- (16:07) Final val1160 done (`docs/runs/2026-10-15_rashad_final-s15_val1160`): task A 0.981 (evidence 0.988), task B
  0.968 (1 unreadable).
- (16:28) Stability run 2 done: every one of the 600 labels equals run 1's (A 0.977, B 0.987).
- (16:32) Final probe188 done: task A 0.990 (evidence 1.000), task B 0.977.

- (17:11) Stability run 3 done. **Step 5: 0 of 600 labels changed over the three runs** (A 0.9767 [0.958, 0.991], B
  0.9867 [0.973, 0.997] each time; one backend, 0 cache hits); 10 task A answers cite other paragraphs and 20 task B
  answers differ in trailing text, labels equal (`stability.json` in run 3's folder).

- (17:56) Final dev600 done (`docs/runs/2026-10-15_rashad_final-s15_dev600`): task A 0.977 (evidence 0.990), task B
  0.987; the same 600 labels as the stability runs. All model calls of the session are done. `check_format.py`: all
  six final prediction files pass; Python wrote 1 of 1,948 final labels (val task B).
- (18:07) New replay reference `docs/runs/2026-10-15_rashad_prompt-snapshot-final-s15_devAB-valA` (two passes): all
  1,198 calls replayed (1,180 answers, 15 A6 second looks, 3 translations); replay against the final runs: 0 label
  and 0 evidence differences on 1,180 cases. `scripts/local_time.py`'s default table now points to it.
- (18:08) Self-checks 17 of 17 pass.

- (19:08) Local time of the final image (CPUs 2–3, new reference's table): dev task A 0.020 / 0.027 / 0.062 s, task B
  0.012 / 0.021 / 0.172 s at 1.0 / 0.3 / 0.1 s (dev 1.0 and 0.3 s: mean of two); val A 0.010 / 0.010, B 0.009 / 0.010 s;
  probe A 0.039 / 0.035, B 0.020 / 0.019 s. REF SCORE dev 0.904 / 0.893, val 0.908 / 0.907, probe 0.901 / 0.902.
- (19:15) Technical report updated (summary table, role table, negative results, endpoint-drift paragraph, Limitations,
  A6 in section 3.1); PDF 6 pages. Session report written. pytest 356 passed, 1 skipped (pypdf 6.17.0);
  `build_docs.py --check` passes.

- (19:18) The branch's workflows on `734f188` are green: tests, image, publish, pull-and-run. PR #23's title and
  description updated (draft, not merged, no tag).

## Closed

Every step of the instruction is done; nothing was dropped for time. Final defaults: model S, hedge H, two lanes, A6 on
(published image `sha-7ae78ad87cfd`). Report: `docs/session_15_report.md`.
