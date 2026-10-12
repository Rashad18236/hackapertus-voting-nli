# Academia Challenges

Submissions must use the Apertus model family.
For Track 2 this means that submitted solutions must be built with Apertus. Other open-weights models can be used to support development, e.g. as automatic judges during evaluation. Their role must be clearly described in the submission report.

💬 In case you have questions, join the conversation on Discord or send an email to “hello@hackapertus.ch”

## How it works
Pick from 5 academia challenges provided by Swiss academic institutions:

- **FHGR:** AI-Powered Job Interview Coach
- **OpenParlData:** Extracting Parliamentary Affairs from PDFs into One Common Structure
- **OST:** Multilingual Natural Language Inference over Swiss Official Voting Booklets
- **UZH:** Detecting Cross-Lingual Semantic Differences in Swiss Government Websites
- **ZHAW:** See It, Say It, Pick It: Vision-Language Grounding for a Real Robot Arm

The challenges incl. submission and judging criteria are described in our **Getting Started guide**:
https://hackapertus.notion.site/getting-started-guide-onlinehack

## Run it

Keep `track_2a/` as it is: don't rename it or move its files, just delete the
other track directories.

From the root of the project:

```bash
make run
```

Fill in the [Makefile](Makefile) so that it works on a clean checkout. It is
expected to run the project in a Docker container, since that is how the judges
will run it, without relying on anything already installed on your machine.

Requirements: `runtime, hardware, API keys, model weights`

### Our project: requirements and running it

- **Runtime:** Docker (the image is `linux/amd64`, Python 3.12). `make run` builds the image and answers
  `examples/cases.jsonl`; predictions go to `output/predictions.jsonl`.
- **Hardware:** CPU only, no GPU. Measured with 2 CPUs and 4 GB: the 300 dev task A cases take about 4 minutes
  of local work with the default context, peak memory about 2.2 GB (`docs/runs/2026-10-09_rashad_container-speed_devA300`).
  Since session 10 a worker process prepares the next cases while a request is in flight, so most of that work
  overlaps with the model's latency (`docs/session_10_report.md`).
- **API keys:** the model is called through `BASE_URL` with `API_KEY` (an OpenAI-compatible endpoint serving
  Apertus v1.5; the model name comes from `MODEL`, default `swiss-ai/Apertus-v1.5-8B`). Export them, or put
  them in a local `.env` (`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_NAME`; see `.env.example`). No key is in the
  image or the repository.
- **Model weights:** the only local model, `intfloat/multilingual-e5-small` (MIT), is downloaded when the
  image is built and baked into it; nothing is downloaded at run time. It only chooses which booklet text
  Apertus reads (task A); task B sends the whole reference (session 10). Apertus makes every entailment decision.

**Your own cases and booklets.** Write one JSON request per line, as in `examples/cases.jsonl`: `id`, `vote`,
`claim` (`text`, `language`), and either `booklet` (`path` relative to the cases file's folder, e.g.
`booklets/2024_09_22_de.pdf`, and `language`) for task A or `reference` (`text`, `language`) for task B.
Put the PDFs in one folder and run, from `track_2a/`:

```bash
make run CASES=path/to/cases.jsonl BOOKLETS=path/to/booklets OUTPUT_DIR=path/to/output
```

The cases file is mounted as `/data/cases.jsonl` and the booklets folder as `/data/booklets` (both
read-only), so a booklet's `path` must start with `booklets/`. Add `EXTRA_ARGS="--raw /output/raw.jsonl"`
to also keep the model's raw answers. Each input id gets exactly one line in `predictions.jsonl`
(`label`, `label_name`, `evidence`, `metrics`); a request that cannot be answered gets label 1 (neutral).
Behind a proxy: `make run DOCKER_RUN_FLAGS="--network host -e HTTPS_PROXY"`.

**The published image.** The image is published to the GitHub container registry by
`.github/workflows/publish-image.yml`: `latest` is built from `main` only, each build also gets its commit hash
(`sha-` and 12 characters). Pull it and run it with the organisers' command, without building anything:

```bash
docker pull ghcr.io/rashad18236/hackapertus-voting-nli:latest
docker run --rm --read-only --tmpfs /tmp -e BASE_URL -e API_KEY \
  -v "$PWD/cases.jsonl:/data/cases.jsonl:ro" -v "$PWD/booklets:/data/booklets:ro" -v "$PWD/output:/output" \
  ghcr.io/rashad18236/hackapertus-voting-nli:latest --input /data/cases.jsonl --output /output/predictions.jsonl
```

`BASE_URL` and `API_KEY` are taken from the shell (export them first); `MODEL` may be passed the same way.
`/output` must be writable for the container's user.

**Not political advice.** The system only checks whether a claim agrees with the text of an official voting
booklet. Its answers are not voting recommendations and must not be presented as such. Every task A answer
of entailment or contradiction quotes the booklet text it rests on, with its page, so it can be traced to
the source booklet.

## Data
The `data/` directory must not exceed 100 MB.


## 📦 Submission Requirements & Deliverables
❗️ Submissions are not handled on Devpost. Submit through our website only:
http://hackapertus.ch/online-hack/submissions

Requirements differ by challenge. See the description of the challenge you are entering for the exact deliverables.


## ⚖️ Judging Criteria
Judging criteria also differ by challenge. See the respective challenge description.


## Support

**Licensing requirements**
Please check our Terms & Conditions (6. What you build is open source):
https://hackapertus.ch/terms-and-conditions

## FAQ
💡 https://hackapertus.ch/faq

## Contact
💬 In case you have questions, join the conversation on Discord or send an email to “hello@hackapertus.ch”
