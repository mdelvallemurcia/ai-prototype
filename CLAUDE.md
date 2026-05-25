# MealMate AI - Recipe Assistant

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
uv run pytest                       # All tests
uv run pytest tests/unit/           # Unit only
uv run pytest tests/integration/    # Integration (requires DB)
```

### Linting

```bash
uv run ruff check .
uv run ruff format .
```

## Conventions

### Code Style

- ruff for linting and formatting (line-length: 100)
- Type hints on all public functions
- No docstrings unless behavior is non-obvious

### Environment Variables

- All config via environment variables loaded from `.env`
- Never commit `.env`
- Prefix app-specific vars with `MEALMATE_`

### Database

- pgvector for embeddings storage and similarity search
- SQLAlchemy as ORM
- Init scripts in `deploy/database/`

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
