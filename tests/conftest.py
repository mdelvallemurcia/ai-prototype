"""Shared test fixtures and factories for the MealMate AI test suite."""

import io

import pytest
from PIL import Image


class FakeUploadedFile:
    """Duck-typed stand-in for Streamlit's UploadedFile.

    Exposes the four attributes that handlers.py depends on:
    .name, .type, .size, .getvalue()
    """

    def __init__(self, name: str, mime_type: str, data: bytes) -> None:
        self.name = name
        self.type = mime_type
        self.size = len(data)
        self._data = data

    def getvalue(self) -> bytes:
        return self._data


def make_png_bytes(width: int = 10, height: int = 10) -> bytes:
    """Return bytes of a minimal valid PNG image (in-memory, no disk I/O)."""
    img = Image.new("RGB", (width, height))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


@pytest.fixture
def fake_png_file() -> FakeUploadedFile:
    """A FakeUploadedFile backed by a tiny in-memory PNG."""
    return FakeUploadedFile("photo.png", "image/png", make_png_bytes())


@pytest.fixture
def fake_pdf_file() -> FakeUploadedFile:
    """A FakeUploadedFile that simulates a PDF (content is irrelevant for metadata tests)."""
    return FakeUploadedFile("recipe.pdf", "application/pdf", b"%PDF-1.4 fake content")
