# ADR-002: PostgreSQL + pgvector as Vector Store

## Status

Accepted — open to revision

## Context

The project needs a vector store for storing recipe embeddings and performing similarity search. Options considered: Chroma (in-process), Pinecone (managed SaaS), Qdrant (self-hosted or cloud), and PostgreSQL with the pgvector extension.

## Decision

Use PostgreSQL 17 with pgvector extension (`pgvector/pgvector:pg17` Docker image) as the single database for both relational data and vector search.

## Reasoning

- **Familiarity**: PostgreSQL is well-documented and widely covered in tutorials — the initial learning came from video content showing pgvector in RAG pipelines.
- **Single database**: No need to manage a separate vector store service alongside a relational DB. One Docker container handles everything.
- **Easy local setup**: Runs in Docker with no GPU or special hardware requirements.
- **No licensing cost**: PostgreSQL and pgvector are fully open-source (PostgreSQL License / MIT). Safe to use if the project evolves into a real product.
- **LangChain support**: `langchain-postgres` provides `PGVector` integration out of the box.

### Driver: psycopg v3

The project uses `psycopg` (v3), not `psycopg2`. This was chosen for its native async support and active development. The SQLAlchemy connection string uses the `postgresql+psycopg://` dialect — swapping to `psycopg2-binary` would require changing all connection URLs.

## Consequences

- Performance at scale is not validated — this is a spike/prototype. If the recipe corpus grows significantly, a dedicated vector DB may perform better.
- The team is open to switching to another vector store if a better fit is found, as long as it runs locally without restrictions and has no licensing cost.
- Cosine similarity with k=5 is the current retrieval config — not benchmarked, just a reasonable starting point.
