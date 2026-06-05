"""Unit tests for src/web/handlers.py — pure logic, no Streamlit runtime needed."""

from src.web.handlers import (
    build_echo_response,
    extract_file_metadata,
    validate_file_types,
)
from tests.conftest import FakeUploadedFile

# ---------------------------------------------------------------------------
# build_echo_response
# ---------------------------------------------------------------------------


def test_build_echo_response_no_files_returns_text_only():
    # Arrange
    text = "hola"
    files: list[dict] = []

    # Act
    result = build_echo_response(text, files)

    # Assert
    assert result == "Mensaje recibido: 'hola'"


def test_build_echo_response_one_file_returns_singular():
    # Arrange
    text = "x"
    files = [{"name": "a.png", "type": "image/png", "size": 1, "thumbnail": None}]

    # Act
    result = build_echo_response(text, files)

    # Assert
    assert "(1 archivo adjunto)" in result


def test_build_echo_response_two_files_returns_plural():
    # Arrange
    text = "x"
    files = [
        {"name": "a.png", "type": "image/png", "size": 1, "thumbnail": None},
        {"name": "b.pdf", "type": "application/pdf", "size": 2, "thumbnail": None},
    ]

    # Act
    result = build_echo_response(text, files)

    # Assert
    assert "(2 archivos adjuntos)" in result


def test_build_echo_response_empty_text_with_file():
    # Arrange
    text = ""
    files = [{"name": "a.pdf", "type": "application/pdf", "size": 1, "thumbnail": None}]

    # Act
    result = build_echo_response(text, files)

    # Assert
    assert result == "Mensaje recibido: '' (1 archivo adjunto)"


# ---------------------------------------------------------------------------
# extract_file_metadata
# ---------------------------------------------------------------------------


def test_extract_file_metadata_image_returns_thumbnail(fake_png_file):
    # Arrange — fake_png_file provided by conftest fixture

    # Act
    result = extract_file_metadata(fake_png_file)

    # Assert
    assert result["name"] == "photo.png"
    assert result["type"] == "image/png"
    assert result["size"] == fake_png_file.size
    assert "thumbnail" in result
    assert isinstance(result["thumbnail"], str)
    assert result["thumbnail"].startswith("data:image/png;base64,")


def test_extract_file_metadata_pdf_returns_no_thumbnail(fake_pdf_file):
    # Arrange — fake_pdf_file provided by conftest fixture

    # Act
    result = extract_file_metadata(fake_pdf_file)

    # Assert
    assert result["name"] == "recipe.pdf"
    assert result["type"] == "application/pdf"
    assert result["size"] == fake_pdf_file.size
    assert result.get("thumbnail") is None


def test_extract_file_metadata_idempotent(fake_png_file):
    # Arrange — same fake file, called twice

    # Act
    result_a = extract_file_metadata(fake_png_file)
    result_b = extract_file_metadata(fake_png_file)

    # Assert
    assert result_a == result_b


# ---------------------------------------------------------------------------
# validate_file_types
# ---------------------------------------------------------------------------


def test_validate_file_types_allowed_types_pass():
    # Arrange
    allowed_mime_types = [
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/webp",
        "application/pdf",
    ]
    files = [
        FakeUploadedFile(f"file{i}", mime, b"data") for i, mime in enumerate(allowed_mime_types)
    ]

    # Act
    result = validate_file_types(files)

    # Assert
    assert len(result) == len(allowed_mime_types)


def test_validate_file_types_unsupported_type_excluded():
    # Arrange
    plain_text_file = FakeUploadedFile("readme.txt", "text/plain", b"hello")

    # Act
    result = validate_file_types([plain_text_file])

    # Assert — result-based, does NOT raise; unsupported type simply absent
    assert len(result) == 0
