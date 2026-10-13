### Cost of model S through the image: task A's local time at 0.3 s per request 0.145 → 0.018 s per case, peak memory 2,286 → 200 MiB (session 12 step 1c)

**Image** `ghcr.io/rashad18236/hackapertus-voting-nli:sha-c3cbaac54b15` (built by the publish workflow from `c3cbaac`;
it holds e5 and model S's 256-dimension table). `scripts/local_time.py`: 2 CPUs pinned to CPUs 2-3, 4 GB, the fake
model replaying the session 11 reference's answers after 1.0, 0.3 or 0.1 s per request (requests the table does not
know, such as those whose paragraphs S chose, get the fake model's fixed answer; the local work is the same), all 300
dev cases of each task. Arms in alternating order; a second round at 0.3 s in the other order.

- **today**: the defaults (e5 ranks long parts and the fallback's chunks; task B selector T);
- **S**: model S everywhere: task A `--ranker S` (long parts, fallback, vote names by meaning); task B `--context-b
  cut4-r --ranker S` (B-R, which failed step 3: it is measured here only for its cost).

| Task | Model latency per request | today: local s per case | S: local s per case | Longest gap today / S (s) | Peak memory today / S (MiB) |
|---|---|---|---|---|---|
| A | 1.0 s | 0.0174 | 0.0159 | 0.016 / 0.013 | 2283 / 201 |
| A | 0.3 s | 0.1621 | 0.0178 | 13.49 / 0.015 | 2287 / 203 |
| A | 0.1 s | 0.3645 | 0.0430 | 14.956 / 1.0 | 2286 / 200 |
| A | 0.3 s (round 2, other order) | 0.1267 | 0.0183 | 13.834 / 0.016 | |
| B | 1.0 s | 0.0077 | 0.0085 | 0.014 / 0.014 | 1164 / 82 |
| B | 0.3 s | 0.0104 | 0.0069 | 0.027 / 0.013 | 1168 / 82 |
| B | 0.1 s | 0.1632 | 0.0082 | 1.037 / 0.027 | 1164 / 82 |
| B | 0.3 s (round 2, other order) | 0.0106 | 0.0068 | 0.02 / 0.013 | |

Means of the two rounds at 0.3 s: task A today 0.144, S 0.018 s per case; task B today 0.0105, S 0.0069. At 1.0 s per
request everything hides behind the requests in both arms; at 0.3 and 0.1 s e5's embedding of long parts (and of the
whole booklet for the fallback) shows, and S removes it: the longest gap between two requests falls from 13.5 s to
under a second. Peak memory (the container's cgroup maximum, page cache included) falls from 2,286 to about 200 MiB
for task A and from 1,164 to 82 MiB for task B, because onnxruntime and e5 are never loaded.

**S RULE (c)** (local time at 1.0 and 0.3 s at most today's + 0.005 s): **passes for task A** (1.0 s: 0.0159 against
0.0174; 0.3 s: 0.018 against 0.144).
