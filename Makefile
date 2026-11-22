# Single entry point for every project command. Run `make` for the list.
# Every container is defined in compose.yaml (project ha-claude-code-assist).

SHELL := /bin/bash
.DEFAULT_GOAL := help

ROOT           := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
APP            := local_ha_claude_code_assist
DEV_CONTAINER  := ha-claude-code-assist-dev
PYTHON_VERSION := 3.13

COMPOSE  := UID_GID=$(shell id -u):$(shell id -g) docker compose -f $(ROOT)/compose.yaml
RUN      := $(COMPOSE) run --rm
DEV_EXEC := docker exec $(DEV_CONTAINER)

.PHONY: help
help: ## Show this list
	@grep -hE '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "} {printf "  %-17s %s\n", $$1, $$2}'

# --- Test environment (Supervisor + Home Assistant) -----------------------

.PHONY: dev-up
dev-up: ## Start the test environment (clean data) and wait until it is ready
	$(COMPOSE) up -d --build dev
	$(ROOT)/scripts/dev-wait.sh

.PHONY: dev-down
dev-down: ## Stop and remove the test environment container
	$(COMPOSE) down

.PHONY: dev-logs
dev-logs: ## Follow the Supervisor and provisioning logs
	$(DEV_EXEC) journalctl -f -u ha-supervisor -u ha-dev-setup

.PHONY: dev-shell
dev-shell: ## Open a shell in the test environment
	docker exec -it $(DEV_CONTAINER) bash

.PHONY: dev-destroy
dev-destroy: ## Remove the test environment, its image caches and its image
	$(COMPOSE) down --volumes --rmi local

# --- App in the test environment --------------------------------------------

.PHONY: app-rebuild
app-rebuild: ## Rebuild the app from the local folder and restart it
	$(DEV_EXEC) ha apps rebuild $(APP) --no-progress

.PHONY: integration-sync
integration-sync: ## Copy the Assist integration into the test Home Assistant and restart its Core
	$(DEV_EXEC) sh -c 'rm -rf /mnt/supervisor/homeassistant/custom_components/ha_claude_code_assist && cp -r /mnt/supervisor/apps/local/ha-claude-code-assist/custom_components/ha_claude_code_assist /mnt/supervisor/homeassistant/custom_components/'
	$(DEV_EXEC) ha core restart --no-progress

.PHONY: app-logs
app-logs: ## Show the app log
	$(DEV_EXEC) ha apps logs $(APP)

.PHONY: app-smoke
app-smoke: ## End-to-end test through Ingress: panel, real chat with Claude, memory, sessions
	$(RUN) smoke

.PHONY: app-behave
app-behave: ## Behaviour report: real conversations with the assistant (scripts/app-behave.json)
	$(RUN) smoke node /scripts/app-behave.mjs

# --- Tests and dependencies -------------------------------------------------

.PHONY: test
test: ## Run the core's automated tests (in the app image)
	$(COMPOSE) build test
	$(RUN) test

.PHONY: test-integration
test-integration: ## Run the tests of the Home Assistant integration (custom_components/)
	$(COMPOSE) build test-integration
	$(RUN) test-integration

.PHONY: lint
lint: ## Check the panel: TypeScript types and ESLint
	$(RUN) node sh -c "npm ci --ignore-scripts --no-audit --no-fund && npx tsc && npm run lint"

.PHONY: lock
lock: ## Regenerate the locked dependencies (requirements*.txt, package-lock.json)
	$(RUN) uv uv pip compile requirements.in --generate-hashes \
		--python-version $(PYTHON_VERSION) --output-file requirements.txt
	$(RUN) uv uv pip compile requirements-dev.in --generate-hashes \
		--python-version $(PYTHON_VERSION) --output-file requirements-dev.txt
	$(RUN) -v $(ROOT)/integration-tests:/it -w /it uv uv pip compile requirements.in --generate-hashes \
		--python-version 3.14.9 --output-file requirements.txt
	$(RUN) node npm install --package-lock-only --ignore-scripts
