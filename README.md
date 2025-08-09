## Phase-1 Backend Foundations

This repository contains a minimal ingestion backend for academic literature, focused on arXiv for Phase-1. It can search arXiv, persist metadata to PostgreSQL, and download PDFs to local storage.

### Prerequisites
- Python 3.10+
- Docker (optional, for local PostgreSQL)
- Poetry (recommended) or pip

### Quickstart
1) Create a virtualenv and install dependencies (pip):
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

2) Optional: start PostgreSQL locally (or use the default SQLite):
```bash
docker compose up -d db
export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/literature
```

3) Run a search (choose one):
```bash
# Module entrypoint (no PYTHONPATH needed after editable install). Supports --author and --source (arxiv|openalex).
python -m ingestion.cli --query "transformer" --author "Vaswani" --max-results 3 --source arxiv
python -m ingestion.cli --query "large language models" --max-results 3 --source openalex

# or via Makefile
make run-search query="transformer" max=3
```

Environment variables (defaults):
- `DATABASE_URL=sqlite:///./data/literature.db`
- `STORAGE_DIR=./data/pdfs`
- `ARXIV_MAX_RESULTS=10`
To use PostgreSQL locally: `make db-up` or the docker compose command above, then set `DATABASE_URL` as shown.

### Output
JSON like `{ "stored": N, "skipped": M, "errors": E }`. Metadata stored in DB, PDFs under `data/pdfs/`.

### Connector architecture
- Base interface in `src/ingestion/connectors/base.py` now uses `QuerySpec` and `PDFRef`.
- arXiv implementation in `src/ingestion/connectors/arxiv.py`.
- OpenAlex implementation in `src/ingestion/connectors/openalex.py`.
- Add new connectors by implementing `search(QuerySpec)` yielding `PaperMetadata` and optional `fetch_pdf`.

### Database schema
- Table `papers` includes: `id`, `source`, `external_id`, `doi`, `title`, `authors` (JSON), `abstract`, `license`, `pdf_path`, `fetched_at`.
- Deduplication: by DOI (preferred), then by `(source, external_id)`, then a heuristic hash of title + authors.

### CI
GitHub Actions runs linting (ruff, black) and tests (pytest) on each PR/push to `main`.

### Notes on licensing & compliance
- We store any available license metadata from arXiv. Always respect source licensing; only download PDFs where permitted by the source.

### Makefile targets
- `make db-up` / `make db-down`: start/stop PostgreSQL
- `make setup`: install dependencies via Poetry
- `make run-search query="..." max=10 [source=arxiv|openalex]`: run ingestion
- `make search-up`: start OpenSearch
- `make up` / `make down`: start/stop DB and search together
- `make reindex`: push papers from DB into search index
- `make api`: run the FastAPI server on `http://localhost:8000`
- `make sweep source=openalex q="large language models" max=20`: simple sweep convenience wrapper

### Search API
- `GET /search` with params: `q`, `author`, `year_start`, `year_end`, `license`, `source`, `sort=recency|citations`, `size`
- `GET /paper/{id}` returns metadata and PDF path if stored

- `make lint` / `make format` / `make test`

