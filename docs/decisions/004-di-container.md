# ADR-004: DI Container in core/

## Status

Accepted (supersedes module-level singletons)

## Context

The `core/` package exposes shared infrastructure: config, DB engine, embeddings client, and vector store retriever. The original approach used module-level singletons — each module created its instance at import time.

This caused testing friction: importing any `core/` module triggered real connections (DB, NVIDIA API), requiring tests to mock or patch before importing dependent modules. With Testcontainers planned for integration tests, the import-time approach became impractical — Testcontainers provides a dynamic DB URL at runtime, but singletons were already created before the test could set it.

## Decision

Replace module-level singletons with a `Container` class in `core/container.py`. All services are exposed as lazy properties — created on first access, not on import.

## Implementation

- `config.py` — `Settings` frozen dataclass + `load_settings()` factory function (no module-level instance)
- `container.py` — `Container(settings)` with lazy properties for engine, session_factory, embeddings, vector_store, retriever
- `create_container()` — factory that loads settings from env and returns a wired container
- `database.py`, `embeddings.py`, `retriever.py` — removed (consolidated into container)

## Reasoning

- **Testability**: Tests construct `Container(Settings(db_url=...))` with any config — no patching, no import-order tricks, Testcontainers just works.
- **No import-time side effects**: Importing `src.core` doesn't trigger DB or API connections.
- **No framework overhead**: Plain Python class with lazy properties — no `dependency-injector` or other library needed.
- **Same developer experience**: `container.engine` instead of importing `engine` — minimal ceremony.

## Consequences

- Callers must create or receive a `Container` instance instead of importing singletons directly.
- LangChain imports (`NVIDIAEmbeddings`, `PGVector`) are deferred inside properties to avoid import-time overhead.
- If the project grows to need scoped lifetimes (e.g., per-request containers), this pattern extends naturally.
