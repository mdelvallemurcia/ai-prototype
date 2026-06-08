"""Unit tests for src/worker/pipeline.py — load→enrich→dedup→chunk→store orchestration."""

from unittest.mock import MagicMock, patch

from src.worker.pipeline import IngestResult, ingest_task
from src.worker.tasks import Task


def make_doc(page_content: str, metadata: dict | None = None) -> MagicMock:
    doc = MagicMock()
    doc.page_content = page_content
    doc.metadata = metadata if metadata is not None else {}
    return doc


def make_container(content_hash_exists: bool = False) -> MagicMock:
    container = MagicMock()
    container.vector_store = MagicMock()
    container.embeddings = MagicMock()
    return container


# ---------------------------------------------------------------------------
# Happy path — new source is loaded, enriched, chunked, and stored
# ---------------------------------------------------------------------------


@patch("src.worker.pipeline._content_hash_exists", return_value=False)
@patch("src.worker.pipeline.loader_for")
def test_ingest_task_new_source_stores_chunks_with_full_metadata(mock_loader_for, mock_exists):
    # Arrange
    task = Task(source_type="pdf", source="/recipes/pasta.pdf", metadata={})
    docs = [make_doc("Some recipe content that is long enough to be split into chunks. " * 5)]
    mock_loader = MagicMock(return_value=docs)
    mock_loader_for.return_value = mock_loader
    container = make_container()

    # Act
    result = ingest_task(container, task)

    # Assert
    assert isinstance(result, IngestResult)
    assert result.status == "stored"
    assert result.source == "/recipes/pasta.pdf"
    assert result.chunks > 0
    container.vector_store.add_documents.assert_called_once()
    stored_chunks = container.vector_store.add_documents.call_args[0][0]
    assert len(stored_chunks) == result.chunks
    for index, chunk in enumerate(stored_chunks):
        assert chunk.metadata["source_url"] == "/recipes/pasta.pdf"
        assert chunk.metadata["source_type"] == "pdf"
        assert chunk.metadata["chunk_index"] == index
        assert "content_hash" in chunk.metadata
        assert "title" in chunk.metadata


@patch("src.worker.pipeline._content_hash_exists", return_value=False)
@patch("src.worker.pipeline.loader_for")
def test_ingest_task_new_source_uses_per_source_content_hash(mock_loader_for, mock_exists):
    # Arrange
    task = Task(source_type="pdf", source="/recipes/soup.pdf", metadata={})
    docs = [make_doc("Soup content " * 20), make_doc("More soup content " * 20)]
    mock_loader_for.return_value = MagicMock(return_value=docs)
    container = make_container()

    # Act
    ingest_task(container, task)

    # Assert
    mock_exists.assert_called_once()
    called_hash = mock_exists.call_args[0][1]
    stored_chunks = container.vector_store.add_documents.call_args[0][0]
    assert all(chunk.metadata["content_hash"] == called_hash for chunk in stored_chunks)


# ---------------------------------------------------------------------------
# Dedup — existing content_hash means SKIP without embedding/storing
# ---------------------------------------------------------------------------


@patch("src.worker.pipeline._content_hash_exists", return_value=True)
@patch("src.worker.pipeline.loader_for")
def test_ingest_task_existing_content_hash_skips_without_storing(mock_loader_for, mock_exists):
    # Arrange
    task = Task(source_type="pdf", source="/recipes/duplicate.pdf", metadata={})
    docs = [make_doc("Duplicate content")]
    mock_loader_for.return_value = MagicMock(return_value=docs)
    container = make_container()

    # Act
    result = ingest_task(container, task)

    # Assert
    assert result.status == "skipped"
    assert result.source == "/recipes/duplicate.pdf"
    assert result.chunks == 0
    container.vector_store.add_documents.assert_not_called()
    container.embeddings.embed_documents.assert_not_called()


# ---------------------------------------------------------------------------
# _content_hash_exists — raw, parameterized, read-only existence check
# ---------------------------------------------------------------------------


def test_content_hash_exists_returns_true_when_row_found():
    # Arrange
    from src.worker.pipeline import _content_hash_exists

    connection = MagicMock()
    connection.execute.return_value.first.return_value = (1,)
    container = MagicMock()
    container.engine.connect.return_value.__enter__.return_value = connection

    # Act
    found = _content_hash_exists(container, "abc123")

    # Assert
    assert found is True
    connection.execute.assert_called_once()


def test_content_hash_exists_returns_false_when_no_row_found():
    # Arrange
    from src.worker.pipeline import _content_hash_exists

    connection = MagicMock()
    connection.execute.return_value.first.return_value = None
    container = MagicMock()
    container.engine.connect.return_value.__enter__.return_value = connection

    # Act
    found = _content_hash_exists(container, "abc123")

    # Assert
    assert found is False


def test_content_hash_exists_passes_hash_as_bound_parameter():
    # Arrange
    from sqlalchemy import TextClause

    from src.worker.pipeline import _content_hash_exists

    connection = MagicMock()
    connection.execute.return_value.first.return_value = None
    container = MagicMock()
    container.engine.connect.return_value.__enter__.return_value = connection

    # Act
    _content_hash_exists(container, "the-hash-value")

    # Assert
    call_args = connection.execute.call_args[0]
    statement = call_args[0]
    params = call_args[1]
    assert isinstance(statement, TextClause)
    assert params == {"content_hash": "the-hash-value"}
