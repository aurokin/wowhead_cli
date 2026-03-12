VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
WOWHEAD := $(VENV)/bin/wowhead
WARCRAFT := $(VENV)/bin/warcraft
METHOD := $(VENV)/bin/method
RAIDERIO := $(VENV)/bin/raiderio
WARCRAFT_WIKI := $(VENV)/bin/warcraft-wiki
WOWPROGRESS := $(VENV)/bin/wowprogress
SIMC := $(VENV)/bin/simc

.PHONY: dev-deploy dev-deploy-no-link test test-live fmt-check run

dev-deploy:
	./scripts/dev_deploy.sh

dev-deploy-no-link:
	./scripts/dev_deploy.sh --no-link-bin

test:
	$(PYTEST) -q

test-live:
	WOWHEAD_LIVE_TESTS=1 $(PYTEST) -q -m live

fmt-check:
	$(PYTHON) -m compileall -q packages

run:
	@if [ -z "$(ARGS)" ]; then \
		echo 'Usage: make run ARGS="search defias"'; \
		exit 2; \
	fi
	$(WOWHEAD) $(ARGS)
