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

# Runs the image on examples/cases.jsonl (one task A, one task B request).
# /data is mounted read-only and the container's root filesystem is read-only;
# it can write only to /output (mounted) and /tmp (in memory).
run: build
	mkdir -p output
	docker run --rm --platform $(PLATFORM) $(ENV_FILE) $(PASS_VARS) $(DOCKER_RUN_FLAGS) \
		--read-only --tmpfs /tmp \
		--user $$(id -u):$$(id -g) \
		-v "$(CURDIR)/examples:/data:ro" \
		-v "$(CURDIR)/output:/output" \
		$(IMAGE) --input /data/cases.jsonl --output /output/predictions.jsonl
