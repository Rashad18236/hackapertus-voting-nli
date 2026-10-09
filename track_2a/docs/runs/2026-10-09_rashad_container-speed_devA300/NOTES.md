### 2026-10-09, session 8 change B: length-sorted embedding batches, speed and memory in the container (no model calls)

- `scripts/container_speed.sh <dir>` (from `track_2a/`): the 300 dev task A cases with the default settings (section-route) in one process, inside the image `hackapertus-voting-nli` (built 2026-10-09 01:06 UTC by the checks session; Dockerfile unchanged since) with `--cpus 2 --memory 4g --memory-swap 4g --read-only --tmpfs /tmp`, data read-only, an internal Docker network without internet, and the fake model in a second container. The working tree's `src/` is mounted over `/app/src`, so each run measures the code as it was then. Empty booklet cache. Times: each case's `inference_time_ms` (local steps only; the fake model answers in milliseconds); total wall time of the CLI; peak memory from the container's cgroup (`memory.max_usage_in_bytes`, cgroup v1). The machine (4 CPUs, 15 GB) ran nothing else during the three runs.
- `before`: code at `72cf03a` (after change A). `B32`: `E5Embedder.embed` batches the texts sorted by length, then puts the vectors back in order, batch size 32. `B16`: the same with batch size 16.

| | Total wall time | Median / p95 / slowest case | Peak memory | Five slowest cases |
|---|---|---|---|---|
| before | 364.9 s | 0.04 / 4.15 / 51.2 s | 3,287 MiB | row 9 51.2 s, 782 35.0, 500 33.8, 580 29.5, 904 28.2 |
| sorted, batch 32 | 248.4 s | 0.04 / 3.63 / 20.9 s | 2,764 MiB | row 1383 20.9 s, 500 17.7, 782 16.9, 904 14.7, 580 12.1 |
| **sorted, batch 16 (kept)** | **228.5 s** | 0.05 / **3.21** / **17.6 s** | **2,254 MiB** | row 1383 17.6 s, 500 17.3, 782 16.9, 904 14.5, 580 10.8 |

- The long law parts (rows 500, 782, 580, 904: 385 to 636 paragraphs) take about half as long; row 1383 is the one dev case that falls back to embed-e5-small and embeds a whole booklet; row 9 (routed to a detail part, the fourth case of the run) took 51.2 s before and is no longer among the slowest.
- Batch size 16 was kept by the rule set for it: selections identical (below), peak memory lower (2,254 against 2,764 MiB), total time at most 10 % worse (it was 8 % better).
- Vectors and selections (`scripts/embed_equivalence.py`, host; files `embed_equivalence_B32.json`, `embed_equivalence_B16.json`): the "passage:" vectors of every chunk of the 45 dev and val booklets and the 880 query vectors are identical to the code before change B (largest absolute difference 0.0, both batch sizes), and embed-e5-small selects the same 8 chunks in all 880 dev and val task A cases. The host times in those files (old 803.6 s, new 328 to 330 s for all booklets) are not a fair comparison: the old run overlapped other work on the machine.
- The earlier measurement of the checks session (same image, same limits, code before session 7's merge was complete) gave 287 s total and a peak of 2,763 MiB for section-route; the "before" run here is slower and higher, which this note does not explain; only the three runs here compare with each other.
