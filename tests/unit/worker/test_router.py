"""Unit tests for src/worker/router.py — explicit source-type to loader factory."""

import pytest

from src.worker.loaders.pdf import load_pdf
from src.worker.router import loader_for


def test_loader_for_pdf_returns_pdf_loader():
    # Arrange
    source_type = "pdf"

    # Act
    loader = loader_for(source_type)

    # Assert
    assert loader is load_pdf


def test_loader_for_youtube_raises_not_implemented_error():
    # Arrange
    source_type = "youtube"

    # Act / Assert
    with pytest.raises(NotImplementedError):
        loader_for(source_type)


def test_loader_for_web_raises_not_implemented_error():
    # Arrange
    source_type = "web"

    # Act / Assert
    with pytest.raises(NotImplementedError):
        loader_for(source_type)


def test_loader_for_unknown_type_raises_value_error():
    # Arrange
    source_type = "unknown"

    # Act / Assert
    with pytest.raises(ValueError):
        loader_for(source_type)
