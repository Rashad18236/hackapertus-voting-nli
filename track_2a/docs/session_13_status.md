# Session 13 status

One line per event, UTC. If the session is restarted with "continue", work goes on from "Next".

- **Branch:** `rashad/session-13` from `main` at `c85a119` (draft pull request, never merged, no tag).
- **Clock:** experiments stop on Wednesday 14 October at 08:00 UTC; everything pushed by 09:00 UTC.
- **Decisions:** `docs/decisions/2026-10-13-1956_rashad_session-13.md`.
- **Replay reference for G1/G2:** `docs/runs/2026-10-13_rashad_prompt-snapshot-final-s12_devAB-valA`.

## Done

- (19:56 Tue) The instruction ends with "END OF SESSION 13 INSTRUCTION": complete.
- (19:57) Step 0: PR #20 checked: open, `mergeable_state` clean, head `668114f`, all four checks green (tests, image,
  publish, pull-and-run). It was a draft, which GitHub refuses to merge; marked ready for review, then merged with a
  merge commit: `main` = `c85a119` (branch kept).
- (19:58) Step 0: `origin/kaan/robustness-experiments` is an ancestor of `origin/main`; PR #19 closed with the comment
  "Contained in main via PR #20 (merged kaan/robustness-experiments in session 12)."
- (19:59) Step 0: publish-image on `main` (run 74, `c85a119`) succeeded: tags `latest` and `sha-c85a119b409a`.
  `origin/main` contains `668114f`.
- (20:00) Branch `rashad/session-13` from `origin/main`; publish workflow builds `session-13`; CLAUDE.md's current
  stage is session 13 (session 12 "merged as PR #20").

- (20:05) Step 1 code: prompts A1–A5 (`--prompt-a`), A6 (`--second-look-a6`), all off; pytest 332 passed; G1/G2 pass.
- (20:08) Step 1 format check (`docs/runs/2026-10-13_rashad_format-check-A_devA5`): all seven arms readable, fields
  in order; no arm void.
- (20:09) Step 1 dev run started (`docs/runs/2026-10-13_rashad_prompts-A_devA300-ontopic46`, 346 cases, 7 arms).
- (20:16) Step 2 code: prompts B1, B2, B4 (`--prompt-b v7-*`), B3 (`--context-b cut4-tf`), all off; G1/G2 pass.
  B3 offline (`docs/runs/2026-10-13_rashad_b3-picks_offline`): 383 of 539 long references (71 %) change a pick:
  B3 is an arm.
- (20:25) Step 3 code: H (`--evidence-hedge-a`, off); step 3 offline scoring started. Step 5:
  `docs/organiser_questions.md` written.
- (20:26) Step 4 groundwork: `scripts/error_types.py` offline part on session 12's val task A errors: 23 errors,
  13 reading, 10 routing (gold passage not in what Apertus read); of the 15 answered neutral, 9 reading, 6 routing.

- (20:30) G1/G2 with the H code (off): pass. With H on: G1 identical, 0 labels differ, evidence differs in 414 dev
  and val cases (as rebuilt offline).
- (20:36) **Step 3 done: H passes its rule** (`docs/runs/2026-10-13_rashad_evidence-pages_offline`): rule 3 (first
  gold page) dev 116 → 119, val 223 → 236, probe 44 → 46; text hit dev 197 → 198; nothing worse. Joins the combination.
  Rule 3 would cost about 40 % of today's evidence score (passages often start a page before the cited paragraph).

- (20:45) G1 with the default ranker set to S: 0 of 300 dev task B requests change (74 task A requests do): step 6
  runs on val task A only (decisions file). `scripts/prompt_snapshot.py` replays A6's second look (for G1/G2 if A6 is
  adopted).

- (21:38) Step 1 dev run done (`docs/runs/2026-10-13_rashad_prompts-A_devA300-ontopic46`, one backend): dev Macro-F1
  today 0.983, A1 0.902, A2 0.973, A3 0.980, A4 0.964, A5 0.983, today+A6 0.987; on-topic neutral 32 / 13 / 27 / 19 / 28
  / 25 / 30 of 46. **No arm passes its dev conditions** (A5 and A6 fail (g), the others (b), (d) or (e)).
- (21:39) Offline error typing (`docs/runs/2026-10-13_rashad_error-types_valAB`, 31 calls): task A reading errors
  direction/negation 6, scope 5, number/date 2; task B number/date 6, other ballot/topic 6, scope 4, direction 1, other 1.
- (21:40) Step 1 val run started (`docs/runs/2026-10-13_rashad_prompts-A_valA580`: today, A5, A3, today+A6), for the
  report only (which of the 15 val errors each arm fixes).

- (22:34) Step 1 val run done (report only): today 0.959, A5 0.971, A3 0.970, today+A6 0.973 (9 fixes, 1 break); of
  session 12's 15 val errors answered neutral they fix 7, 9 and 8. **Step 1 adopts nothing** (dev conditions).
- (22:35) Step 2 format check (`docs/runs/2026-10-13_rashad_format-check-B_devB5`): **B1 void** (one answer cut at
  `passage_ballot`'s 80 characters, then whitespace until the budget ran out: unreadable); today, B2, B3, B4 readable.
- (22:35) Step 2 dev run started (`docs/runs/2026-10-13_rashad_prompts-B_devB300`: today, B2, B3, B4).

- (23:04) Step 2 dev run done (`docs/runs/2026-10-13_rashad_prompts-B_devB300`): today 0.987, B2 0.983 (not ruled
  out), B3 0.980 (fails b), B4 0.980 (fails b, d, e: 5 unreadable).
- (23:04) Step 2 val run started (`docs/runs/2026-10-13_rashad_prompts-B_valB580`: today, B2, B3); step 6 queued after
  it (val task A, today and `--ranker S`).
- (23:06) Val local time (step 6): task A today 0.0091 / 0.0088 s, S 0.0073 / 0.0071 s per case at 1.0 / 0.3 s per
  request (medians of three).

- (23:37) Step 2 val run done (`docs/runs/2026-10-13_rashad_prompts-B_valB580`): today 0.968, B2 0.974 (fixes 8 of
  the 9; fails (c) p = 0.30 and (e) 2 unreadable vs 1), B3 0.966. **Step 2 adopts nothing.**
- (23:37) Step 6 started (`docs/runs/2026-10-13_rashad_S-val_valA580`: val task A, today and `--ranker S`).

- (00:00) Step 6 done (`docs/runs/2026-10-13_rashad_S-val_valA580`): val task A 0.961 → 0.969 (6 fixes, 1 break),
  evidence 0.963 → 0.968; REF SCORE 0.9243 / 0.9166 → 0.9269 / 0.9192 at 1.0 / 0.3 s: **S passes the S RULE.**
- (00:00) H is the default (commit `b634ac9`; G1 identical, G2 only evidence).
- (00:01) Combination run started (`docs/runs/2026-10-14_rashad_combination-H-S_valA580`: today against H+S, val task A).
- (00:08) S as the default in the working tree: G1 changes only the 74 task A requests of long parts, G2 labels only
  there; 346 tests pass.

- (00:23) Combination (`docs/runs/2026-10-14_rashad_combination-H-S_valA580`): H+S 0.969 against 0.959 on val task A,
  equal to S alone: kept. S becomes the default (commit `54032b4`; e5 stays for task B).
- (00:25) Final image `sha-54032b4a7970` (also `session-13`) pulled; final runs started.
- (00:57) Memory grid of the final image (`docs/runs/2026-10-14_rashad_memory-grid-final-s13_grid24`): every
  response at every limit; task A peak 2,287 → 206 MiB; image size unchanged (2,216 MB).
- (01:01) Final runs done (`docs/runs/2026-10-14_rashad_final-s13_*`, one backend, 0 failed calls): dev A 0.973 /
  0.985, B 0.987; val A 0.969 / 0.965, B 0.968; probe A 0.981 / 0.985, B 0.977; Python wrote 1 of 2,128 labels.
- (01:03) `latest` pulls without a login: digest `sha256:a6213d70ea55…`, the same image as `sha-c85a119b409a`
  (`main` = `c85a119`).

- (01:16) The worker process restarted: dockerd and the local-time measurement were lost; the instruction arrived
  again, identical (nothing repeated). (01:17) dockerd restarted; local time of the final image restarted from scratch.

- (02:05) Local time of the final image and REF SCORE: dev 0.915 / 0.911, val 0.917 / 0.912, probe 0.903 / 0.901 at
  1.0 / 0.3 s per request; task A dev local time 0.016 / 0.017 / 0.025 s at 1.0 / 0.3 / 0.1 s.
- (02:15) Reports, technical report (section 4, PDF 6 pages), CLAUDE.md, README; self-checks; pushed; PR description.

## Running

- Nothing. Session 13 is finished; the pull request stays a draft (never merged, no tag).

## Next

- For the team: A6 (val 0.973 vs 0.959, misses its rule by one on-topic case), B2 (val 0.974 vs 0.968, removes the
  targeted task B error, fails on breaks and one unreadable answer), and task A's one-lane limit below 2.5 GiB (set for
  e5; with model S a second lane would fit). See the session report.
