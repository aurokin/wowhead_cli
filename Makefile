VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff
MYPY := $(VENV)/bin/mypy
RADON := $(VENV)/bin/radon
VULTURE := $(VENV)/bin/vulture
WOWHEAD := $(VENV)/bin/wowhead
WARCRAFT := $(VENV)/bin/warcraft
METHOD := $(VENV)/bin/method
RAIDERIO := $(VENV)/bin/raiderio
WARCRAFT_WIKI := $(VENV)/bin/warcraft-wiki
WOWPROGRESS := $(VENV)/bin/wowprogress
SIMC := $(VENV)/bin/simc
LINT_PATHS := packages/warcraft-core packages/warcraft-api packages/warcraft-content
LINT_ALL_PATHS := packages tests scripts

.PHONY: dev-deploy dev-deploy-no-link test test-live fmt-check lint lint-all complexity typecheck coverage deadcode run

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

lint:
	$(RUFF) check $(LINT_PATHS)

lint-all:
	$(RUFF) check $(LINT_ALL_PATHS)

complexity:
	$(RADON) cc packages -s -a
	$(RADON) mi packages -s

typecheck:
	$(MYPY)

coverage:
	@$(PYTHON) -c 'import sqlite3' >/dev/null 2>&1 || { \
		echo "Coverage is blocked: the active Python build is missing sqlite3/_sqlite3."; \
		echo "Fix the local Python runtime first, then re-enable pytest-cov."; \
		exit 2; \
	}
	@echo "Coverage tooling is deferred on this machine until sqlite3 support is available."

deadcode:
	$(VULTURE) packages scripts tests --min-confidence 80

run:
	@if [ -z "$(ARGS)" ]; then \
		echo 'Usage: make run ARGS="search defias"'; \
		exit 2; \
	fi
	$(WOWHEAD) $(ARGS)
