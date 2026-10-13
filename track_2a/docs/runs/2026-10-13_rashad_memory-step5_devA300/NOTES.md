### Step 5, memory: task A needed 3 GiB with 2 CPUs; one lane under 2.5 GiB brings it to 1.5 GiB (session 11)

**What holds the memory** (task A, dev, 2 CPUs, 4 GB; `before/A_c2_m4g.phases.txt` and an in-process probe): the
main process stays at 48 MiB (it only sends requests); each of the two lanes peaks at about 1.19 GiB. Of that,
**loading e5 peaks at 1.16 GiB** (the 470 MB ONNX file is read and its weights copied; 0.80 GiB once loaded),
onnxruntime's memory arena keeps the largest batch's buffers (+0.34 GiB after embedding long parts), page texts and
the parsed booklets are small (about 6 MB per booklet). With two lanes, two e5 copies: the container's peak is
2.29 GiB (cgroup, page cache included). Task B (whole reference, no e5) peaks at 49 MiB.

**Before** (`before/sweep.txt`; the image under `--memory` × `--cpus`, fake model at 0.1 s, a limit passes if all 300
responses are written with the labels of the 4g run; lower limits not run after a failure):

| | 4g | 3g | 2g | 1.5g | 1g |
|---|---|---|---|---|---|
| task A, 2 CPUs | ok (peak 2,285 MiB) | ok | **OOM** (exit 137, 24 responses missing) | — | — |
| task A, 1 CPU (one lane) | ok (1,193 MiB) | ok | ok | ok | OOM |
| task B, 2 CPUs | ok (49 MiB) | — | ok | ok | ok |

**Fixes tried at 2 CPUs** (`variants/`; local time per case at 0.1 s per request in brackets, today 0.29 s at 4g):

| Variant | 4g | 2g | 1.5g | 1g |
|---|---|---|---|---|
| arena off (`MEMORY_ARENA = False`), two lanes | ok, 1,992 MiB (0.348 s) | ok, 2,005 MiB (0.352 s) | ok (0.728 s) | OOM |
| arena off + batches of at most 4,096 tokens | ok, 2,033 MiB (0.331 s) | — | ok (0.698 s) | OOM |
| **one lane under 2.5 GiB** (`MEMORY_FOR_TWO_LANES`) | ok, two lanes (0.309 s) | **ok, 1,194 MiB (0.423 s)** | **ok, 1,195 MiB (0.421 s)** | OOM |
| all three | ok (0.352 s) | ok (0.492 s) | ok (0.495 s) | — |

**Adopted: one lane under a 2.5 GiB limit** (`src/pipeline.py`, `MEMORY_FOR_TWO_LANES = 2.5 GiB`). Under 2.5 GiB the
container now answers every case with the same labels at 2 GiB and at 1.5 GiB with 2 CPUs (the target was 2 GiB);
at 2.5 GiB and above nothing changes (two lanes, the same requests: G1/G2 pass, as the fake-model runs use no
limit). Not adopted: the arena off (it lowers the peak only to 2.0 GiB with two lanes, leaving 43 MiB of margin at
2 GiB, and costs 0.06 s per case at every limit) and token-bounded batches (no further gain); both stay in the code,
off. Not built: one e5 copy shared by both lanes, and dropping page texts (about 6 MB per booklet). 1 GiB stays out
of reach: loading e5 alone peaks at 1.16 GiB.
