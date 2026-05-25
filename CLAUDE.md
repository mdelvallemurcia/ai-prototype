# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered chat assistant that helps users find the perfect meal. Uses RAG (Retrieval-Augmented Generation) to search through recipes ingested from YouTube videos, PDFs, and websites.

## Tech Stack

- **Language**: Python 3.12+
- **LLM Provider**: NVIDIA Build API (`langchain-nvidia-ai-endpoints`)
- **RAG Framework**: LangChain
- **Vector Store**: PostgreSQL + pgvector
- **Web UI**: Streamlit
- **Package Manager**: uv
- **Testing**: pytest
- **Linting**: ruff
- **Infrastructure**: Docker Compose

## Architecture

```
User → Streamlit Chat → LangChain RAG Chain → pgvector retrieval → NVIDIA LLM → Response
                                                      ↑
                                        CLI Worker (ingestion pipeline)
                                        YouTube | PDFs | Websites → chunks → embeddings → pgvector
```

**Three source packages under `src/`:**
- `core/` — shared infrastructure: config, DB engine, embeddings client, retriever. All wired as **module-level singletons** (imported, not constructed).
- `web/` — Streamlit chat app. Currently a stub with TODO for RAG chain integration.
- `worker/` — CLI ingestion pipeline. Each source type has a loader in `worker/loaders/` using LangChain community document loaders.

**Key wiring detail:** `core/config.py` calls `load_dotenv()` and reads env vars at **import time** via a frozen dataclass default. `core/database.py`, `core/embeddings.py`, and `core/retriever.py` all create their singletons (engine, embeddings client, vector store) at import time too. This means importing any `core` module triggers real connections — mock or patch these in tests before importing dependent modules.

## Project Structure

```
src/
├── web/          # Streamlit chat application
├── worker/       # CLI ingestion pipeline (manual trigger)
│   └── loaders/  # Source-specific loaders (youtube, pdf, web)
└── core/         # Shared modules (config, DB, embeddings, retriever)
deploy/
├── docker-compose.yml  # PostgreSQL + pgvector (+ future services like Grafana)
└── database/           # DB init scripts
tests/
├── unit/
└── integration/        # Requires running database
```

## Development

### Prerequisites

- Python 3.12+
- uv
- Docker & Docker Compose

### Setup

```bash
docker compose -f deploy/docker-compose.yml up -d
uv sync
cp .env.example .env
# Edit .env with your NVIDIA API key
```

### Run

```bash
# Chat UI
uv run streamlit run src/web/app.py

# Ingest content
uv run python -m src.worker.cli ingest --source <url-or-path>
```

### Testing

```bash
uv run pytest                                    # All tests (with coverage)
uv run pytest tests/unit/                        # Unit only
uv run pytest tests/integration/                 # Integration (requires DB)
uv run pytest tests/unit/test_foo.py::test_bar   # Single test
uv run pytest --no-cov                           # Skip coverage
```

### Linting

```bash
uv run ruff check .
uv run ruff format .
```

## Conventions

### Testing

- **Pattern**: AAA (Arrange-Act-Assert) — every test has three clearly separated blocks
- **Naming**: `test_<unit>_<scenario>_<expected>` (e.g. `test_load_pdf_empty_file_returns_empty_list`)
- **Coverage**: 80% minimum enforced via `pytest-cov` (configured in `pyproject.toml`)
- **Unit tests** (`tests/unit/`): fast, no external dependencies. Mock DB, APIs, and filesystem
- **Integration tests** (`tests/integration/`): hit real PostgreSQL (Docker). No mocking the DB here
- **Libraries**: pytest, pytest-asyncio, pytest-cov
- **Fixtures**: shared fixtures go in `conftest.py` at the appropriate level (`tests/`, `tests/unit/`, `tests/integration/`)
- **What to mock**: NVIDIA API calls, filesystem access, network requests. Never mock the thing you're testing

### Code Style

- ruff for linting and formatting (line-length: 100)
- Type hints on all public functions
- No docstrings unless behavior is non-obvious

### Environment Variables

- All config via environment variables loaded from `.env`
- Never commit `.env`
- Prefix app-specific vars with `MEALMATE_`
- Key vars: `MEALMATE_NVIDIA_API_KEY`, `MEALMATE_NVIDIA_MODEL`, `MEALMATE_NVIDIA_EMBED_MODEL`, `MEALMATE_DB_URL`
- Config lives in `src/core/config.py` as a frozen `Settings` dataclass

### Database

- pgvector for embeddings storage and similarity search
- PostgreSQL 17 (`pgvector/pgvector:pg17` image)
- SQLAlchemy as ORM
- Init scripts in `deploy/database/`
- PGVector vector store in `core/retriever.py` with collection name `recipes`, cosine similarity, k=5

### Ingestion Pipeline

- Each source type has its own loader in `src/worker/loaders/`
- LangChain document loaders for parsing
- Chunking: RecursiveCharacterTextSplitter
- Embeddings via NVIDIA API

### RAG

- Retrieval chain via LangChain
- System prompt enforces recipe/meal domain context
- User can specify ingredients to include/exclude
- Similarity search with pgvector (cosine distance)
