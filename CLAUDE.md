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
- `core/` — shared infrastructure via **DI container** (`container.py`). `Settings` dataclass in `config.py`, all services (engine, embeddings, vector store, retriever) lazily created by `Container` on first access.
- `web/` — Streamlit chat app. Currently a stub with TODO for RAG chain integration.
- `worker/` — CLI ingestion pipeline. Each source type has a loader in `worker/loaders/` using LangChain community document loaders.

**Key wiring detail:** Use `create_container()` to get a `Container` with all dependencies. In tests, construct `Container(settings)` directly with a custom `Settings` instance (e.g., Testcontainers DB URL). No import-time side effects — all connections are deferred until the property is accessed.

## Project Structure

```
src/
├── web/          # Streamlit chat application
├── worker/       # CLI ingestion pipeline (manual trigger)
│   └── loaders/  # Source-specific loaders (youtube, pdf, web)
└── core/         # DI container, config, and shared infrastructure
deploy/
├── docker-compose.yml  # PostgreSQL + pgvector (+ future services like Grafana)
└── database/           # DB init scripts
tests/
├── unit/
└── integration/        # Requires running database
```

## Development

See `README.md` for full setup instructions (Docker, uv sync, .env config).

**Quick reference:**

```bash
uv run streamlit run src/web/app.py              # Chat UI
uv run python -m src.worker.cli ingest --source <url>  # Ingest content
uv run pytest                                    # All tests (with coverage, 80% min)
uv run pytest tests/unit/                        # Unit only
uv run pytest tests/integration/                 # Integration (Testcontainers)
uv run pytest --no-cov                           # Skip coverage
uv run ruff check .                              # Lint
uv run ruff format .                             # Format
```

## Documentation

- `docs/architecture.md` — detailed system architecture, component wiring, and implementation status
- `docs/decisions/` — Architecture Decision Records (ADRs) explaining the "why" behind technical choices

## Agent Rules

- Never commit or push code. Only modify files — the developer handles git.
- Never add new libraries or dependencies without asking first.
- Never replace the current LLM provider, vector store, or UI framework without discussion.
- Don't bypass the DI container — all core services must be accessed through `Container` (see `docs/decisions/004-di-container.md`).
- Don't tune chunking parameters (`chunk_size`, `chunk_overlap`) without discussion.
- Always use `uv run`, never raw `python` or `pip`.

## Conventions

### Testing

- **Pattern**: AAA (Arrange-Act-Assert) — every test has three clearly separated blocks
- **Naming**: `test_<unit>_<scenario>_<expected>` (e.g. `test_load_pdf_empty_file_returns_empty_list`)
- **Coverage**: 80% minimum enforced via `pytest-cov` (configured in `pyproject.toml`)
- **Unit tests** (`tests/unit/`): fast, no external dependencies. Mock DB, APIs, and filesystem
- **Integration tests** (`tests/integration/`): hit real PostgreSQL via Testcontainers — no mocking the DB, no manual Docker setup needed
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
- PGVector vector store via `Container.vector_store` with collection name `recipes`, cosine similarity, k=5

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
