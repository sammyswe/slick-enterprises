.PHONY: install dev test test-backend-config ensure-test-db migrate verify

ROOT := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
PYTHON ?= python3

install:
	cd $(ROOT)backend && $(PYTHON) -m pip install -r requirements.txt
	cd $(ROOT)worker && $(PYTHON) -m pip install -r requirements.txt
	cd $(ROOT)scheduler && $(PYTHON) -m pip install -r requirements.txt
	cd $(ROOT)frontend && npm install

dev:
	bash $(ROOT)scripts/stop-dev-ports.sh
	docker compose -f $(ROOT)docker/docker-compose.yml --env-file $(ROOT).env up --build -d

ensure-test-db:
	bash $(ROOT)scripts/ensure-test-db.sh

test-backend-config:
	cd $(ROOT)backend && $(PYTHON) -m pytest -q tests/test_competitors_api.py tests/test_products_api.py tests/integration/test_config_flow.py

test:
	$(MAKE) test-backend-config
	cd $(ROOT)worker && $(PYTHON) -m pytest -q
	cd $(ROOT)scheduler && $(PYTHON) -m pytest -q
	cd $(ROOT)frontend && npm test

migrate:
	cd $(ROOT)backend && $(PYTHON) -m alembic upgrade head

verify:
	bash $(ROOT)scripts/verify-foundation.sh
