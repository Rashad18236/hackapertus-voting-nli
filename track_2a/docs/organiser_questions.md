# Questions for the organisers (Hack Apertus, track 2A)

Ready to post. Short answers are enough; each one changes a setting or a line in our report.

**Evidence (task A)**

1. Which page does the official run check for an evidence item: (a) the page the quoted text is on, (b) any page of
   the gold passage, or (c) the first page of the gold passage? The starter's `evaluate.py` says pages are "not
   checked yet".
2. Does evidence returned with a neutral answer count in any way (credit, penalty, or ignored)?
3. Are evidence items beyond the first five ignored, and does an extra item that does not match the gold passage
   cost anything?

**Evaluation run**

4. On what hardware does the container run (CPU count and type, memory limit)? Local time T depends on it.
5. Which server and model variant answer at evaluation: CSCS or Public AI, and which `swiss-ai/Apertus-v1.5-...`
   model (8B instruct or another)?
6. Do output tokens (and reasoning tokens, if any) count in K, or input tokens only?
7. Is there a rate limit on the team key at evaluation (requests per second or per minute)? Are retries after an
   HTTP 429 or 5xx counted in K?

**Thresholds**

8. Is the task B minimum Macro-F1 0.70 (starter repository, commit `5e695772`) or 0.75 (Q&A slides of 8 October)?
