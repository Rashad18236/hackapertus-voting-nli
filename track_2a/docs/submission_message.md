Abstimmungsbüchlein Check (Bissegger & Bayraktar), Track 2A — OST.

Image: ghcr.io/rashad18236/hackapertus-voting-nli:latest, run with the documented command
(`--input /data/cases.jsonl --output /output/predictions.jsonl`); task A and task B run in separate containers. The
final commit on main is tagged `submission`.

Model: the solution calls swiss-ai/Apertus-v1.5-8B only, through BASE_URL (the 70B was listed on the public endpoint
but unreachable on 15 October, so it was not used or measured). Local models baked into the image, embedding only
(they choose what Apertus reads, never a label): intfloat/multilingual-e5-small (MIT) and
sentence-transformers/static-similarity-mrl-multilingual-v1 (Apache-2.0); both are documented in the technical report. The image resolves the
model id from BASE_URL/models if the default name (swiss-ai/Apertus-v1.5-8B) is refused; MODEL can override it.

Sealed test dates (2020-02-09, 2022-02-13, 2022-05-15), run once after the freeze: task A Macro-F1 0.989 (evidence
0.975), task B 0.960 (technical report, section 1). The questions we posted on Discord are in
track_2a/docs/organiser_questions.md.
