.PHONY: run build

IMAGE := hackapertus-voting-nli
PLATFORM := linux/amd64

# Credentials, environment first: variables exported in the shell are passed
# with -e and take precedence over a local .env (used if present).
# The pipeline reads BASE_URL / API_KEY (official names), falling back to
# LLM_BASE_URL / LLM_API_KEY, and MODEL, falling back to LLM_NAME.
ENV_FILE := $(if $(wildcard .env),--env-file .env,)
PASS_VARS := -e BASE_URL -e API_KEY -e MODEL -e LLM_BASE_URL -e LLM_API_KEY -e LLM_NAME

# Optional extra docker run flags, empty by default. Only needed where the
# container cannot reach the internet directly, e.g. behind a proxy:
#   make run DOCKER_RUN_FLAGS="--network host -e HTTPS_PROXY"
DOCKER_RUN_FLAGS ?=

build:
	docker build --platform $(PLATFORM) -t $(IMAGE) .

# What to run on. Defaults: the two example requests (with the booklet the task A
# example needs, from examples/booklets/), predictions in ./output.
# Only the cases file (and, for task A, the booklets folder) is mounted, never
# the expected labels. Example for the dev split:
#   make run CASES=data/dev/cases.jsonl OUTPUT_DIR=output/dev
CASES ?= examples/cases.jsonl
BOOKLETS ?= $(if $(wildcard examples/booklets),examples/booklets,)
OUTPUT_DIR ?= output
EXTRA_ARGS ?=
BOOKLET_MOUNT := $(if $(BOOKLETS),-v "$(abspath $(BOOKLETS)):/data/booklets:ro",)

# /data is mounted read-only and the container's root filesystem is read-only;
# it can write only to /output (mounted) and /tmp (in memory).
run: build
	mkdir -p $(OUTPUT_DIR)
	docker run --rm --platform $(PLATFORM) $(ENV_FILE) $(PASS_VARS) $(DOCKER_RUN_FLAGS) \
		--read-only --tmpfs /tmp \
		--user $$(id -u):$$(id -g) \
		-v "$(abspath $(CASES)):/data/cases.jsonl:ro" $(BOOKLET_MOUNT) \
		-v "$(abspath $(OUTPUT_DIR)):/output" \
		$(IMAGE) --input /data/cases.jsonl --output /output/predictions.jsonl $(EXTRA_ARGS)
