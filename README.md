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

## API Key Setup

The chat interface requires a free NVIDIA Build API key to call the LLM.

1. Go to [build.nvidia.com](https://build.nvidia.com) and create a free account.
2. Generate an API key — it starts with `nvapi-`.
3. Copy the environment template and add your key:

   ```bash
   cp .env.example .env
   # Then open .env and set:
   # MEALMATE_NVIDIA_API_KEY=nvapi-<your-key-here>
   ```

**Key variables:**

| Variable | Required for | Notes |
|----------|-------------|-------|
| `MEALMATE_NVIDIA_API_KEY` | Chat (required) | Free tier at build.nvidia.com |
| `MEALMATE_NVIDIA_MODEL` | Chat (optional) | Defaults to `meta/llama-3.1-8b-instruct` |
| `MEALMATE_NVIDIA_EMBED_MODEL` | Ingestion only | Not needed for chat |
| `MEALMATE_DB_URL` | Ingestion only | Not needed for chat |

> **Note:** You can run the chat UI without a database. A database is only needed for
> the ingestion pipeline (`uv run python -m src.worker.cli ingest ...`). If the API key
> is missing or invalid, the app shows a friendly error message instead of crashing.

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
