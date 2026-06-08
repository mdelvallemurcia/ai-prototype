"""E2E integration test: PDF ingestion against a real pgvector store (Testcontainers).

Embeddings are mocked (DeterministicFakeEmbedding — no network/API key); the
vector store, Postgres, and pgvector extension are REAL. This is the proof that
PR1 (parsing/metadata) + PR2 (router/pipeline/dedup) work together end-to-end.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from src.worker.pipeline import ingest_task
from src.worker.tasks import Task
from tests.integration.fixtures.pdf import build_minimal_pdf

_RECIPE_TEXT = "MealMate Test Recipe: tomato pasta with basil."

_ROW_COUNT_QUERY = text("SELECT cmetadata FROM langchain_pg_embedding")


def _write_recipe_pdf(tmp_path: Path) -> str:
    pdf_path = tmp_path / "recipe.pdf"
    pdf_path.write_bytes(build_minimal_pdf(_RECIPE_TEXT))
    return str(pdf_path)


def _fetch_stored_metadata(container) -> list[dict]:
    with container.engine.connect() as connection:
        rows = connection.execute(_ROW_COUNT_QUERY).fetchall()
    return [row[0] for row in rows]


def test_ingest_pdf_task_persists_chunks_with_full_metadata(container, tmp_path):
    # Arrange
    pdf_path = _write_recipe_pdf(tmp_path)
    task = Task(source_type="pdf", source=pdf_path, metadata={})

    # Act
    result = ingest_task(container, task)

    # Assert
    assert result.status == "stored"
    assert result.chunks > 0

    stored = _fetch_stored_metadata(container)
    assert len(stored) == result.chunks

    expected_title = Path(pdf_path).stem
    chunk_indices = sorted(meta["chunk_index"] for meta in stored)
    assert chunk_indices == list(range(result.chunks))

    for meta in stored:
        assert meta["source_url"] == pdf_path
        assert meta["source_type"] == "pdf"
        assert meta["title"] == expected_title
        assert meta["content_hash"]


def test_ingest_pdf_task_rerun_same_source_skips_without_new_rows(container, tmp_path):
    # Arrange
    pdf_path = _write_recipe_pdf(tmp_path)
    task = Task(source_type="pdf", source=pdf_path, metadata={})
    first_result = ingest_task(container, task)
    rows_after_first_run = _fetch_stored_metadata(container)

    # Act
    second_result = ingest_task(container, task)

    # Assert
    assert second_result.status == "skipped"
    assert second_result.chunks == 0

    rows_after_second_run = _fetch_stored_metadata(container)
    assert len(rows_after_second_run) == len(rows_after_first_run) == first_result.chunks
