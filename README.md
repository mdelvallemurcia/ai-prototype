# MealMate AI

A learning spike to explore LLM integration, RAG pipelines, AI agents, and conversational UIs. The project builds a recipe assistant chatbot that ingests content from YouTube videos, PDFs, and websites, stores it as vector embeddings, and uses retrieval-augmented generation to answer cooking questions.

Not production code — just a playground to get hands-on with the AI toolchain.

## Tech Stack

- Python 3.12+ / uv
- LangChain + NVIDIA Build API (free tier)
- PostgreSQL + pgvector
- Streamlit
- Docker Compose

## Getting Started

```bash
# 1. Start the database
docker compose -f deploy/docker-compose.yml up -d

# 2. Install dependencies
uv sync

# 3. Configure environment
cp .env.example .env
# Edit .env and add your NVIDIA API key (MEALMATE_NVIDIA_API_KEY)

# 4. Ingest some content
uv run python -m src.worker.cli ingest --source <youtube-url-or-pdf-path>

# 5. Launch the chat UI
uv run streamlit run src/web/app.py
```

## Running Tests

Coverage is enforced at 80% minimum (`--cov-fail-under=80`, configured in `pyproject.toml`).

```bash
uv run pytest                   # All tests (with coverage)
uv run pytest tests/unit/       # Unit only
uv run pytest tests/integration # Integration (uses Testcontainers)
uv run pytest --no-cov          # Skip coverage
```

## Linting

```bash
uv run ruff check .             # Lint
uv run ruff format .            # Format
```
