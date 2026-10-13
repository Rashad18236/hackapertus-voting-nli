### Step 4, a fast server: where task A's local time goes at 0.3 s per request, and three changes that halve it (session 11)

**Profile** (`single/today/d*.json` and `.phases.txt`; `src/timing.py` with `PROFILE_PHASES=1`; the image with 2 CPUs,
4 GB, fake model replaying the session 10 reference's answers). Today's defaults, all 300 dev task A cases:

| Model time per request | Local time per case | Time to the first request | Main process waiting for a case |
|---|---|---|---|
| 1.0 s | 0.017 s | 3.1 s | 2.2 s |
| 0.3 s | 0.225 s | 3.7 s | 63.9 s |
| 0.1 s | 0.426 s | 3.3 s | 124.5 s |

At 0.3 s per request the two lanes are busy all the time: per lane about 145–155 s of preparation for 90 s of
requests. Phase totals over both lanes: **PDF reading 107 s** (44 booklets, 2,624 pages, about 2.4 s per booklet),
**e5 embedding 177 s** (47 long parts, about 3.8 s each), e5 loading 4.6 s (once per lane), parsing 1.2 s. The main
process waited for a prepared case 25 times, 62 s in all. At 1.0 s per request the same work hides behind the
requests.

**Candidates** (each a switch in `src/`, G1/G2 decide whether answers stay identical):

- **light-first** (`pipeline.LIGHT_FIRST`): a lane first prepares every case that needs no embedding model (a case
  that would need it is put aside by `src/deferral.py`), then the others; the e5 model is loaded only when the
  first such case comes (no separate change was needed for "e5 loaded only when needed").
- **lazy pages** (`parse.LAZY_PAGES`): a page is read from the PDF when first asked for; the cache key is the PDF
  file's SHA-256 (no page needs reading to name the booklet); one PDF reader open per process. The parser still
  asks for 84 % of the pages (2,208 of 2,624).
- **SHARE_CPUS** (`pipeline.SHARE_CPUS`), found in the profile: two lanes embedding at once each started
  onnxruntime with every CPU, so 4 threads (which spin while idle) shared 2 CPUs; now each lane gets its share
  (1 thread under a 2-CPU limit; the vectors are the same for 1, 2 and 4 threads, session 10).
- no-spin (onnxruntime's `allow_spinning` off, 2 threads per lane), for comparison.
- Not built: shared reading of the first booklet (the time to the first request is 3.1 s, 0.010 s per case; the
  smallest booklet first would cut part of it), quantised e5 for task A (changes 50 of 75 cut selections, so it
  fails G1).

**Rounds at 0.3 s per request** (`rr1_runs/`, `rr2_runs/`; every variant once per round, beside a model run on the
other two CPUs, so single values vary by about ±0.015 s):

| Variant | Local time per case (rounds) | Mean |
|---|---|---|
| today | 0.184, 0.210, 0.218, 0.195 | 0.202 |
| light-first | 0.176, 0.178 | 0.177 |
| lazy pages | 0.173, 0.196 | 0.184 |
| light-first + lazy | 0.159, 0.153 | 0.156 |
| no-spin | 0.128, 0.131 | 0.129 |
| SHARE_CPUS | 0.113, 0.127, 0.135, 0.120 | 0.124 |
| light-first + SHARE_CPUS | 0.124, 0.116 | 0.120 |
| **light-first + lazy + SHARE_CPUS** | 0.101, 0.101 | **0.101** |

With all three, PDF reading falls to 58 s and embedding to 145 s over both lanes, and the main process waits 27 s
instead of 62 s.

**SAME-ANSWER RULE.** G1 and G2 pass on dev and val with all three switched on (every request, label and evidence
identical to the session 10 reference), and each lowers the local time: **all three adopted** (commit after this
folder). The target (≤ 0.05 s per case at 0.3 s) is **not reached**: what still takes the time is PDF reading
(about 1.3 s per booklet, pure Python in pypdf) and e5 embedding of long parts (about 3 s per part); both are done
once per booklet or part, and with a fast model they no longer hide behind the requests. The final image is
measured at 1.0, 0.3 and 0.1 s in FINISH.

Peak memory rose with the first version of lazy pages (2.58 GiB against 2.31 GiB: every booklet's PDF reader stayed
open); the adopted version keeps one reader per process. Memory is step 5.
