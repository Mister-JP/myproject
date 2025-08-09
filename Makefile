PY = python

.PHONY: setup install lint format test db-up db-down search-up up down run-search reindex api sweep

setup:
	@echo "Poetry not detected; use pip install -r requirements.txt or install Poetry if desired."

install:
	poetry install --no-root

lint:
	@echo "Skipping lint (Poetry/linters not installed via pip)."

format:
	@echo "Skipping format (Poetry/linters not installed via pip)."

test:
	@echo "Skipping tests (pytest not installed via pip)."

db-up:
	docker compose up -d db

db-down:
	docker compose down

run-search:
    PYTHONPATH=src $(PY) -m ingestion.cli --query "$(query)" --max-results $(or $(max), 10) --source $(or $(source), arxiv)

search-up:
	docker compose up -d search

up:
	docker compose up -d db search

down:
	docker compose down

reindex:
	PYTHONPATH=src $(PY) -m ingestion.indexer

api:
	PYTHONPATH=src uvicorn ingestion.api:app --host 0.0.0.0 --port 8000

sweep:
    # Simple sweep against a source and query; author and max optional
    PYTHONPATH=src $(PY) -m ingestion.cli --query "$(or $(q), $(query))" --max-results $(or $(max), 10) --source $(or $(source), arxiv) $(if $(author),--author "$(author)")


