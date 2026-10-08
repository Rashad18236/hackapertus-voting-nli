.PHONY: run build compare

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
DOCKER_RUN := docker run --rm --platform $(PLATFORM) $(ENV_FILE) $(PASS_VARS) $(DOCKER_RUN_FLAGS) \
	--read-only --tmpfs /tmp \
	--user $$(id -u):$$(id -g) \
	-v "$(abspath $(CASES)):/data/cases.jsonl:ro" $(BOOKLET_MOUNT)

run: build
	mkdir -p $(OUTPUT_DIR)
	$(DOCKER_RUN) -v "$(abspath $(OUTPUT_DIR)):/output" \
		$(IMAGE) --input /data/cases.jsonl --output /output/predictions.jsonl $(EXTRA_ARGS)

# Run the same cases once per task A context mode (src/context.py, MODES), one
# after the other, each into its own folder: $(OUTPUT_DIR)/<variant>/predictions.jsonl,
# plus the raw model answers in raw.jsonl. Task B cases give the same answers in every
# variant, so compare on a task-A-only cases file to avoid paying for them twice:
#   make compare CASES=output/devA60/cases.jsonl BOOKLETS=output/booklets_dev OUTPUT_DIR=output/compare-A60
# This checks the variants inside the Docker image. For results in docs/results.md use
# scripts/paired_run.py: it runs the variants on each case back to back (endpoint drift).
VARIANTS ?= full vote-section embed-e5-small
compare: build
	@for v in $(VARIANTS); do \
		echo "=== task A context: $$v ==="; \
		mkdir -p "$(abspath $(OUTPUT_DIR))/$$v" && \
		$(DOCKER_RUN) -v "$(abspath $(OUTPUT_DIR))/$$v:/output" \
			$(IMAGE) --input /data/cases.jsonl --output /output/predictions.jsonl \
			--context-a $$v --raw /output/raw.jsonl $(EXTRA_ARGS) || exit 1; \
	done
