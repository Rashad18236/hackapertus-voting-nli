### Smoke test of Apertus v1.5 70B (session 15b, step 1): every 70B call refused with HTTP 429

**Cases:** the last 3 dev task A and the last 3 dev task B cases (rows 1477, 1478, 1481), through
`scripts/paired_run.py` (the CLI's code in-process) with `--call-log`, 1 request per second, 10:36 to 10:46 UTC. Arms:
`70B` (`{"name": "70B", "model": "swiss-ai/apertus-v1.5-70b"}`: `MODEL` set for the arm's calls, nothing else changed)
and `8B` (the final defaults; a check that the arm switch sends the right model).

**Result:** all 6 70B calls failed: 3 attempts each (the CLI's retries for HTTP 429), every attempt answered after about
26 s with HTTP 429 ("litellm.RateLimitError … 429 Too Many Requests … Received Model Group=swiss-ai/apertus-v1.5-70b,
Available Model Group Fallbacks=None"); 18 HTTP 429 answers. The 6 70B responses are the neutral fallback (Python's
label). The 8B arm answered all 6 in 1.3–1.7 s per call; every 8B response body names `swiss-ai/apertus-v1.5-8b`
(`8B/calls.jsonl`), so the arm switch sends what it should.

**Probes** (`probes.jsonl`, `probe.py` in the scratchpad: one minimal request to `swiss-ai/apertus-v1.5-70b`, 8 tokens,
one attempt) at 10:47, 11:02 and 11:17 UTC: HTTP 429 after 27.0, 27.2 and 26.0 s. With the smoke test, 9 of 9 calls
(21 HTTP requests) refused over 41 minutes: the 70B was not reachable, and the interleaved run of step 2 did not run
(decisions file).
