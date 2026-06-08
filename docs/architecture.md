# Architecture

## System Overview

MealMate AI is a RAG-powered recipe assistant. Users chat in a Streamlit UI, the system retrieves relevant recipe chunks from pgvector, and an NVIDIA-hosted LLM generates a contextual response.

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐     ┌────────────┐
│  Streamlit   │────▶│  LangChain RAG   │────▶│   pgvector      │     │  NVIDIA    │
│  Chat UI     │◀────│  Chain           │◀────│   (retriever)   │     │  Build API │
│  (src/web)   │     │  (src/core)      │────▶│                 │     │            │
└─────────────┘     └──────────────────┘     └─────────────────┘     └────────────┘
                                                     ▲
                                              ┌──────┴───────┐
                                              │  Ingestion    │
                                              │  Pipeline     │
                                              │  (src/worker) │
                                              └──────┬───────┘
                                                     │
                                          ┌──────────┼──────────┐
                                          ▼          ▼          ▼
                                       YouTube     PDFs      Websites
```

## Components

### 1. Core (`src/core/`)

Shared infrastructure via a **DI container** — no import-time side effects. All services are lazily created on first property access.

| Module | Responsibility |
|---|---|
| `config.py` | `Settings` frozen dataclass + `load_settings()` factory (reads env vars via `python-dotenv`) |
| `container.py` | `Container` class — holds all services as lazy properties. `create_container()` factory for production use |

#### Container services (lazy properties)

| Property | Type | What it creates on first access |
|---|---|---|
| `settings` | `Settings` | Passed at construction — no side effects |
| `engine` | `Engine` | `create_engine(settings.db_url)` |
| `session_factory` | `sessionmaker` | Bound to `engine` |
| `embeddings` | `NVIDIAEmbeddings` | `model="nvidia/nv-embedqa-e5-v5"` — deferred import |
| `vector_store` | `PGVector` | `collection_name="recipes"` — deferred import |
| `retriever` | `VectorStoreRetriever` | `.as_retriever(search_kwargs={"k": 5})` |

**Methods:**
- `get_session() -> Session` — creates a new SQLAlchemy session from the session factory

**Production**: `container = create_container()` — loads settings from `.env` and creates a container.

**Testing**: `container = Container(Settings(db_url=testcontainers_url, ...))` — inject test config directly, no env vars or mocking needed.

### 2. Web UI (`src/web/`)

Single-file Streamlit app (`app.py`).

- **Interface**: One page, chat-only. Uses `st.chat_message` and `st.chat_input`.
- **State**: Conversation history in `st.session_state`.
- **RAG integration**: _Not yet wired_ — currently a stub. Will connect to the LangChain chain in `core/`.

### 3. Ingestion Pipeline (`src/worker/`)

CLI tool for feeding content into the vector store, driven by a task-list file (YAML or JSON).

```
Task-list file → Task → Router → Loader → Documents → Metadata enrichment
              → content_hash dedup check → Splitter → Chunks → Embeddings → pgvector
```

**Entry point**: `uv run python -m src.worker.cli ingest --tasks <path-to-task-list.yaml>`

Each entry in the task-list file declares `type` (`pdf` | `youtube` | `web`), `source`
(path or URL), and optional `metadata` overrides (e.g. `title`). The CLI parses and
validates the whole file up front (`src/worker/tasks.py`), then runs each task through
the pipeline with **per-task error isolation**: a failing task is recorded and the run
continues; a summary is printed at the end and the process exits non-zero if any task
failed.

#### Loaders (`src/worker/loaders/`)

| Loader | LangChain Class | Notes |
|---|---|---|
| `youtube.py` | `YoutubeLoader` | `add_video_info=True` — fetches title, author into metadata |
| `pdf.py` | `PyPDFLoader` | Reads local PDF files |
| `web.py` | `WebBaseLoader` | Scrapes web pages |

All loaders return `list[Document]`. Routing (`src/worker/router.py`) is an explicit
factory — `pdf` is wired end-to-end; `youtube` and `web` are recognized but currently
raise `NotImplementedError` (deferred to a separate change; isolated as a failed task,
not a crash).

#### Metadata contract (`src/worker/metadata.py`)

Every persisted chunk carries a normalized metadata shape, computed once per source
before chunking: `source_url`, `source_type`, `title` (task override > loader-derived >
filename/URL fallback), `content_hash` (SHA-256 over the source's concatenated raw
text), and `chunk_index` (0-based, assigned after splitting).

#### Chunking

- Splitter: `RecursiveCharacterTextSplitter`, used with library defaults — `chunk_size`
  and `chunk_overlap` are intentionally NOT tuned; see [ADR-005](decisions/005-chunking-strategy.md)
  for the rationale and future tuning plan.

#### Idempotent re-ingest (dedup)

Before chunking/embedding, the pipeline (`src/worker/pipeline.py`) checks whether a
chunk with the same `content_hash` already exists in the `recipes` collection (raw,
parameterized read against `langchain_pg_embedding.cmetadata`). A match skips the whole
task — no embedding calls, no writes. Changed content (different hash) is treated as a
new, additive ingest; replace/delete-on-change is explicitly out of scope for now.

#### Storage

Chunks are embedded via `Container.embeddings` (`NVIDIAEmbeddings`) and stored in the
`recipes` collection in pgvector via `Container.vector_store.add_documents()`, using
cosine distance.

**Current status**: PDF ingestion (routing → chunking → embedding → idempotent storage)
is implemented and covered end-to-end (unit + Testcontainers integration tests).
YouTube and web ingestion remain deferred — the loaders exist but are not yet wired
into the router.

## RAG Chain (Planned)

The retrieval chain is not yet implemented. Intended design:

```
User query
    │
    ▼
┌─────────────────────────┐
│ Retriever               │
│ pgvector cosine search  │
│ k=5, collection=recipes │
└────────┬────────────────┘
         │ relevant chunks
         ▼
┌─────────────────────────┐
│ Prompt Template         │
│ System: recipe/meal     │
│   domain enforcement    │
│ Context: {chunks}       │
│ Question: {user_query}  │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ ChatNVIDIA              │
│ model: meta/llama-3.1   │
│        -8b-instruct     │
└────────┬────────────────┘
         │
         ▼
    Response to user
```

- System prompt will enforce recipe/meal domain context
- Users can specify ingredients to include/exclude
- LLM: `meta/llama-3.1-8b-instruct` via NVIDIA Build API

## Database

### Infrastructure

- **Image**: `pgvector/pgvector:pg17`
- **Database**: `mealmate`
- **Credentials**: `mealmate` / `mealmate_dev` (dev only)
- **Port**: `5432`
- **Volume**: `postgres_data` (named, persistent)
- **Driver**: `psycopg` (v3, not psycopg2)

### Schema

Managed entirely by `langchain-postgres` — no hand-written tables or Alembic migrations.

The `PGVector` class auto-creates:

| Table | Purpose |
|---|---|
| `langchain_pg_collection` | Collection metadata (`name`, `uuid`, `cmetadata` JSONB) |
| `langchain_pg_embedding` | Document chunks (`id`, `collection_id` FK, `embedding` vector, `document` text, `cmetadata` JSONB) |

Init script (`deploy/database/init.sql`) only enables the pgvector extension:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## Configuration

All config via `MEALMATE_*` environment variables, loaded from `.env` by `python-dotenv`.

| Variable | Default | Purpose |
|---|---|---|
| `MEALMATE_NVIDIA_API_KEY` | `""` | NVIDIA Build API authentication |
| `MEALMATE_NVIDIA_MODEL` | `meta/llama-3.1-8b-instruct` | Chat completion model |
| `MEALMATE_NVIDIA_EMBED_MODEL` | `nvidia/nv-embedqa-e5-v5` | Embedding model |
| `MEALMATE_DB_URL` | `postgresql+psycopg://mealmate:mealmate_dev@localhost:5432/mealmate` | Database connection |

## Key Dependencies

| Package | Version | Purpose |
|---|---|---|
| `langchain` | `>=0.3` | RAG framework |
| `langchain-nvidia-ai-endpoints` | `>=0.3` | NVIDIA LLM + embeddings |
| `langchain-postgres` | `>=0.0.12` | pgvector integration |
| `langchain-community` | `>=0.3` | Document loaders |
| `streamlit` | `>=1.40` | Chat UI |
| `sqlalchemy` | `>=2.0` | Database engine |
| `psycopg[binary]` | `>=3.2` | PostgreSQL driver (v3, not psycopg2 — see note below) |
| `yt-dlp` | `>=2024.0` | YouTube video metadata and transcript download |
| `beautifulsoup4` | `>=4.12` | HTML parsing for web loader |
| `pypdf` | `>=5.0` | PDF parsing for PDF loader |

**Note on psycopg v3**: The project uses `psycopg` (v3), not `psycopg2`. This affects connection strings — the SQLAlchemy dialect is `postgresql+psycopg://` (not `postgresql+psycopg2://`). Do not swap for `psycopg2-binary` without updating all connection URLs

## Implementation Status

| Component | Status |
|---|---|
| DI container (config, engine, embeddings, retriever) | Done |
| Document loaders (YouTube, PDF, web) | Done |
| CLI entry point | Stub — routing not wired |
| Chunking + embedding + upsert pipeline | Not implemented |
| RAG chain (prompt + LLM + retriever) | Not implemented |
| Streamlit chat UI | Stub — hardcoded response |
| Integration tests with Testcontainers | Not implemented |
