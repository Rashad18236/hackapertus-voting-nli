### Session 17 verification: the model-name fallback through the published image, without MODEL

**What ran.** The `session-17` image (`ghcr.io/rashad18236/hackapertus-voting-nli@sha256:fe4324697372af91247c25a7f21c5b1c2ae6298c43b08ba424e2d22729ec43ae`,
revision `898776f`, pulled with an empty Docker configuration) with the organisers' command (`docker run --rm
--read-only --tmpfs /tmp ... --input /data/cases.jsonl --output /output/predictions.jsonl`, plus `--raw`), only this
sandbox's proxy flags, CPUs 0–1, `LLM_MIN_INTERVAL=1`, the real endpoint (Public AI). `BASE_URL` and `API_KEY` set,
**`MODEL` and `LLM_NAME` unset** and `.env` not mounted, so the image asked for its default name
`swiss-ai/Apertus-v1.5-8B`. Four containers, 20:01:41–20:03:14 UTC:

| Folder | Cases | Exit | "model name replaced" | Labels by Python | Same label as the session 15 final dev run |
|---|---|---|---|---|---|
| `examples/` | `examples/cases.jsonl` (1 A, 1 B) | 0 | 1 | 0 | 2 of 2 |
| `dev-A20/` | first 20 task A cases of `data/dev/cases.jsonl` | 0 | 1 | 0 | **20 of 20** |
| `dev-B20/` | first 20 task B cases | 0 | 1 | 0 | **20 of 20** |
| `examples-with-MODEL/` | the 2 example cases, `MODEL=swiss-ai/apertus-v1.5-8b` | 0 | 0 | 0 | 2 of 2 |

In each container without `MODEL`, the first request was refused with **HTTP 403** and the log says once: "The
endpoint refused the model name (HTTP 403); model name replaced by swiss-ai/apertus-v1.5-8b, listed by the endpoint,
for the rest of the run". That case made 2 requests (the refused one counts no tokens), every later case 1; every
answer names `swiss-ai/apertus-v1.5-8b` and came from one backend (blablador). With `MODEL` set: no refusal, no
replacement line. `scripts/check_format.py`: no errors, no warnings for all four files. The 40 dev labels equal
`docs/runs/2026-10-15_rashad_final-s15_dev600` for the same ids: no endpoint drift seen.

Gateway cache: `v1.1-row-2-A` (dev-A20) and `v1.1-row-9-B` (dev-B20) are the example cases, sent 14 to 60 s earlier
in `examples/`, so their identical requests were answered from the gateway's cache, as were both cases of
`examples-with-MODEL/`; every other answer is fresh. Tokens (input + output, all cases): examples 1,883 + 21, dev-A20
28,626 + 312, dev-B20 17,033 + 165.
