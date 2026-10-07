.PHONY: run build

IMAGE := hackapertus-voting-nli

# Credentials: a local .env is used if present. Variables exported in the shell
# are passed with -e as well and take precedence over .env.
ENV_FILE := $(if $(wildcard .env),--env-file .env,)

build:
	docker build -t $(IMAGE) .

# data/ and output/ are mounted so cases can be swapped without a rebuild and
# predictions land in ./output on the host. Extra CLI args: make run ARGS="in out"
run: build
	mkdir -p output
	docker run --rm $(ENV_FILE) \
		-e LLM_NAME -e LLM_BASE_URL -e LLM_API_KEY \
		--user $$(id -u):$$(id -g) \
		-v "$(CURDIR)/data:/app/data:ro" \
		-v "$(CURDIR)/output:/app/output" \
		$(IMAGE) $(ARGS)
