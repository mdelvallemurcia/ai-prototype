"""Greenfield Testcontainers fixtures for worker ingestion integration tests.

Spins up a real PostgreSQL + pgvector container (matching deploy/docker-compose.yml's
pgvector/pgvector:pg17 image), enables the vector extension, and yields a real
Container wired to it. NVIDIA embeddings are replaced with a deterministic fake
(no network, no API key) — the vector store and database are REAL.

Requires Docker. If the `testcontainers` package is not installed, or no Docker
daemon is reachable, these fixtures will fail to collect/run — see the
worker-cli-ingestion apply-progress notes for the developer follow-up needed
to approve the `testcontainers` dev dependency and run this suite locally/in CI.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding
from sqlalchemy import text
from testcontainers.postgres import PostgresContainer

from src.core.config import Settings
from src.core.container import Container

_FAKE_EMBEDDING_SIZE = 16


@pytest.fixture(scope="session")
def pg_container() -> Iterator[PostgresContainer]:
    with PostgresContainer("pgvector/pgvector:pg17", driver="psycopg") as postgres:
        yield postgres


@pytest.fixture()
def container(pg_container: PostgresContainer) -> Iterator[Container]:
    db_url = pg_container.get_connection_url()
    settings = Settings(
        nvidia_api_key="unused-in-integration-tests",
        nvidia_model="unused-in-integration-tests",
        nvidia_embed_model="unused-in-integration-tests",
        db_url=db_url,
    )
    test_container = Container(settings)

    with test_container.engine.connect() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        connection.commit()

    # Override the lazily-created embeddings with a deterministic fake so no
    # NVIDIA API call/network is involved while the pgvector store stays real.
    test_container._embeddings = DeterministicFakeEmbedding(size=_FAKE_EMBEDDING_SIZE)

    yield test_container

    with test_container.engine.connect() as connection:
        connection.execute(text("DROP TABLE IF EXISTS langchain_pg_embedding CASCADE"))
        connection.execute(text("DROP TABLE IF EXISTS langchain_pg_collection CASCADE"))
        connection.commit()
