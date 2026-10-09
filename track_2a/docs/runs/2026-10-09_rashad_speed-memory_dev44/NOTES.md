### 2026-10-09, checks without a model, Part 7: speed and memory without the model (dev booklets, host and container)

- **Per booklet** (`scripts/speed_memory.py`, one fresh Python process per booklet, empty booklet cache; e5 model files present): 01:13 to about 01:50 UTC on the host (4 CPUs, 15 GB), then 02:00 to 02:20 inside the image with `--cpus 2 --memory 4g --memory-swap 4g --read-only --network none`. Files: `per_booklet_host.json`, `per_booklet_container.json`. The first 12 host booklets overlapped with other work on the machine: the 10 model loads above 2.4 s (up to 7.7 s) are all among them; from the 13th booklet on, at most 2.4 s.
- **End to end** (the real CLI on all 300 dev task A cases against `scripts/stub_llm.py`, which answers in milliseconds, so the times are the local steps; one process for all cases, as in a real run; empty booklet cache): host, then the image with the same limits, for `embed-e5-small` (today's default) and `section-route`. Peak memory: the child's `ru_maxrss` on the host, the container's cgroup peak (`memory.max_usage_in_bytes`) in the image. MB here means MiB.
- **Cold start**: the image started with one case (twice each), limits as above, wall time from `docker run` to exit. Driver log: `log.txt`. Summary of all numbers: `summary.json`.

**Per booklet (min / median / max over the 44 dev booklets), host → container:**

| Step | Host | Container (2 CPUs, 4 GB) |
|---|---|---|
| import of the pipeline | 0.18 / 0.19 / 0.28 s | 0.41 / 0.44 / 0.50 s |
| PDF to page texts (pypdf, no cache) | 0.44 / 1.15 / 2.87 s | 0.53 / 1.36 / 3.48 s |
| booklet parse (sections) | 0.005 / 0.02 / 0.06 s | 0.005 / 0.02 / 0.07 s |
| e5 model load | 1.67 / 1.87 / 7.70 s | 1.75 / 1.85 / 2.07 s |
| embed the whole booklet (first embed-e5-small case) | 1.6 / 7.3 / 21.3 s | 3.0 / 13.8 / 44.8 s |
| a later embed-e5-small case (claim only) | 0.008 / 0.013 / 0.079 s | 0.009 / 0.025 / 0.064 s |
| slowest section-route case of the booklet | 0.005 / 0.04 / 25.4 s | 0.005 / 0.05 / 34.0 s |
| peak memory after embedding | 1,197 / 1,640 / 2,868 MB | 1,190 / 1,616 / 2,871 MB |

- Slowest whole-booklet embeddings: 2021-06-13 (144 pages; fr 44.8 s, it 38.8 s, de 35.6 s in the container) and 2022-09-25 fr (37.3 s).
- Slowest routed cases: v1.1-row-500-A, 782, 580, 904 (law parts of 385 to 636 paragraphs, 79k to 136k characters, all embedded to keep the 8 most similar): 29 to 34 s in the container. These are the same four cases that were slowest in E5 (16 to 20 s there, on the host).
- Peak memory is reached when the e5 model embeds a whole booklet or a long part (the model alone: about 1.2 GiB); the highest, 2,871 MiB (2.8 GiB), is 2021-06-13 fr, 70 % of the 4 GiB limit.

**End to end, 300 dev task A cases (local steps only):**

| | Host total | Host median / p95 / max per case | Container total | Container median / p95 / max per case | Peak memory host / container |
|---|---|---|---|---|---|
| `embed-e5-small` | 412 s | 0.02 / 10.4 / 21.6 s | 786 s | 0.06 / 19.3 / 44.4 s | 1,853 / 1,800 MB |
| `section-route` | 170 s | 0.03 / 2.3 / 14.9 s | 287 s | 0.04 / 3.7 / 31.9 s | 2,809 / 2,763 MB |

- Slowest embed-e5-small cases (container): v1.1-row-31-A 44.4 s, 367 40.1 s, 94 38.3 s, 5 37.9 s, 154 35.0 s: each is the first case of a large booklet, which pays for embedding the whole booklet.
- Slowest section-route cases (container): v1.1-row-500-A 31.9 s, 782 31.6 s, 580 27.2 s, 904 26.9 s (long law parts), 1383 18.4 s (the one fallback case: it embeds the whole booklet).
- No case failed or fell back except section-route's one known fallback (v1.1-row-1383-A).

**Cold start in the container (one case, `docker run` to exit, twice):** task B 0.96 s / 0.96 s (31 MB); task A with `embed-e5-small` 27.1 s / 26.3 s (case time 25.9 s / 25.0 s: PDF, model load and the whole 88-page booklet; 1,459 MB); task A with `section-route` 3.0 s / 2.9 s (case 2.1 s / 2.0 s: the routed part is short, so no model is loaded; 37 MB).

**Proposal measured: length-sorted batches** (`scripts/embed_batching_check.py`, host, 02:26 UTC; `embed_batching.json`). The pipeline's `E5Embedder` pads each batch of 32 to its longest text; a law part mixes clause lines of a few words with paragraphs of 1,000 characters. Embedding the same paragraphs sorted by length (then put back in order) took 6.7 s instead of 14.9 s (v1.1-row-500-A), 6.2 instead of 14.5 (782), 4.3 instead of 12.6 (580), 5.6 instead of 12.3 (904): 2.2 to 2.9 times faster, with identical vectors (largest difference 0.0) and the same 8 paragraphs kept. Not applied: `src/contexts/` belongs to another session (proposal P6 in `docs/checks_no_model.md`). The whole-booklet embedding of embed-e5-small could gain the same way (its chunks vary less in length; not measured).
