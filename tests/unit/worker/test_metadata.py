"""Unit tests for src/worker/metadata.py — content_hash, base metadata, and enrichment."""

from unittest.mock import MagicMock

from src.worker.metadata import build_base_metadata, compute_content_hash, enrich_documents
from src.worker.tasks import Task

# ---------------------------------------------------------------------------
# compute_content_hash
# ---------------------------------------------------------------------------


def make_doc(page_content: str, metadata: dict | None = None) -> MagicMock:
    doc = MagicMock()
    doc.page_content = page_content
    doc.metadata = metadata if metadata is not None else {}
    return doc


def test_compute_content_hash_same_content_returns_same_hash():
    # Arrange
    docs_a = [make_doc("Page one"), make_doc("Page two")]
    docs_b = [make_doc("Page one"), make_doc("Page two")]

    # Act
    hash_a = compute_content_hash(docs_a)
    hash_b = compute_content_hash(docs_b)

    # Assert
    assert hash_a == hash_b


def test_compute_content_hash_different_content_returns_different_hash():
    # Arrange
    docs_a = [make_doc("Page one")]
    docs_b = [make_doc("Page two")]

    # Act
    hash_a = compute_content_hash(docs_a)
    hash_b = compute_content_hash(docs_b)

    # Assert
    assert hash_a != hash_b


def test_compute_content_hash_returns_sha256_hexdigest():
    # Arrange
    docs = [make_doc("Some recipe text")]

    # Act
    result = compute_content_hash(docs)

    # Assert
    assert isinstance(result, str)
    assert len(result) == 64
    int(result, 16)  # raises ValueError if not valid hex


def test_compute_content_hash_strips_surrounding_whitespace_before_hashing():
    # Arrange
    docs_a = [make_doc("Page one\nPage two")]
    docs_b = [make_doc("  Page one\nPage two  \n")]

    # Act
    hash_a = compute_content_hash(docs_a)
    hash_b = compute_content_hash(docs_b)

    # Assert
    assert hash_a == hash_b


# ---------------------------------------------------------------------------
# build_base_metadata — title precedence and contract fields
# ---------------------------------------------------------------------------


def test_build_base_metadata_uses_task_metadata_title_override():
    # Arrange
    task = Task(source_type="pdf", source="/recipes/pasta.pdf", metadata={"title": "Custom Title"})
    docs = [make_doc("Page content")]

    # Act
    result = build_base_metadata(task, docs)

    # Assert
    assert result["title"] == "Custom Title"
    assert result["source_url"] == "/recipes/pasta.pdf"
    assert result["source_type"] == "pdf"
    assert "content_hash" in result


def test_build_base_metadata_falls_back_to_filename_stem_when_no_override():
    # Arrange
    task = Task(source_type="pdf", source="/recipes/pasta-carbonara.pdf", metadata={})
    docs = [make_doc("Page content")]

    # Act
    result = build_base_metadata(task, docs)

    # Assert
    assert result["title"] == "pasta-carbonara"


def test_build_base_metadata_content_hash_matches_compute_content_hash():
    # Arrange
    task = Task(source_type="pdf", source="/recipes/soup.pdf", metadata={})
    docs = [make_doc("Soup recipe content")]

    # Act
    result = build_base_metadata(task, docs)

    # Assert
    assert result["content_hash"] == compute_content_hash(docs)


# ---------------------------------------------------------------------------
# enrich_documents — chunk_index assignment and constant fields
# ---------------------------------------------------------------------------


def test_enrich_documents_assigns_sequential_chunk_index():
    # Arrange
    docs = [make_doc("Chunk A"), make_doc("Chunk B"), make_doc("Chunk C")]
    base_metadata = {
        "source_url": "/recipes/pasta.pdf",
        "source_type": "pdf",
        "title": "Pasta",
        "content_hash": "abc123",
    }

    # Act
    result = enrich_documents(docs, base_metadata)

    # Assert
    assert [doc.metadata["chunk_index"] for doc in result] == [0, 1, 2]


def test_enrich_documents_keeps_constant_fields_across_chunks():
    # Arrange
    docs = [make_doc("Chunk A"), make_doc("Chunk B")]
    base_metadata = {
        "source_url": "/recipes/pasta.pdf",
        "source_type": "pdf",
        "title": "Pasta",
        "content_hash": "abc123",
    }

    # Act
    result = enrich_documents(docs, base_metadata)

    # Assert
    for doc in result:
        assert doc.metadata["source_url"] == "/recipes/pasta.pdf"
        assert doc.metadata["source_type"] == "pdf"
        assert doc.metadata["title"] == "Pasta"
        assert doc.metadata["content_hash"] == "abc123"


def test_enrich_documents_does_not_clobber_loader_native_metadata():
    # Arrange
    docs = [make_doc("Chunk A", metadata={"page": 1, "source": "loader-native"})]
    base_metadata = {
        "source_url": "/recipes/pasta.pdf",
        "source_type": "pdf",
        "title": "Pasta",
        "content_hash": "abc123",
    }

    # Act
    result = enrich_documents(docs, base_metadata)

    # Assert
    assert result[0].metadata["page"] == 1
    assert result[0].metadata["source_url"] == "/recipes/pasta.pdf"
